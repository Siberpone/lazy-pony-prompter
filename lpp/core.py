from copy import deepcopy
from lpp.log import get_logger
from lpp.sources.common import TagSourceBase
from lpp.sources import *
from lpp.data import TagData, FilterData, Models, Ratings
from lpp.formatting import Tags
from os import path
from random import sample
from abc import ABC, abstractmethod
import pickle
import re

logger = get_logger()


def get_sources(work_dir: str = ".") -> dict[str:TagSourceBase]:
    return {x.__name__: x(work_dir) for x in TagSourceBase.__subclasses__()}


class PromptsManager:
    def __init__(self, sources: dict[str:TagSourceBase]):
        self.__sources: dict[str:TagSourceBase] = sources
        self.tag_data: TagData = None

    def __replace_tokens(self, flat_groups: dict[str:str], template: str) -> str:
        result = template
        for token, prompt_fragment in flat_groups.items():
            result = result.replace(f"{{{token}}}", prompt_fragment)
        return result

    def __apply_template(self,
                         flat_groups: dict[str:str],
                         default_template: str,
                         template: str = None,
                         sep: str = ", ",
                         sanitize: bool = True) -> str:
        tokens = set(flat_groups.keys())
        prompt = ""

        if template:
            if "{prompt}" in template:
                for token in tokens:
                    template = template.replace(f"{{{token}}}", "")
                template = template.replace("{prompt}", default_template)
                prompt = self.__replace_tokens(flat_groups, template)
            elif any(f"{{{x}}}" in template for x in tokens):
                for token in tokens:
                    prompt = self.__replace_tokens(flat_groups, template)
            else:
                prompt = self.__replace_tokens(
                    flat_groups, sep.join([default_template, template])
                )
        else:
            prompt = self.__replace_tokens(flat_groups, default_template)

        if sanitize:
            rules = {
                " +": " ",
                r"(, )\1+": r"\1",
                "^, +": "",
                ", +$": ""
            }
            for re_pattern, replacement in rules.items():
                prompt = re.sub(re_pattern, replacement, prompt)
        return prompt

    def choose_prompts(self,
                       model: str,
                       template: str = None,
                       n: int = 1,
                       allowed_ratings: list[str] = None,
                       filters: list[FilterData] = None
                       ) -> list[str]:
        if not self.tag_data:
            raise ValueError("No prompts are currently loaded.")

        raw_tags = self.tag_data.raw_tags
        source = self.__sources[self.tag_data.source]

        if allowed_ratings and len(allowed_ratings) < len(Ratings):
            raw_tags = [
                x for x in raw_tags if (source.get_lpp_rating(x) in allowed_ratings)
            ]
            if len(raw_tags) == 0:
                raise ValueError("Current collection doesn't seem to have prompts with selected rating(s).")

        # manually handle requests for more images than we have tags
        # because random.sample would raise a ValueError
        if n > len(raw_tags):
            factor = n // len(raw_tags) + 1  # +1 because // rounds down
            raw_tags = raw_tags * factor
        chosen_prompts = sample(raw_tags, k=n)

        format_func = source.formatters[model]\
            if model in source.supported_models\
            else source.default_formatter

        processed_prompts = []
        for raw_tags in chosen_prompts:
            formatted_tags = Tags(format_func(raw_tags))\
                .escape_parentheses()\
                .filter(*filters)\
                .as_flat_groups()
            processed_prompts.append(
                self.__apply_template(
                    formatted_tags, Models.get_default_template(model), template
                )
            )
        return processed_prompts

    @property
    def prompts_count(self) -> int:
        return len(self.tag_data.raw_tags) if self.tag_data else 0


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
