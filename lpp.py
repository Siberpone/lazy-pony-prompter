from lpp_utils import send_api_request, send_paged_api_request
from random import choices
import json
import os


class LazyPonyPrompter():
    def __init__(self, working_path="."):
        self.__working_path = working_path
        self.__api_key = self.__get_api_key()
        self.__prompt_cache = self.__load_prompt_cache()
        self.__prompts = []

        config = self.__load_config()
        self.__filters = config["system filters"]
        if self.__api_key is not None:
            self.__fetch_user_filters()
        self.__sort_params = config["sort params"]
        self.__ratings = config["ratings"]
        self.__character_tags = set(config["character tags"])
        self.__prioritized_tags = set(config["prioritized tags"])
        self.__blacklisted_tags = set(config["blacklisted tags"])
        self.__negative_prompt = config["negative prompt"]

    def choose_prompts(self, n=1):
        return choices(self.__prompts, k=n)

    def get_loaded_prompts_count(self):
        return len(self.__prompts)

    def get_negative_prompt(self):
        return self.__negative_prompt

    def get_cached_prompts_names(self):
        return self.__prompt_cache.keys()

    def get_filter_names(self):
        return self.__filters.keys()

    def get_sort_option_names(self):
        return self.__sort_params.keys()

    def cache_current_prompts(self, name):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        self.__prompt_cache[name] = self.__prompts
        cache_file = os.path.join(self.__working_path, "cache.json")
        with open(cache_file, "w") as f:
            json.dump(self.__prompt_cache, f, indent=4)

    def load_cached_prompts(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        self.__prompts = self.__prompt_cache[name]

    def fetch_prompts(self, query, count=50, filter_type=None, sort_type=None):
        query_params = {
            "q": query
        }
        if self.__api_key is not None:
            query_params["key"] = self.__api_key
        if filter_type is not None and filter_type in self.__filters.keys():
            query_params["filter_id"] = self.__filters[filter_type]
        if sort_type is not None and sort_type in self.__sort_params.keys():
            query_params["sf"] = self.__sort_params[sort_type]

        json_response = send_paged_api_request(
            "https://derpibooru.org/api/v1/json/search/images",
            query_params,
            lambda x: x["images"],
            lambda x: x["tags"],
            count
        )
        self.__prompts = self.__process_raw_tags(json_response)

    def __load_config(self):
        with open(os.path.join(self.__working_path, "config.json")) as f:
            return json.load(f)

    def __load_prompt_cache(self):
        cache_file = os.path.join(self.__working_path, "cache.json")
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                return json.load(f)
        else:
            return {}

    def __get_api_key(self):
        api_key_file = os.path.join(self.__working_path, "api_key")
        if os.path.exists(api_key_file):
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
            self.__filters[filter["name"]] = filter["id"]

    def __process_raw_tags(self, raw_image_tags):
        result = []
        preface = "source_pony, score_9"
        for tag_list in raw_image_tags:
            rating = None
            characters = []
            prioritized_tags = []
            prompt_tail = []
            for tag in tag_list:
                if rating is None and tag in self.__ratings.keys():
                    rating = self.__ratings[tag]
                    continue
                if tag in self.__character_tags:
                    characters.append(tag)
                    continue
                if tag in self.__prioritized_tags:
                    prioritized_tags.append(tag)
                    continue
                if tag.startswith("artist:") or tag in self.__blacklisted_tags:
                    continue
                prompt_tail.append(tag)
            result.append(
                ", ".join(
                    filter(
                        None,
                        [
                            preface,
                            rating,
                            ", ".join(characters),
                            ", ".join(prioritized_tags),
                            ", ".join(prompt_tail)
                        ]
                    )
                )
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
        return result
