from urllib.request import urlopen, Request
from urllib.parse import urlencode
from random import choices
import json
import os


class LazyPonyPrompter():
    def __init__(self, working_path="."):
        self.working_path = working_path
        self.api_key = self.get_api_key()
        self.prompts = []
        self.api_endpoint = 'https://derpibooru.org/api/v1/json/search/images'
        self.filters = {
            "Default (System)": 100073,
            "Everything (System)": 56027
        }
        if self.api_key is not None:
            self.fetch_user_filters()
        self.sort_params = {
            "Wilson Score": "wilson_score",
            "Score": "score",
            "Tag Count": "tag_count",
            "Upvotes": "upvotes",
            "Fave Count": "faves"
        }
        self.ratings = {
            "safe": "rating_safe",
            "suggestive": "rating_questionable",
            "questionable": "rating_questionable",
            "explicit": "rating_explicit",
            "semi-grimdark": "rating_explicit, semi-grimdark",
            "grimdark": "rating_explicit, grimdark",
            "grotesque": "rating_explicit, grotesque",
        }

    def get_api_key(self):
        api_key_file = os.path.join(self.working_path, "api_key")
        if os.path.exists(api_key_file):
            with open(api_key_file) as f:
                return f.readline().strip('\n')
        else:
            return None

    def fetch_user_filters(self):
        filter_api_endpoint = "https://derpibooru.org/api/v1/json/filters/user"
        query = {
            "key": self.api_key
        }
        url = "?".join([filter_api_endpoint, urlencode(query)])
        req = Request(url)
        req.add_header("User-Agent", "urllib")
        with urlopen(req) as response:
            json_response = json.load(response)

        for filter in json_response["filters"]:
            self.filters[filter["name"]] = filter["id"]

    def fetch_prompts(
            self,
            query,
            count=50,
            filter_type=None,
            sort_type=None):
        query_params = {
            "q": query,
            "per_page": count
        }
        if self.api_key is not None:
            query_params["key"] = self.api_key
        if filter_type is not None and filter_type in self.filters.keys():
            query_params["filter_id"] = self.filters[filter_type]
        if sort_type is not None and sort_type in self.sort_params.keys():
            query_params["sf"] = self.sort_params[sort_type]

        url = "?".join([self.api_endpoint, urlencode(query_params)])
        req = Request(url)
        req.add_header("User-Agent", "urllib")
        with urlopen(req) as response:
            json_response = json.load(response)

        self.prompts.clear()
        preface = "source_pony, score_9"
        for image in json_response["images"]:
            rating = None
            prompt = []
            for tag in image["tags"]:
                if rating is None and tag in self.ratings.keys():
                    rating = self.ratings[tag]
                    continue
                if tag.startswith("artist:"):
                    continue
                prompt.append(tag)
            self.prompts.append(
                " ,".join(filter(None, [preface, rating, " ,".join(prompt)]))
            )

    def choose_prompts(self, n=1):
        return choices(self.prompts, k=n)

    def get_loaded_prompts_count(self):
        return len(self.prompts)
