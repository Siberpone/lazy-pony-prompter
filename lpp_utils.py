from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import os
import shutil
import fnmatch


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


def get_config(name, work_dir="config"):
    config_file = os.path.join(work_dir, f"{name}.json")
    with open(config_file) as f:
        config_entry = json.load(f)
    return config_entry


def formatter(pretty_model_name):
    def inner(func):
        func.is_formatter = True
        func.pretty_model_name = pretty_model_name
        return func
    return inner


def glob_match(term, patterns):
    return any([fnmatch.fnmatch(term, x) for x in patterns])
