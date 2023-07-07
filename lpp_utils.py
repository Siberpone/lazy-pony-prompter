from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import time


def send_api_request(endpoint, query):
    url = "?".join([endpoint, urlencode(query)])
    req = Request(url)
    req.add_header("User-Agent", "urllib")
    with urlopen(req) as response:
        return json.load(response)


def get_character_tags(images_count=500, query_delay=0.5, selector="name"):
    def fetch_query_page(page=1):
        query_params = {
            "q": f"category:character, images.gte:{images_count}",
            "per_page": 50,
            "page": page
        }
        return send_api_request(
            "https://derpibooru.org/api/v1/json/search/tags",
            query_params
        )

    tags = []
    print("Sending query...")
    json_response = fetch_query_page()
    total = json_response["total"]
    page_count = (total // 50) + (1 if total % 50 > 0 else 0)
    tags += [x[selector] for x in json_response["tags"]]
    print(
        f"Success! A total of {total} tags on {page_count} pages will be fetched.")

    for p in range(2, page_count + 1):
        time.sleep(query_delay)
        print(f"Fetching page {p}")
        json_response = fetch_query_page(p)
        tags += [x[selector] for x in json_response["tags"]]

    print("Done!")
    return tags
