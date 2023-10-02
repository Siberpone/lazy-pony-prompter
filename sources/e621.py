from lpp_utils import send_api_request, formatter


class TagSource():
    def __init__(self, work_dir="."):
        self.pretty_name = "E621"
        self.__work_dir = work_dir

    def request_tags(self, query, count):
        ENDPOINT = "https://e621.net/posts.json"
        PER_PAGE_MAX = 320
        QUERY_DELAY = 1
        query_params = {
            "tags": query,
            "limit": count if count < PER_PAGE_MAX else PER_PAGE_MAX
        }

        json_response = send_api_request(ENDPOINT, query_params)
        for post in json_response["posts"]:
            post["tags"]["rating"] = post["rating"]
        return {
            "source": "e621",
            "query": query,
            "raw_tags": [x["tags"] for x in json_response["posts"]]
        }

    @formatter("EasyFluff")
    def easyfluff_format(self, raw_image_tags):
        t = raw_image_tags
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["artist"] + t["general"] + t["copyright"] + t["meta"]]

    @formatter("EasyFluff (no aritst names)")
    def easyfluff_no_artist_format(self, raw_image_tags):
        t = raw_image_tags
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["general"] + t["copyright"] + t["meta"]]
