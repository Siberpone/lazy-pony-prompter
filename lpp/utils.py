from abc import ABC, abstractmethod
from lpp.log import get_logger

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
