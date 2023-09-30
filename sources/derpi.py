from lpp_utils import send_api_request
import os
import time


class TagSource():
    def __init__(self, workdir="."):
        self.pretty_name = "Derpibooru"
        self.__workdir = workdir
        self.__api_key = self.__get_api_key()

        self.PER_PAGE_MAX = 50
        self.QUERY_DELAY = 0.5

        self.__filter_ids = {
            "Default (System)": 100073,
            "Everything (System)": 56027
        }
        if self.__api_key is not None:
            self.__fetch_user_filters()

        self.__sort_params = {
            "Wilson Score": "wilson_score",
            "Score": "score",
            "Upvotes": "upvotes",
            "Fave Count": "faves",
            "Upload Date": "first_seen_at",
            "Tag Count": "tag_count"
        }

    def get_filters(self):
        return list(self.__filter_ids.keys())

    def get_sort_options(self):
        return list(self.__sort_params.keys())

    def request_tags(self, query, count, filter_type=None, sort_type=None):
        endpoint = "https://derpibooru.org/api/v1/json/search/images"
        query_params = {
            "q": query,
            "per_page": self.PER_PAGE_MAX
        }
        if self.__api_key is not None:
            query_params["key"] = self.__api_key
        if filter_type is not None and filter_type in self.__filter_ids.keys():
            query_params["filter_id"] = self.__filter_ids[filter_type]
        if sort_type is not None and sort_type in self.__sort_params.keys():
            query_params["sf"] = self.__sort_params[sort_type]

        json_response = send_api_request(endpoint, query_params)
        response_total = json_response["total"]
        items_total = count if count < response_total else response_total
        pages_to_load = (items_total // self.PER_PAGE_MAX) + \
            (1 if items_total % self.PER_PAGE_MAX > 0 else 0)

        raw_tags = []
        for p in range(1, pages_to_load + 1):
            time.sleep(self.QUERY_DELAY)
            query_params["page"] = p
            json_response = send_api_request(endpoint, query_params)
            raw_tags += [x["tags"] for x in json_response["images"]]

        return {
            "source": "derpi",
            "query": query,
            "filter_type": filter_type,
            "sort_type": sort_type,
            "raw_tags": raw_tags[:items_total]
        }

    def __get_api_key(self):
        api_key_file = os.path.join(self.__workdir, "api_key")
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
            self.__filter_ids[filter["name"]] = filter["id"]
