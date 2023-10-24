from lpp.utils import TagData, glob_match, get_config
from lpp.log import get_logger
from urllib.request import urlopen, Request, URLError
from urllib.parse import urlencode
import os
import time
import json

logger = get_logger()


def formatter(model_name: callable) -> callable:
    def inner(func: callable) -> callable:
        func.is_formatter = True
        func.model_name = model_name
        return func
    return inner


class TagSourceBase:
    def __init__(self, work_dir: str = "."):
        self._work_dir: str = work_dir
        self.models: dict[str:callable] = {}
        for attr in [x for x in dir(self) if not x.startswith("_")]:
            obj = getattr(self, attr)
            if hasattr(obj, "is_formatter"):
                self.models[obj.model_name] = obj

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
        return list(self.models.keys())

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

    def request_tags(
        self, query: str, count: int,
        rating: str = None, sort_type: str = None
    ) -> TagData:
        ENDPOINT = "https://e621.net/posts.json"
        PER_PAGE_MAX = 320
        QUERY_DELAY = 1

        p_rating = self.__ratings["lookup"][rating] if rating \
            and rating in self.__ratings["lookup"] else None
        p_sort = self.__sort_params[sort_type] if sort_type \
            and sort_type in self.__sort_params else None
        p_query = " ".join(x for x in [query, p_rating, p_sort] if x)
        query_params = {
            "tags": p_query,
            "limit": count if count < PER_PAGE_MAX else PER_PAGE_MAX
        }

        json_response = self._send_api_request(ENDPOINT, query_params)
        for post in json_response["posts"]:
            post["tags"]["rating"] = post["rating"]
        return TagData(
            self.__class__.__name__,
            p_query,
            [x["tags"] for x in json_response["posts"]],
            {}
        )

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
        return filtered_tags

    @formatter("Pony Diffusion V5")
    def pdv5_format(self, raw_image_tags: dict[str:list[str]]) -> list[str]:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "meta"],
            raw_image_tags
        )
        rating = self.__ratings["pdv5"][raw_image_tags["rating"]]
        return [rating] + [x.replace("_", " ") for x in t["character"]
                           + t["species"] + t["general"] + t["meta"]]

    @formatter("EasyFluff")
    def easyfluff_format(
        self, raw_image_tags: dict[str:list[str]]
    ) -> list[str]:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "artist", "copyright", "meta"],
            raw_image_tags
        )
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["general"] + [f"by {x}" for x in t["artist"]]
                + t["copyright"] + t["meta"]]

    @formatter("EasyFluff (no artist names)")
    def easyfluff_no_artist_format(
        self, raw_image_tags: dict[str:list[str]]
    ) -> list[str]:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "copyright", "meta"],
            raw_image_tags
        )
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["general"] + t["copyright"] + t["meta"]]


class Derpibooru(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self, work_dir)
        self.__api_key = self.__get_api_key()
        config = get_config("derpi", os.path.join(self._work_dir, "config"))
        self.__filter_ids = config["filter_ids"]
        self.__sort_params = config["sort_params"]
        self.__pdv5_ratings = config["ratings"]["pdv5"]
        self.__character_tags = config["character_tags"]
        self.__prioritized_tags = config["prioritized_tags"]
        self.__filtered_tags = config["filtered_tags"]
        if self.__api_key is not None:
            self.__fetch_user_filters()

    def get_filters(self) -> list[str]:
        return list(self.__filter_ids.keys())

    def get_sort_options(self) -> list[str]:
        return list(self.__sort_params.keys())

    def request_tags(
        self, query: str, count: int,
        filter_type: str = None, sort_type: str = None
    ) -> TagData:
        ENDPOINT = "https://derpibooru.org/api/v1/json/search/images"
        PER_PAGE_MAX = 50
        QUERY_DELAY = 0.5

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

    def __get_api_key(self) -> str:
        old_api_key_file = os.path.join(self._work_dir, "api_key")
        api_key_file = os.path.join(self._work_dir, "auth", "derpi")
        if os.path.exists(old_api_key_file):
            with open(old_api_key_file) as f:
                return f.readline().strip('\n')
        elif os.path.exists(api_key_file):
            with open(api_key_file) as f:
                return f.readline().strip('\n')
        else:
            return None

    def __fetch_user_filters(self) -> None:
        try:
            json_response = self._send_api_request(
                "https://derpibooru.org/api/v1/json/filters/user",
                {"key": self.__api_key}
            )

            for filter in json_response["filters"]:
                self.__filter_ids[filter["name"]] = filter["id"]
        except (URLError, json.JSONDecodeError):
            logger.warning("Failed to fetch Derpibooru user filters")

    def __filter_tags(self, raw_image_tags: list[str]) -> tuple[str]:
        rating = None
        characters = []
        prioritized_tags = []
        artists = []
        prompt_tail = []
        for tag in raw_image_tags:
            if glob_match(tag, self.__filtered_tags):
                continue
            if rating is None and tag in self.__pdv5_ratings.keys():
                rating = self.__pdv5_ratings[tag]
                continue
            if tag in self.__character_tags:
                characters.append(tag)
                continue
            if tag in self.__prioritized_tags:
                prioritized_tags.append(tag)
                continue
            if tag.startswith("artist:"):
                artists.append(tag[7:])
                continue
            prompt_tail.append(tag)
        return ([] if rating is None else [rating]), characters, \
            prioritized_tags, artists, prompt_tail

    @formatter("Pony Diffusion V5")
    def pdv5_format(self, raw_image_tags: list[str]) -> list[str]:
        rating, characters, prioritized_tags, _, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return rating + characters + prioritized_tags + prompt_tail

    @formatter("EasyFluff")
    def easyfluff_format(self, raw_image_tags: list[str]) -> list[str]:
        _, characters, prioritized_tags, artists, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return characters + prioritized_tags \
            + [f"by {x}" for x in artists] + prompt_tail

    @formatter("EasyFluff (no artist names)")
    def easyfluff_no_artists_format(
        self, raw_image_tags: list[str]
    ) -> list[str]:
        _, characters, prioritized_tags, artists, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return characters + prioritized_tags + prompt_tail
