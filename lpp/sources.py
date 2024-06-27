from lpp.utils import TagData, TagGroups, Models, glob_match, get_config
from lpp.log import get_logger
from urllib.request import urlopen, Request, URLError
from urllib.parse import urlencode
from abc import ABC, abstractmethod
import os
import re
import time
import json

logger = get_logger()


def formatter(model_name: callable) -> callable:
    def inner(func: callable) -> callable:
        func.is_formatter = True
        func.model_name = model_name
        return func
    return inner


class TagSourceBase(ABC):
    def __init__(self, work_dir: str = "."):
        self._work_dir: str = work_dir
        self.formatters: dict[str:callable] = {}
        for attr in [x for x in dir(self) if not x.startswith("_")]:
            obj = getattr(self, attr)
            if hasattr(obj, "is_formatter"):
                self.formatters[obj.model_name] = obj

    def _send_api_request(
        self, endpoint: str, query_params: dict[str:str],
        user_agent: str = "lazy-pony-prompter (by user Siberpone)"
    ) -> dict[str:object]:
        url = "?".join([endpoint, urlencode(query_params)])
        req = Request(url)
        req.add_header("User-Agent", user_agent)
        with urlopen(req) as response:
            return json.load(response)

    def get_model_names(self) -> list[str]:
        return list(self.formatters.keys())

    @abstractmethod
    def get_lpp_rating(self, tag_data: TagData):
        pass

    @abstractmethod
    def request_tags(self, query: str, count: int, *params: object) -> TagData:
        pass


class E621(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self, work_dir)
        config: dict[str:object] = get_config(
            "e621", os.path.join(self._work_dir, "config")
        )
        self.__ratings: dict[str:str] = config["ratings"]
        self.__sort_params: dict[str:str] = config["sort_params"]
        self.__filtered_tags: dict[str:object] = config["filtered_tags"]

    def get_ratings(self) -> list[str]:
        return list(self.__ratings["lookup"].keys())

    def get_sort_options(self) -> list[str]:
        return list(self.__sort_params.keys())

    def get_lpp_rating(self, raw_tags: dict[str:list[str]]) -> str:
        return self.__ratings["lpp"][raw_tags["rating"]]

    def request_tags(
        self, query: str, count: int,
        rating: str = None, sort_type: str = None
    ) -> TagData:
        ENDPOINT = "https://e621.net/posts.json"
        PER_PAGE_MAX = 320
        QUERY_DELAY = 1

        image_id = re.search(
            r"^(?:https?:\/\/)?(?:e621\.net\/posts\/)?(\d+).*$", query
        )
        if image_id:
            query = f"id:{image_id.groups(0)[0]}"

        p_rating = self.__ratings["lookup"][rating] if rating \
            and rating in self.__ratings["lookup"] else None
        p_sort = self.__sort_params[sort_type] if sort_type \
            and sort_type in self.__sort_params else None
        p_query = " ".join(x for x in [query, p_rating, p_sort] if x)
        query_params = {
            "tags": p_query,
            "limit": count if count < PER_PAGE_MAX else PER_PAGE_MAX
        }

        raw_tags = []
        pages_to_load = (count // PER_PAGE_MAX) + \
            (1 if count % PER_PAGE_MAX > 0 else 0)

        for p in range(1, pages_to_load + 1):
            time.sleep(QUERY_DELAY)
            query_params["page"] = p
            json_response = self._send_api_request(ENDPOINT, query_params)
            posts = json_response["posts"]
            for post in posts:
                post["tags"]["rating"] = post["rating"]
            raw_tags += posts
            if len(posts) < PER_PAGE_MAX:
                break

        raw_tags = [x["tags"] for x in raw_tags]
        return TagData(
            self.__class__.__name__,
            p_query,
            raw_tags[:count],
            {}
        )

    def __replace_underscores(self, tags: dict[str:list[str]]):
        return {k: [x.replace("_", " ") for x in v] for k, v in tags.items()}

    def __filter_raw_tags(
        self, categories: list[str], raw_image_tags: dict[str:list[str]]
    ) -> dict[str:list[str]]:
        filtered_tags = {}
        for category in categories:
            if category not in self.__filtered_tags.keys():
                filtered_tags[category] = raw_image_tags[category]
            else:
                filtered_tags[category] = [
                    x for x in raw_image_tags[category]
                    if not glob_match(x, self.__filtered_tags[category])
                ]
        return self.__replace_underscores(filtered_tags)

    @formatter(Models.PDV56.value)
    def pdv5_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "meta"],
            raw_image_tags
        )
        rating = self.__ratings["pdv5"][raw_image_tags["rating"]]
        return TagGroups(
            t["character"],
            t["species"],
            [rating],
            [],
            t["general"],
            t["meta"]
        )

    @formatter(Models.EF.value)
    def easyfluff_format(
        self, raw_image_tags: dict[str:list[str]]
    ) -> TagGroups:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "artist", "copyright", "meta"],
            raw_image_tags
        )
        return TagGroups(
            t["character"],
            t["species"],
            [],
            [f"by {x}" for x in t["artist"]],
            t["general"],
            t["copyright"] + t["meta"]
        )

    @formatter(f"{Models.EF.value} (no artist names)")
    def easyfluff_no_artist_format(
        self, raw_image_tags: dict[str:list[str]]
    ) -> TagGroups:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "copyright", "meta"],
            raw_image_tags
        )
        return TagGroups(
            t["character"],
            t["species"],
            [],
            [],
            t["general"],
            t["copyright"] + t["meta"]
        )


class Derpibooru(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self, work_dir)
        self.__api_key = None
        config = get_config("derpi", os.path.join(self._work_dir, "config"))
        self.__filter_ids = config["filter_ids"]
        self.__sort_params = config["sort_params"]
        self.__ratings = config["ratings"]
        self.__character_tags = config["character_tags"]
        self.__species_tags = config["species_tags"]
        self.__meta_tags = config["meta_tags"]
        self.__filtered_tags = config["filtered_tags"]

    def get_filters(self) -> list[str]:
        return list(self.__filter_ids.keys())

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
            r"^(?:https?:\/\/)?(?:derpibooru\.org\/images\/)?(\d+).*$", query
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
        for p in range(1, pages_to_load + 1):
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
        logger.info("Attempting to fetch Derpibooru user filters...")
        try:
            json_response = self._send_api_request(
                "https://derpibooru.org/api/v1/json/filters/user",
                {"key": self.__api_key}
            )

            for filter in json_response["filters"]:
                self.__filter_ids[filter["name"]] = filter["id"]
            logger.info("Successfully fetched Derpibooru user filters.")
        except (URLError, json.JSONDecodeError):
            logger.warning("Failed to fetch Derpibooru user filters")
        except Exception as e:
            logger.debug(f"Failed to fetch Derpibooru user filters ({e:=})")

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
            if tag in self.__meta_tags:
                meta.append(tag)
                continue
            if tag.startswith("artist:"):
                artists.append(tag[7:])
                continue
            general.append(tag)
        return rating, characters, species, artists, general, meta

    @formatter(Models.PDV56.value)
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
