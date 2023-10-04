from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import os
import shutil


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


def formatter(pretty_model_name):
    def inner(func):
        func.is_formatter = True
        func.pretty_model_name = pretty_model_name
        return func
    return inner


def update_legacy_prompt_cache(working_path):
    cache_file = os.path.join(working_path, "cache.json")
    if not os.path.exists(cache_file):
        return

    backup_file = os.path.join(working_path, "cache.231002.bak.json")
    if not os.path.exists(backup_file):
        shutil.copy(cache_file, backup_file)

    if os.path.exists(cache_file):
        with open(cache_file, "r+") as f:
            try:
                cache_json = json.load(f)
            except Exception as e:
                return
            if "source" not in next(iter(cache_json.values())):
                for key in cache_json.keys():
                    if "source" not in cache_json[key].keys():
                        cache_json[key]["source"] = "derpi"
                    if "core" in cache_json[key].keys():
                        cache_json[key]["raw_tags"] = cache_json[key].pop(
                            "core")
                f.seek(0)
                f.truncate()
                json.dump(cache_json, f, indent=4)
