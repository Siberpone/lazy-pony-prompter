from lpp.log import get_logger
from abc import ABC, abstractmethod
from lpp.utils import TagData
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


class TagSourceBase(ABC):
    def __init__(self, work_dir: str = "."):
        self._work_dir: str = work_dir
        self._logger = get_logger()
        self.formatters: dict[str:callable] = {}
        self.default_formatter: callable = None
        for attr in [x for x in dir(self) if not x.startswith("_")]:
            obj = getattr(self, attr)
            if hasattr(obj, "is_formatter"):
                self.formatters[obj.model_name] = obj
            if hasattr(obj, "is_default_formatter"):
                self.default_formatter = obj

    def _send_api_request(
        self, endpoint: str, query_params: dict[str:str],
        user_agent: str = "lazy-pony-prompter (by user Siberpone)/v1.0.0"
    ) -> dict[str:object]:
        TIMEOUTS = (3.1, 9.1)
        req = requests.get(
            endpoint,
            query_params,
            timeout=TIMEOUTS,
            headers={"User-Agent": user_agent}
        )
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
