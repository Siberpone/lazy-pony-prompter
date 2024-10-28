from lpp.sources.common import TagSourceBase
from lpp.sources import *


def get_sources(work_dir: str = ".") -> dict[str:TagSourceBase]:
    return {x.__name__: x(work_dir) for x in TagSourceBase.__subclasses__()}
