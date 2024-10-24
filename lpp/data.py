from dataclasses import dataclass
from lpp.utils import glob_match
import enum


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

    def match_subst(self, term: str) -> bool:
        return glob_match(term, self.substitutions.keys())

    def match(self, term: str) -> bool:
        return glob_match(term, self.patterns)
