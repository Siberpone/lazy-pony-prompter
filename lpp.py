from lpp_utils import *
from random import choices
import json
import os


class LazyPonyPrompter():
    def __init__(self, working_path="."):
        self.__working_path = working_path
        self.__api_key = self.__get_api_key()
        self.__prompt_cache = self.__load_prompt_cache()
        self.__prompts = {
            "quiery": "",
            "filter_type": "",
            "sort_type": "",
            "core": []
        }

        config = self.__load_config()
        self.__filters = config["system_filters"]
        if self.__api_key is not None:
            self.__fetch_user_filters()
        self.__sort_params = config["sort_params"]
        self.__ratings = config["ratings"]
        self.__character_tags = config["character_tags"]
        self.__prioritized_tags = config["prioritized_tags"]
        self.__filtered_tags = config["filtered_tags"]
        self.__negative_prompt = config["negative_prompt"]

    def choose_prompts(self, n=1, prefix=None, suffix=None, tag_filter_str=""):
        extra_tag_filter = set(
            filter(None, [t.strip() for t in tag_filter_str.split(",")])
        )

        chosen_prompts = choices(self.__prompts["core"], k=n)
        processed_prompts = []
        for prompt_core in chosen_prompts:
            filtered_prompt = filter(
                lambda tag: tag not in extra_tag_filter,
                prompt_core
            )
            processed_prompts.append(
                ", ".join(
                    filter(
                        None,
                        [
                            prefix,
                            ", ".join(filtered_prompt)
                                .replace("(", "\\(")
                                .replace(")", "\\)"),
                            suffix
                        ]
                    )
                )
            )
        return processed_prompts

    def get_loaded_prompts_count(self):
        return len(self.__prompts["core"])

    def get_negative_prompt(self):
        return self.__negative_prompt

    def get_cached_prompts_names(self):
        return list(self.__prompt_cache.keys())

    def get_filter_names(self):
        return list(self.__filters.keys())

    def get_sort_option_names(self):
        return list(self.__sort_params.keys())

    def cache_current_prompts(self, name):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        self.__prompt_cache[name] = self.__prompts
        self.__dump_prompts_cache()

    def load_cached_prompts(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        self.__prompts = self.__prompt_cache[name]

    def delete_cached_prompts(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        del self.__prompt_cache[name]
        self.__dump_prompts_cache()

    def get_cached_prompts_metadata(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        cache_entry = self.__prompt_cache[name]
        return {
            "query": cache_entry["query"],
            "filter_type": cache_entry["filter_type"],
            "sort_type": cache_entry["sort_type"],
            "prompts_count": len(cache_entry["core"])
        }

    def send_derpibooru_request(self, query, count, filter_type, sort_type):
        query_params = {
            "q": query
        }
        if self.__api_key is not None:
            query_params["key"] = self.__api_key
        if filter_type is not None and filter_type in self.__filters.keys():
            query_params["filter_id"] = self.__filters[filter_type]
        if sort_type is not None and sort_type in self.__sort_params.keys():
            query_params["sf"] = self.__sort_params[sort_type]

        raw_tags = send_paged_api_request(
            "https://derpibooru.org/api/v1/json/search/images",
            query_params,
            lambda x: x["images"],
            lambda x: x["tags"],
            count
        )
        self.__prompts = {
            "query": query,
            "filter_type": filter_type,
            "sort_type": sort_type,
            "core": self.__process_raw_tags(raw_tags)
        }

    def __load_config(self):
        p = self.__working_path

        # convert user tag filter to new format
        update_legacy_tag_filter(p)

        config = get_merged_config_entry("lpp", p)
        config["prioritized_tags"] = get_merged_config_entry(
            "prioritized_tags", p
        )
        config["character_tags"] = get_merged_config_entry("character_tags", p)
        config["filtered_tags"] = get_merged_config_entry("filtered_tags", p)
        return config

    def __load_prompt_cache(self):

        # convert legacy cache file to new format
        update_legacy_prompt_cache(self.__working_path)

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

    def __dump_prompts_cache(self):
        cache_file = os.path.join(self.__working_path, "cache.json")
        with open(cache_file, "w") as f:
            json.dump(self.__prompt_cache, f, indent=4)

    def __process_raw_tags(self, raw_image_tags):
        processed_tags = []
        for tag_list in raw_image_tags:
            rating = None
            characters = []
            prioritized_tags = []
            prompt_tail = []
            for tag in tag_list:
                if (any([tag.startswith(x) for x in self.__filtered_tags["starts_with"]])
                        or any([tag.endswith(x) for x in self.__filtered_tags["ends_with"]])
                        or tag in self.__filtered_tags["exact"]):
                    continue
                if rating is None and tag in self.__ratings.keys():
                    rating = self.__ratings[tag]
                    continue
                if tag in self.__character_tags:
                    characters.append(tag)
                    continue
                if tag in self.__prioritized_tags:
                    prioritized_tags.append(tag)
                    continue
                prompt_tail.append(tag)
            processed_tags.append(([] if rating is None else [rating])
                                  + characters + prioritized_tags + prompt_tail)
        return processed_tags
