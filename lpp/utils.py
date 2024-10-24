from abc import ABC, abstractmethod
from lpp.log import get_logger
import os
import json
import fnmatch

logger = get_logger()


class LppMessageService(ABC):
    @abstractmethod
    def info(self, message: str): pass

    @abstractmethod
    def warning(self, message: str): pass

    @abstractmethod
    def error(self, message: str): pass


class DefaultLppMessageService(LppMessageService):
    def info(self, message: str) -> None:
        logger.info(message)

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.error(message)


def glob_match(term: str, patterns: list[str]) -> bool:
    return any([fnmatch.fnmatch(term, x) for x in patterns])


def get_config(name: str, work_dir: str = "config") -> dict[str:object]:
    config_file = os.path.join(work_dir, f"{name}.json")
    with open(config_file) as f:
        config_entry = json.load(f)
    return config_entry
