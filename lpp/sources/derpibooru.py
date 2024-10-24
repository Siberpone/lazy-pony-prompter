from lpp.sources.common import TagSourceBase, formatter, default_formatter, attach_query_param
from lpp.data import TagData, TagGroups, Models
from lpp.utils import get_config, glob_match
from requests.exceptions import HTTPError, Timeout, ConnectionError, TooManyRedirects
from tqdm import trange
import time
import os
import re


class Derpibooru(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self,
                               "https://derpibooru.org/pages/search_syntax",
                               "Derpibooru query or image URL",
                               work_dir)
        self.__api_key = None
        config = get_config("derpi", os.path.join(self._work_dir, "config"))
        self.__filter_ids = config["filter_ids"]
        self.__sort_params = config["sort_params"]
        self.__ratings = config["ratings"]
        self.__character_tags = config["character_tags"]
        self.__species_tags = config["species_tags"]
        self.__meta_tags = config["meta_tags"]
        self.__filtered_tags = config["filtered_tags"]

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

    def request_tags(
        self, query: str, count: int,
        filter_type: str = None, sort_type: str = None
    ) -> TagData:
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
            self._logger.warning("Failed to fetch Derpibooru user filters due to connection issues.")
        except Timeout:
            self._logger.warning("Failed to fetch Derpibooru filters due to connection timeout.")
        except Exception as e:
            self._logger.debug(f"Failed to fetch Derpibooru user filters ({e:=})")

    def __filter_tags(self, raw_image_tags: list[str]) -> tuple[str]:
        rating = []
        characters = []
        species = []
        artists = []
        general = []
        meta = []
        for tag in raw_image_tags:
            if glob_match(tag, self.__filtered_tags):
                continue
            if tag in self.__ratings["pdv5"].keys():
                rating.append(self.__ratings["pdv5"][tag])
                continue
            if tag in self.__character_tags:
                characters.append(tag)
                continue
            if tag in self.__species_tags:
                species.append(tag)
                continue
            if glob_match(tag, self.__meta_tags):
                meta.append(tag)
                continue
            if tag.startswith("artist:"):
                artists.append(tag[7:])
                continue
            general.append(tag)
        return rating, characters, species, artists, general, meta

    @default_formatter(Models.PDV56.value)
    def pdv5_format(self, raw_image_tags: list[str]) -> TagGroups:
        rating, characters, species, _, general, meta = \
            self.__filter_tags(raw_image_tags)
        return TagGroups(
            characters,
            species,
            rating,
            [],
            general,
            meta
        )

    @formatter(Models.EF.value)
    def easyfluff_format(self, raw_image_tags: list[str]) -> TagGroups:
        _, characters, species, artists, general, meta = \
            self.__filter_tags(raw_image_tags)
        return TagGroups(
            characters,
            species,
            [],
            [f"by {x}" for x in artists],
            general,
            meta
        )

    @formatter(f"{Models.EF.value} (no artist names)")
    def easyfluff_no_artists_format(
        self, raw_image_tags: list[str]
    ) -> TagGroups:
        _, characters, species, _, general, meta = \
            self.__filter_tags(raw_image_tags)
        return TagGroups(
            characters,
            species,
            [],
            [],
            general,
            meta
        )
