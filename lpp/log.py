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


def get_logger():
    global __logger

    if __logger:
        return __logger
    else:
        __logger = __init_logger()
        return __logger
