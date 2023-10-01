from lpp_utils import send_api_request


class TagSource():
    def __init__(self, work_dir="."):
        self.pretty_name = "E621"
        self.__work_dir = work_dir

        self.PER_PAGE_MAX = 320
        self.QUERY_DELAY = 1

    # HACK: remove *args after fixing UI
    def request_tags(self, query, count, *args):
        endpoint = "https://e621.net/posts.json"
        query_params = {
            "tags": query,
            "limit": count if count < self.PER_PAGE_MAX else self.PER_PAGE_MAX
        }

        json_response = send_api_request(endpoint, query_params,)
        return {
            "source": "e621",
            "query": query,
            "raw_tags": [x["tags"] for x in json_response["posts"]]
        }
