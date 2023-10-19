from lpp_utils import send_api_request, get_config, formatter, glob_match
from lpp import TagData
import os
import time


class TagSource():
    def __init__(self, work_dir="."):
        self.pretty_name = "Derpibooru"
        self.__work_dir = work_dir
        self.__api_key = self.__get_api_key()
        config = get_config("derpi", os.path.join(self.__work_dir, "config"))
        self.__filter_ids = config["filter_ids"]
        self.__sort_params = config["sort_params"]
        self.__pdv5_ratings = config["ratings"]["pdv5"]
        self.__character_tags = config["character_tags"]
        self.__prioritized_tags = config["prioritized_tags"]
        self.__filtered_tags = config["filtered_tags"]
        if self.__api_key is not None:
            self.__fetch_user_filters()

    def get_filters(self):
        return list(self.__filter_ids.keys())

    def get_sort_options(self):
        return list(self.__sort_params.keys())

    def request_tags(self, query, count, filter_type=None, sort_type=None):
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

        json_response = send_api_request(ENDPOINT, query_params)
        response_total = json_response["total"]
        items_total = count if count < response_total else response_total
        pages_to_load = (items_total // PER_PAGE_MAX) + \
            (1 if items_total % PER_PAGE_MAX > 0 else 0)

        raw_tags = []
        for p in range(1, pages_to_load + 1):
            time.sleep(QUERY_DELAY)
            query_params["page"] = p
            json_response = send_api_request(ENDPOINT, query_params)
            raw_tags += [x["tags"] for x in json_response["images"]]

        return TagData(
            "derpi",
            query,
            raw_tags[:items_total],
            {
                "filter_type": filter_type,
                "sort_type": sort_type,
            }
        )

    def __get_api_key(self):
        old_api_key_file = os.path.join(self.__work_dir, "api_key")
        api_key_file = os.path.join(self.__work_dir, "auth", "derpi")
        if os.path.exists(old_api_key_file):
            with open(old_api_key_file) as f:
                return f.readline().strip('\n')
        elif os.path.exists(api_key_file):
            with open(api_key_file) as f:
                return f.readline().strip('\n')
        else:
            return None

    def __fetch_user_filters(self):
        json_response = send_api_request(
            "https://derpibooru.org/api/v1/json/filters/user",
            {"key": self.__api_key}
        )
        for filter in json_response["filters"]:
            self.__filter_ids[filter["name"]] = filter["id"]

    def __filter_tags(self, raw_image_tags):
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
    def pdv5_format(self, raw_image_tags):
        rating, characters, prioritized_tags, _, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return rating + characters + prioritized_tags + prompt_tail

    @formatter("EasyFluff")
    def easyfluff_format(self, raw_image_tags):
        _, characters, prioritized_tags, artists, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return characters + prioritized_tags \
            + [f"by {x}" for x in artists] + prompt_tail

    @formatter("EasyFluff (no artist names)")
    def easyfluff_no_artists_format(self, raw_image_tags):
        _, characters, prioritized_tags, artists, prompt_tail = \
            self.__filter_tags(raw_image_tags)
        return characters + prioritized_tags + prompt_tail
