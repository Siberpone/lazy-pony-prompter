from lpp_utils import send_api_request, send_paged_api_request
from random import choices
import json
import os


class LazyPonyPrompter():
    def __init__(self, working_path="."):
        self.working_path = working_path
        self.api_key = self.get_api_key()
        self.prompts = []
        config = self.load_config()
        self.filters = config["system filters"]
        if self.api_key is not None:
            self.fetch_user_filters()
        self.sort_params = config["sort params"]
        self.ratings = config["ratings"]
        self.character_tags = set(config["character tags"])
        self.blacklisted_tags = set(config["blacklisted tags"])
        self.negative_prompt = config["negative prompt"]

    def load_config(self):
        with open(os.path.join(self.working_path, "config.json")) as f:
            return json.load(f)

    def get_api_key(self):
        api_key_file = os.path.join(self.working_path, "api_key")
        if os.path.exists(api_key_file):
            with open(api_key_file) as f:
                return f.readline().strip('\n')
        else:
            return None

    def fetch_user_filters(self):
        json_response = send_api_request(
            "https://derpibooru.org/api/v1/json/filters/user",
            {"key": self.api_key}
        )
        for filter in json_response["filters"]:
            self.filters[filter["name"]] = filter["id"]

    def fetch_prompts(self, query, count=50, filter_type=None, sort_type=None):
        query_params = {
            "q": query
        }
        if self.api_key is not None:
            query_params["key"] = self.api_key
        if filter_type is not None and filter_type in self.filters.keys():
            query_params["filter_id"] = self.filters[filter_type]
        if sort_type is not None and sort_type in self.sort_params.keys():
            query_params["sf"] = self.sort_params[sort_type]

        json_response = send_paged_api_request(
            "https://derpibooru.org/api/v1/json/search/images",
            query_params,
            lambda x: x["images"],
            lambda x: x["tags"],
            count
        )

        self.prompts.clear()
        preface = "source_pony, score_9"
        for tag_list in json_response:
            rating = None
            characters = []
            prompt_tail = []
            for tag in tag_list:
                if rating is None and tag in self.ratings.keys():
                    rating = self.ratings[tag]
                    continue
                if tag in self.character_tags:
                    characters.append(tag)
                    continue
                if tag.startswith("artist:") or tag in self.blacklisted_tags:
                    continue
                prompt_tail.append(tag)
            self.prompts.append(", ".join(filter(None, [
                preface,
                rating,
                ", ".join(characters),
                ", ".join(prompt_tail)
            ])))

    def choose_prompts(self, n=1):
        return choices(self.prompts, k=n)

    def get_loaded_prompts_count(self):
        return len(self.prompts)

    def get_negative_prompt(self):
        return self.negative_prompt
