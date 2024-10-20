from dataclasses import dataclass
from abc import ABC, abstractmethod
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


@dataclass
class TagGroups:
    character: list[str]
    species: list[str]
    rating: list[str]
    artist: list[str]
    general: list[str]
    meta: list[str]


class Models(enum.Enum):
    PDV56 = "Pony Diffusion V5(.5)/V6"
    EF = "EasyFluff"
    SEAART = "SeaArt Furry v1.0"

    def get_default_template(model: str) -> str:
        if model == Models.SEAART.value:
            return "{species}, {character}, {artist}, {general}, {meta}"
        else:
            return "{rating}, {character}, {species}, {artist}, {general}, {meta}"


class LppMessageService(ABC):
    @abstractmethod
    def info(self, message: str): pass

    @abstractmethod
    def warning(self, message: str): pass

    @abstractmethod
    def error(self, message: str): pass


@dataclass
class FilterData:
    substitutions: dict[str:str]
    __patterns: dict[str:None]  # ordered set emulation

    @property
    def patterns(self):
        return self.__patterns.keys()

    @patterns.setter
    def patterns(self, value):
        self.__patterns = dict.fromkeys(value)

    def __post_init__(self):
        if self.__patterns is not dict:
            self.__patterns = dict.fromkeys(self.__patterns)

    def __str__(self):
        s = [f"{k}||{v}" for k, v in self.substitutions.items()]
        return "\n".join(s + list(self.patterns))

    @staticmethod
    def from_string(filter_string: str, sep: str = None):
        lines = {l.strip() for l in filter_string.split(sep) if l}\
            if sep else filter_string.splitlines()
        return FilterData.from_list(lines)

    @staticmethod
    def from_list(filter_patterns: list[str]):
        substitutions = {}
        patterns = []
        for p in filter_patterns:
            if "||" in p:
                pattern, substitution = p.split("||")[slice(2)]
                substitutions[pattern] = substitution
            else:
                patterns.append(p)
        return FilterData(substitutions, patterns)

    @staticmethod
    def merge(*filters):
        substitutions = {}
        patterns = []
        for filter in filters:
            substitutions = {**substitutions, **filter.substitutions}
            patterns += filter.patterns
        return FilterData(substitutions, patterns)

    def match_subst(self, term: str) -> bool:
        return glob_match(term, self.substitutions.keys())

    def match(self, term: str) -> bool:
        return glob_match(term, self.patterns)


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
