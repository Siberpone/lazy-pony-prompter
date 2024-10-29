from lpp.sources.common import TagSourceBase, Tags, formatter, default_formatter, attach_query_param
from lpp.data import TagData, TagGroups, Models, FilterData
from tqdm import trange
import re
import time


class E621(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self,
                               "https://e621.net/help/cheatsheet",
                               "E621 query or image URL",
                               work_dir)
        config: dict[str:object] = self._get_config()
        self.__ratings: dict[str:str] = config["ratings"]
        self.__sort_params: dict[str:str] = config["sort_params"]
        self.filter: FilterData = FilterData.from_list(
            [x for cat in config["filtered_tags"].values() for x in cat]
        )

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
            r"^(?:https?:\/\/)?(?:e621\.net\/posts\/)?(\d+)(\?.*)?$", query
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

    def _convert_raw_tags(self, raw_tags: dict[str:object]) -> TagGroups:
        return TagGroups(
            raw_tags["character"],
            raw_tags["species"],
            raw_tags["rating"],
            raw_tags["artist"],
            raw_tags["general"],
            raw_tags["copyright"] + raw_tags["meta"]
        )

    @formatter(Models.PDV56.value)
    def pdv5_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "rating", "species", "general", "meta")\
            .modify(lambda x: self.__ratings["pdv5"][x], "rating")\
            .filter(self.filter)\
            .replace_underscores(exclude=["rating"])\
            .as_tag_groups()

    @default_formatter(Models.EF.value)
    def easyfluff_format(
            self, raw_image_tags: dict[str:list[str]]
    ) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "general", "artist", "meta")\
            .modify(lambda x: f"by {x}", "artist")\
            .filter(self.filter)\
            .replace_underscores()\
            .as_tag_groups()

    @formatter(f"{Models.EF.value} (no artist names)")
    def easyfluff_no_artist_format(
        self, raw_image_tags: dict[str:list[str]]
    ) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "general", "meta")\
            .filter(self.filter)\
            .replace_underscores()\
            .as_tag_groups()

    @formatter(Models.SEAART.value)
    def seaart_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "species", "general", "artist", "meta")\
            .filter(self.filter)\
            .as_tag_groups()
