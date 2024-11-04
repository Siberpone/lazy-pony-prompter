from lpp.log import get_logger
from abc import ABC, abstractmethod
from lpp.data import TagData, TagGroups, FilterData
from dataclasses import asdict
import requests
import os
import json


def formatter(model_name: str) -> callable:
    def inner(func: callable) -> callable:
        func.is_formatter = True
        func.model_name = model_name
        return func
    return inner


def default_formatter(model_name: str) -> callable:
    def inner(func: callable) -> callable:
        func = formatter(model_name)(func)
        func.is_default_formatter = True
        return func
    return inner


def attach_query_param(name: str, display_name: str) -> callable:
    def inner(func: callable) -> callable:
        func.attached_param = name
        func.display_name = display_name
        return func
    return inner


class TagSourceBase(ABC):
    def __init__(self,
                 syntax_help_url: str = "",
                 query_hint: str = "",
                 work_dir: str = "."):
        self._work_dir: str = work_dir
        self._logger = get_logger()
        self.syntax_help_url = syntax_help_url
        self.query_hint = query_hint
        self.formatters: dict[str:callable] = {}
        self.default_formatter: callable = None
        self.extra_query_params: dict[str:callable] = {}
        for attr in [x for x in dir(self) if not x.startswith("_")]:
            obj = getattr(self, attr)
            if hasattr(obj, "is_formatter"):
                self.formatters[obj.model_name] = obj
            if hasattr(obj, "is_default_formatter"):
                self.default_formatter = obj
            if hasattr(obj, "attached_param"):
                self.extra_query_params[obj.attached_param] = obj

    def _send_api_request(
        self, endpoint: str, query_params: dict[str:str],
        user_agent: str = "lazy-pony-prompter (by user Siberpone)/v1.1.x"
    ) -> dict[str:object]:
        TIMEOUTS = (9.1, 15.1)
        req = requests.get(
            endpoint,
            query_params,
            timeout=TIMEOUTS,
            headers={"User-Agent": user_agent}
        )
        req.raise_for_status()
        return req.json()

    def _get_config(self) -> dict[str:object]:
        name = self.__class__.__name__.lower()
        config_file = os.path.join(self._work_dir, "config", f"{name}.json")
        with open(config_file, encoding="utf-8") as f:
            config_entry = json.load(f)
        return config_entry

    @property
    def supported_models(self) -> list[str]:
        return list(self.formatters.keys())

    @abstractmethod
    def get_lpp_rating(self, tag_data: TagData):
        pass

    @abstractmethod
    def request_tags(self, query: str, count: int, *params: object) -> TagData:
        pass

    @abstractmethod
    def _convert_raw_tags(self, raw_tags: list[object]) -> TagGroups:
        pass


class Tags:
    def __init__(self, tag_groups: TagGroups):
        self.__tag_groups: dict[str:list[str]] = asdict(tag_groups)

    def select(self, *groups: str):
        self.__tag_groups = {
            k: v if k in groups else [] for k, v in self.__tag_groups.items()
        }
        return self

    def modify(self, modifier: callable, *groups: str):
        if not groups:
            groups = set(self.__tag_groups.keys())
        for group in groups:
            self.__tag_groups[group] = [
                modifier(tag) for tag in self.__tag_groups[group]
            ]
        return self

    def replace_underscores(self, replace: bool = True, exclude: list[str] = []):
        if not replace:
            return self
        self.__tag_groups = {
            k: [
                x.replace("_", " ") if k not in exclude else x for x in v
            ] for k, v in self.__tag_groups.items()
        }
        return self

    def escape_parentheses(self, escape: bool = True):
        if not escape:
            return self
        self.__tag_groups = {
            k: [
                x.replace("(", "\\(").replace(")", "\\)") for x in v
            ] for k, v in self.__tag_groups.items()
        }
        return self

    def filter(self, *filters: FilterData):
        if not filters:
            return self

        filtered_tags = {}
        joint_filter = FilterData.merge(*filters)
        for group, tags in self.__tag_groups.items():
            filtered_tags[group] = []
            for tag in tags:
                subst = joint_filter.match_subst(tag)
                if subst:
                    filtered_tags[group].append(subst)
                    continue
                if not joint_filter.match(tag):
                    filtered_tags[group].append(tag)
        self.__tag_groups = filtered_tags
        return self

    def as_tag_groups(self):
        return TagGroups(**self.__tag_groups)

    def as_flat_groups(self, sep: str = ", "):
        return {k: sep.join(v) for k, v in self.__tag_groups.items()}
