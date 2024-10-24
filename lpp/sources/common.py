from lpp.log import get_logger
from abc import ABC, abstractmethod
from lpp.data import TagData
import requests


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
        user_agent: str = "lazy-pony-prompter (by user Siberpone)/v1.0.0"
    ) -> dict[str:object]:
        TIMEOUTS = (6.1, 9.1)
        req = requests.get(
            endpoint,
            query_params,
            timeout=TIMEOUTS,
            headers={"User-Agent": user_agent}
        )
        req.raise_for_status()
        return req.json()

    @property
    def supported_models(self) -> list[str]:
        return list(self.formatters.keys())

    @abstractmethod
    def get_lpp_rating(self, tag_data: TagData):
        pass

    @abstractmethod
    def request_tags(self, query: str, count: int, *params: object) -> TagData:
        pass
