from dataclasses import dataclass
import enum
import os
import json
import fnmatch


@dataclass
class TagData:
    source: str
    query: str
    raw_tags: list
    other_params: dict


class Models(enum.Enum):
    PDV56 = "Pony Diffusion V5(.5)/V6"
    EF = "EasyFluff"


def glob_match(term: str, patterns: list[str]) -> bool:
    return any([fnmatch.fnmatch(term, x) for x in patterns])


def get_merged_config_entry(entry: str, work_dir: str = "config") -> dict:
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


def get_config(name: str, work_dir: str = "config") -> dict:
    config_file = os.path.join(work_dir, f"{name}.json")
    with open(config_file) as f:
        config_entry = json.load(f)
    return config_entry
