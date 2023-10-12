from lpp_utils import send_api_request, formatter, get_config, glob_match
import os


class TagSource():
    def __init__(self, work_dir="."):
        self.pretty_name = "E621"
        self.__work_dir = work_dir
        config = get_config(
            "e621", os.path.join(self.__work_dir, "config")
        )
        self.__ratings = config["ratings"]
        self.__sort_params = config["sort_params"]
        self.__filtered_tags = config["filtered_tags"]

    def get_ratings(self):
        return list(self.__ratings["lookup"].keys())

    def get_sort_options(self):
        return list(self.__sort_params.keys())

    def request_tags(self, query, count, rating=None, sort_type=None):
        ENDPOINT = "https://e621.net/posts.json"
        PER_PAGE_MAX = 320
        QUERY_DELAY = 1

        p_rating = self.__ratings["lookup"][rating] if rating \
            and rating in self.__ratings["lookup"] else None
        p_sort = self.__sort_params[sort_type] if sort_type \
            and sort_type in self.__sort_params else None
        p_query = " ".join(x for x in [query, p_rating, p_sort] if x)
        query_params = {
            "tags": p_query,
            "limit": count if count < PER_PAGE_MAX else PER_PAGE_MAX
        }

        json_response = send_api_request(ENDPOINT, query_params)
        for post in json_response["posts"]:
            post["tags"]["rating"] = post["rating"]
        return {
            "source": "e621",
            "query": p_query,
            "raw_tags": [x["tags"] for x in json_response["posts"]]
        }

    def __filter_raw_tags(self, categories, raw_image_tags):
        filtered_tags = {}
        for category in categories:
            if category not in self.__filtered_tags.keys():
                filtered_tags[category] = raw_image_tags[category]
            else:
                filtered_tags[category] = [
                    x for x in raw_image_tags[category]
                    if not glob_match(x, self.__filtered_tags[category])
                ]
        return filtered_tags

    @formatter("Pony Diffusion V5")
    def derpi(self, raw_image_tags):
        t = self.__filter_raw_tags(
            ["character", "species", "general", "meta"],
            raw_image_tags
        )
        rating = self.__ratings["pdv5"][raw_image_tags["rating"]]
        return [rating] + [x.replace("_", " ") for x in t["character"]
                           + t["species"] + t["general"] + t["meta"]]

    @formatter("EasyFluff")
    def easyfluff_format(self, raw_image_tags):
        t = self.__filter_raw_tags(
            ["character", "species", "general", "artist", "copyright", "meta"],
            raw_image_tags
        )
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["general"] + [f"by {x}" for x in t["artist"]]
                + t["copyright"] + t["meta"]]

    @formatter("EasyFluff (no aritst names)")
    def easyfluff_no_artist_format(self, raw_image_tags):
        t = self.__filter_raw_tags(
            ["character", "species", "general", "copyright", "meta"],
            raw_image_tags
        )
        return [x.replace("_", " ") for x in t["character"] + t["species"]
                + t["general"] + t["copyright"] + t["meta"]]
