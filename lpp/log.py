import logging


def __init_logger(level: int = logging.WARNING,
                  name: str = 'root') -> logging.Logger:
    formatter = logging.Formatter(
        "[LPP] %(levelname)s (%(module)s): %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


__logger = __init_logger()


def get_logger():
    return __logger
