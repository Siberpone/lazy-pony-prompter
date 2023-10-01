from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import os


def send_api_request(endpoint, query_params,
                     user_agent="lazy-pony-prompter (by user Siberpone)"):
    url = "?".join([endpoint, urlencode(query_params)])
    req = Request(url)
    req.add_header("User-Agent", user_agent)
    with urlopen(req) as response:
        return json.load(response)


def get_merged_config_entry(entry, work_dir="config"):
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
        work_dir, f"{entry}.json"
    )
    user_config_file = os.path.join(
        work_dir, f"my_{entry}.json"
    )
    with open(config_file) as f:
        config_entry = json.load(f)
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            user_config_entry = json.load(f)
            config_entry = merge_dicts(config_entry, user_config_entry)
    return config_entry
