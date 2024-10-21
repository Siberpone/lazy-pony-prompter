from lpp.sources.common import TagSourceBase, formatter, default_formatter, attach_query_param
from lpp.utils import TagData, TagGroups, Models, glob_match, get_config
from tqdm import trange
import os
import re
import time


class E621(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self,
                               "https://e621.net/help/cheatsheet",
                               "E621 query or image URL",
                               work_dir)
        config: dict[str:object] = get_config(
            "e621", os.path.join(self._work_dir, "config")
        )
        self.__ratings: dict[str:str] = config["ratings"]
        self.__sort_params: dict[str:str] = config["sort_params"]
        self.__filtered_tags: dict[str:object] = config["filtered_tags"]

    @attach_query_param("rating", "Rating")
    def get_ratings(self) -> list[str]:
        return list(self.__ratings["lookup"].keys())

    @attach_query_param("sort_type", "Sort by")
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

        for p in trange(1, pages_to_load + 1, desc="[LPP] Fetching tags"):
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

    def __filter_raw_tags(self,
                          categories: list[str],
                          raw_image_tags: dict[str:list[str]],
                          replace_underscores: bool = True
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
        return self.__replace_underscores(filtered_tags)\
            if replace_underscores else filtered_tags

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

    @default_formatter(Models.EF.value)
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

    @formatter(Models.SEAART.value)
    def seaart_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        t = self.__filter_raw_tags(
            ["character", "species", "general", "artist", "copyright", "meta"],
            raw_image_tags,
            False
        )
        return TagGroups(
            t["character"],
            t["species"],
            [],
            t["artist"],
            t["general"],
            t["copyright"] + t["meta"]
        )
