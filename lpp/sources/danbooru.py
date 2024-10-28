from lpp.sources.common import TagSourceBase, Tags, formatter, default_formatter, attach_query_param
from lpp.data import TagData, TagGroups, Models, FilterData
from lpp.utils import get_config
from tqdm import trange
import os
import re
import time


class Danbooru(TagSourceBase):
    def __init__(self, work_dir: str = "."):
        TagSourceBase.__init__(self,
                               "https://danbooru.donmai.us/wiki_pages/help%3Acheatsheet",
                               "Danbooru query or image URL",
                               work_dir)
        config: dict[str:object] = get_config(
            "danbooru", os.path.join(self._work_dir, "config")
        )
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
        ENDPOINT = "https://danbooru.donmai.us/posts.json"
        PER_PAGE_MAX = 200
        QUERY_DELAY = 0.1

        image_id = re.search(
            r"/^(?:https?:\/\/)?(?:danbooru\.donmai\.us\/posts\/)?(\d+)(\?.*)?$", query
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

        posts = []
        pages_to_load = (count // PER_PAGE_MAX) + \
            (1 if count % PER_PAGE_MAX > 0 else 0)

        for p in trange(1, pages_to_load + 1, desc="[LPP] Fetching tags"):
            time.sleep(QUERY_DELAY)
            query_params["page"] = p
            json_response = self._send_api_request(ENDPOINT, query_params)
            posts += json_response
            if len(json_response) < PER_PAGE_MAX:
                break

        processed_response = []
        for post in posts:
            post_tags = {
                "general": post["tag_string_general"].split(" "),
                "artist": post["tag_string_artist"].split(" "),
                "rating": post["rating"],
                "character": post["tag_string_character"].split(" "),
                "meta": post["tag_string_meta"].split(" ")
                + post["tag_string_copyright"].split(" ")
            }
            processed_response.append(post_tags)
        return TagData(
            self.__class__.__name__,
            p_query,
            processed_response[:count],
            {}
        )

    def _convert_raw_tags(self, raw_tags: dict[str:object]) -> TagGroups:
        return TagGroups(species=[], **raw_tags)

    @default_formatter(Models.ANIME.value)
    def anime_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "artist", "general", "meta")\
            .filter(self.filter)\
            .replace_underscores()\
            .as_tag_groups()

    @formatter(f"{Models.ANIME.value} (keep underscores)")
    def anime_underscores_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "artist", "general", "meta")\
            .filter(self.filter)\
            .as_tag_groups()

    @formatter(Models.PDV56.value)
    def pdv5_format(self, raw_image_tags: dict[str:list[str]]) -> TagGroups:
        return Tags(self._convert_raw_tags(raw_image_tags))\
            .select("character", "rating", "general", "meta")\
            .modify(lambda x: self.__ratings["pdv5"][x], "rating")\
            .filter(self.filter)\
            .replace_underscores(exclude=["rating"])\
            .as_tag_groups()
