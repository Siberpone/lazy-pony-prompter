from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from lpp.log import get_logger
from os import path
import enum
import fnmatch
import pickle

logger = get_logger()


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
    ANIME = "Generic Anime"

    def get_default_template(model: str) -> str:
        if model == Models.SEAART.value:
            return "{species}, {character}, {artist}, {general}, {meta}"
        if model == Models.ANIME.value:
            return "{character}, {general}, {artist}, {meta}"
        else:
            return "{rating}, {character}, {species}, {artist}, {general}, {meta}"


class Ratings(enum.Enum):
    SAFE = "Safe"
    QUESTIONABLE = "Questionable"
    EXPLICIT = "Explicit"


@dataclass
class FilterData:
    substitutions: dict[str:str]
    __patterns: dict[str:None]  # ordered set emulation

    @property
    def patterns(self) -> list[str]:
        return self.__patterns.keys()

    @patterns.setter
    def patterns(self, value: str) -> None:
        self.__patterns = dict.fromkeys(value)

    def __post_init__(self) -> None:
        if self.__patterns is not dict:
            self.__patterns = dict.fromkeys(self.__patterns)

    def __str__(self) -> str:
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

    @staticmethod
    def glob_match(term: str, *patterns: str) -> bool:
        return any([fnmatch.fnmatch(term, x) for x in patterns])

    def match_subst(self, term: str) -> str:
        for pattern, substitution in self.substitutions.items():
            if FilterData.glob_match(term, pattern):
                return substitution
        return None

    def match(self, term: str) -> bool:
        return FilterData.glob_match(term, *self.patterns)


# HACK: Since "TagData" and "FilterData" were moved to a new module, they won't
# be deserializable from old pickle files, so we need a workaround.
class RenameUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        renamed_module = module
        if module == "lpp.utils" and (name == "TagData" or name == "FilterData"):
            renamed_module = "lpp.data"

        return super(RenameUnpickler, self).find_class(renamed_module, name)


class LppDataManager(ABC):
    def __init__(self, cache_file: str, work_dir: str = "."):
        self._cache_file = cache_file
        self._work_dir: str = work_dir
        self._data: dict[str:object] = self._load_cache()

    def __getitem__(self, name: str) -> object:
        if name not in self._data:
            raise KeyError(f"No name '{name}' in cache")
        return deepcopy(self._data[name])

    def _load_cache(self) -> dict[str:object]:
        cache_file = path.join(self._work_dir, self._cache_file)
        if not path.exists(cache_file):
            return {}

        with open(cache_file, "rb") as f:
            try:
                return RenameUnpickler(f).load()
            except Exception:
                logger.exception(
                    "Failed to unpickle cache file", exc_info=True
                )
                return {}

    def _dump_cache(self) -> None:
        cache_file = path.join(self._work_dir, self._cache_file)
        with open(cache_file, "wb") as f:
            pickle.dump(self._data, f)

    @abstractmethod
    def save_item(self, name: str, data: object, *args) -> None:
        pass

    def get_item_names(self, selector: callable = None) -> list[str]:
        if selector:
            return [k for k, v in self._data.items() if selector(k, v)]
        return list(self._data.keys())

    def delete_item(self, name: str) -> None:
        if name not in self._data:
            raise KeyError(f"No name '{name}' in cache")
        del self._data[name]
        self._dump_cache()


class CacheManager(LppDataManager):
    def __init__(self, work_dir: str = "."):
        super().__init__("tag_cache.dat", work_dir)

    def save_item(self,
                  name: str,
                  data: TagData,
                  filters: list[str] = None) -> None:
        if not name:
            raise ValueError("Empty \"name\" parameter")
        new_item = deepcopy(data)
        new_item.other_params["filters"] = deepcopy(filters) if filters else []

        self._data[name] = new_item
        self._dump_cache()


class FiltersManager(LppDataManager):
    def __init__(self, work_dir: str = "."):
        super().__init__("filters.dat", work_dir)

    def save_item(self, name: str, data: FilterData):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        new_item = deepcopy(data)
        self._data[name] = new_item
        self._dump_cache()

    def import_filters(self, filters: dict[str:FilterData]) -> int:
        count = 0
        for name, lpp_filter in filters.items():
            if name not in self._data.keys():
                self.save_item(name, lpp_filter)
                count += 1
        return count
