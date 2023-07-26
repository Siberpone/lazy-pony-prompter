from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import time
import os


def send_api_request(endpoint, query):
    url = "?".join([endpoint, urlencode(query)])
    req = Request(url)
    req.add_header("User-Agent", "urllib")
    with urlopen(req) as response:
        return json.load(response)


def send_paged_api_request(endpoint,
                           query_params,
                           root_selector_func,
                           item_selector_func=lambda x: x,
                           max_items=None,
                           query_delay=0.5,
                           verbose=False
                           ):
    def report(message):
        if verbose:
            print(message)

    if "per_page" in query_params.keys():
        per_page = query_params["per_page"]
    else:
        per_page = 50
        query_params["per_page"] = per_page

    items = []

    report("Sending query...")
    query_params["page"] = 1
    json_response = send_api_request(endpoint, query_params)
    items += [item_selector_func(x) for x in root_selector_func(json_response)]

    total = json_response["total"]
    if max_items is not None and max_items < total:
        pages_to_load = (max_items // per_page) + (1 if max_items % per_page > 0 else 0)
        report(f"Success! A total of {max_items} items on {pages_to_load} pages will be fetched.")
    else:
        pages_to_load = (total // per_page) + (1 if total % per_page > 0 else 0)
        report(f"Success! A total of {total} items on {pages_to_load} pages will be fetched.")

    for p in range(2, pages_to_load + 1):
        time.sleep(query_delay)
        report(f"Fetching page {p}")
        query_params["page"] = p
        json_response = send_api_request(endpoint, query_params)
        items += [item_selector_func(x) for x in root_selector_func(json_response)]

    report("Done!")
    return items if max_items is None or max_items >= total else items[:max_items]


def update_legacy_tag_filter(working_path):
    user_config_file = os.path.join(
        working_path, "config", "my_filtered_tags.json"
    )
    if os.path.exists(user_config_file):
        with open(user_config_file, "r+") as f:
            user_config_entry = json.load(f)
            if isinstance(user_config_entry, list):
                f.seek(0)
                f.truncate()
                user_config_entry = {"exact": user_config_entry}
                json.dump(user_config_entry, f, indent=4)


def get_merged_config_entry(entry, working_path):
    def merge_dicts(target, replacement):
        for key, val in replacement.items():
            if key not in target:
                target[key] = val
                continue

            if isinstance(val, dict):
                merge_dicts(target[key], val)
            else:
                if isinstance(target[key], list):
                    target[key] += val
                    target[key] = set(target[key])
                else:
                    target[key] = val
        return target

    config_file = os.path.join(
        working_path, "config", f"{entry}.json"
    )
    user_config_file = os.path.join(
        working_path, "config", f"my_{entry}.json"
    )
    with open(config_file) as f:
        config_entry = json.load(f)
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            user_config_entry = json.load(f)
            config_entry = merge_dicts(config_entry, user_config_entry)
    return config_entry
