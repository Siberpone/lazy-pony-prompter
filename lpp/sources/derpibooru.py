from lpp.sources.common import TagSourceBase, Tags, formatter, default_formatter, attach_query_param
from lpp.data import TagData, TagGroups, Models, FilterData, ImageData
from requests.exceptions import HTTPError, Timeout, ConnectionError, TooManyRedirects
from tqdm import trange
import time
import re


class Derpibooru(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self,
                               "https://derpibooru.org/pages/search_syntax",
                               "Derpibooru query or image URL",
                               work_dir)
        self.__api_key = None
        config = self._get_config()
        self.__filter_ids = config["filter_ids"]
        self.__sort_params = config["sort_params"]
        self.__ratings = config["ratings"]
        self.__character_tags = set(config["character_tags"])
        self.__species_tags = set(config["species_tags"])
        self.__meta_tags = set()
        self.__meta_tags_glob = set()
        for pattern in config["meta_tags"]:
            if any(x in pattern for x in ["*", "[", "?"]):
                self.__meta_tags_glob.add(pattern)
            else:
                self.__meta_tags.add(pattern)
        self.filter = FilterData.from_list(config["filtered_tags"])

    @attach_query_param("filter_type", "Derpibooru Filter")
    def get_filters(self) -> list[str]:
        return list(self.__filter_ids.keys())

    @attach_query_param("sort_type", "Sort by")
    def get_sort_options(self) -> list[str]:
        return list(self.__sort_params.keys())

    def get_lpp_rating(self, raw_tags: list[str]) -> str:
        for tag in raw_tags:
            if tag in self.__ratings["lpp"].keys():
                return self.__ratings["lpp"][tag]
        return "Unknown"

    def request_tags(self,
                     query: str,
                     count: int,
                     filter_type: str = None,
                     sort_type: str = None) -> TagData:
        ENDPOINT = "https://derpibooru.org/api/v1/json/search/images"
        PER_PAGE_MAX = 50
        QUERY_DELAY = 0.5

        image_id = re.search(
            r"^(?:https?:\/\/)?(?:derpibooru\.org\/images\/)?(\d+)(\?.*)?$", query
        )
        if image_id:
            query = f"id:{image_id.groups(0)[0]}"

        query_params = {
            "q": query,
            "per_page": PER_PAGE_MAX
        }
        if self.__api_key is not None:
            query_params["key"] = self.__api_key
        if filter_type is not None and filter_type in self.__filter_ids.keys():
            query_params["filter_id"] = self.__filter_ids[filter_type]
        if sort_type is not None and sort_type in self.__sort_params.keys():
            query_params["sf"] = self.__sort_params[sort_type]

        json_response = self._send_api_request(ENDPOINT, query_params)
        response_total = json_response["total"]
        items_total = count if count < response_total else response_total
        pages_to_load = (items_total // PER_PAGE_MAX) + \
            (1 if items_total % PER_PAGE_MAX > 0 else 0)

        raw_tags = []
        for p in trange(1, pages_to_load + 1, desc="[LPP] Fetching tags"):
            time.sleep(QUERY_DELAY)
            query_params["page"] = p
            json_response = self._send_api_request(ENDPOINT, query_params)
            raw_tags += [x["tags"] for x in json_response["images"]]

        return TagData(
            self.__class__.__name__,
            query,
            raw_tags[:items_total],
            {
                "filter_type": filter_type,
                "sort_type": sort_type,
            }
        )

    def request_image_data(self,
                           query: str,
                           page: int = 1,
                           filter_type: str = None,
                           sort_type: str = None) -> list[ImageData]:
        ENDPOINT = "https://derpibooru.org/api/v1/json/search/images"
        PER_PAGE_MAX = 12

        image_id = re.search(
            r"^(?:https?:\/\/)?(?:derpibooru\.org\/images\/)?(\d+)(\?.*)?$", query
        )
        if image_id:
            query = f"id:{image_id.groups(0)[0]}"

        query_params = {
            "q": query + ", -webm, -animated",
            "page": page,
            "per_page": PER_PAGE_MAX
        }
        if self.__api_key is not None:
            query_params["key"] = self.__api_key
        if filter_type is not None and filter_type in self.__filter_ids.keys():
            query_params["filter_id"] = self.__filter_ids[filter_type]
        if sort_type is not None and sort_type in self.__sort_params.keys():
            query_params["sf"] = self.__sort_params[sort_type]

        json_response = self._send_api_request(ENDPOINT, query_params)

        image_data = []
        for image in json_response["images"]:
            image_data.append(
                ImageData(
                    image["id"],
                    image["tags"],
                    image["representations"]["full"],
                    image["representations"]["thumb"],
                    self.__class__.__name__
                )
            )
        return image_data

    def _convert_raw_tags(self, raw_tags: list[str]) -> TagGroups:
        sorted_tags = {k: [] for k in TagGroups.get_categories()}
        for tag in raw_tags:
            if tag in self.__ratings["pdv5"]:
                sorted_tags["rating"].append(self.__ratings["pdv5"][tag])
                continue
            if tag in self.__character_tags or tag.startswith("oc:"):
                sorted_tags["character"].append(tag)
                continue
            if tag in self.__species_tags:
                sorted_tags["species"].append(tag)
                continue
            if (tag in self.__meta_tags
                    or FilterData.glob_match(tag, *self.__meta_tags_glob)):
                sorted_tags["meta"].append(tag)
                continue
            if tag.startswith("artist:"):
                sorted_tags["artist"].append(tag[7:])
                continue
            sorted_tags["general"].append(tag)
        return TagGroups(**sorted_tags)

    def set_api_key(self, key: str):
        if not key:
            return
        self.__api_key = key
        self.__fetch_user_filters()

    def __fetch_user_filters(self) -> None:
        self._logger.info("Attempting to fetch Derpibooru user filters...")
        try:
            json_response = self._send_api_request(
                "https://derpibooru.org/api/v1/json/filters/user",
                {"key": self.__api_key}
            )

            for filter in json_response["filters"]:
                self.__filter_ids[filter["name"]] = filter["id"]
            self._logger.info("Successfully fetched Derpibooru user filters.")
        except (HTTPError, ConnectionError, TooManyRedirects):
            self._logger.warning(
                "Failed to fetch Derpibooru user filters due to connection issues."
            )
        except Timeout:
            self._logger.warning(
                "Failed to fetch Derpibooru filters due to connection timeout."
            )
        except Exception as e:
            self._logger.debug(
                f"Failed to fetch Derpibooru user filters ({e:=})"
            )

    @default_formatter(Models.PDV56.value)
    def pdv5_format(self, raw_image_tags: list[str]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "rating", "general", "meta")\
            .filter(self.filter)\
            .as_tag_groups()

    @formatter(Models.EF.value)
    def easyfluff_format(self, raw_image_tags: list[str]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "artist", "general", "meta")\
            .modify(lambda x: f"by {x}", "artist")\
            .filter(self.filter)\
            .as_tag_groups()

    @formatter(f"{Models.EF.value} (no artist names)")
    def easyfluff_no_artists_format(
        self, raw_image_tags: list[str]
    ) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "general", "meta")\
            .filter(self.filter)\
            .as_tag_groups()
