from abc import ABC, abstractmethod
import logging

__logger = None


def __init_logger(level: int = logging.WARNING,
                  name: str = 'lpp') -> logging.Logger:
    formatter = logging.Formatter(
        "[LPP] %(levelname)s (%(module)s): %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    global __logger

    if __logger:
        return __logger
    else:
        __logger = __init_logger()
        return __logger


class LppMessageService(ABC):
    @abstractmethod
    def info(self, message: str): pass

    @abstractmethod
    def warning(self, message: str): pass

    @abstractmethod
    def error(self, message: str): pass


class DefaultLppMessageService(LppMessageService):
    logger = get_logger()

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)
