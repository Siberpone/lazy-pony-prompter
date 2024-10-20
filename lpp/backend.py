from copy import deepcopy
from dataclasses import asdict
from lpp.log import get_logger
from lpp.sources import TagSourceBase
from lpp.utils import TagData, FilterData, Models
from os import path
from random import sample
from abc import ABC, abstractmethod
import pickle
import re

logger = get_logger()


class SourcesManager:
    def __init__(
        self, work_dir: str = ".", sources: list[TagSourceBase] = None
    ):
        self.__work_dir: str = work_dir
        self.sources: dict[str:TagSourceBase] = self.__load_sources(sources)

    def __load_sources(
        self, sources: list[TagSourceBase]
    ) -> dict[str:TagSourceBase]:
        s = sources if sources else TagSourceBase.__subclasses__()
        return {x.__name__: x(self.__work_dir) for x in s}

    def get_source_names(self) -> list[str]:
        return list(self.sources.keys())

    def request_prompts(self, source: str, *args: object) -> None:
        return self.sources[source].request_tags(*args)


class PromptsManager:
    def __init__(self, sources_manager: SourcesManager):
        self.__sm = sources_manager
        self.tag_data: TagData = None

    def __replace_tokens(self, flat_groups: dict[str:str], template: str) -> str:
        result = template
        for token, prompt_fragment in flat_groups.items():
            result = result.replace(f"{{{token}}}", prompt_fragment)
        return result

    def __apply_template(self,
                         tag_groups: dict[str:list[str]],
                         default_template: str,
                         template: str = None,
                         sep: str = ", ",
                         sanitize: bool = True) -> str:
        escaped_tag_groups = {
            k: [x.replace("(", "\\(").replace(")", "\\)") for x in v] for k, v in tag_groups.items()
        }
        flat_groups = {k: sep.join(v) for k, v in escaped_tag_groups.items()}
        tokens = set(tag_groups.keys())
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
            prompt = re.sub(" +", " ", prompt)
            prompt = re.sub(r"(, )\1+", r"\1", prompt)
            prompt = re.sub("^, *", "", prompt)
            prompt = re.sub(", *$", "", prompt)

        return prompt

    def __filter_tags_legacy(self, tag_groups: dict[str:list[str]], filter_str: str):
        # INFO: this old filtering method is left for compatibility and
        # will be removed in the future.
        tag_filter = FilterData.from_string(filter_str, ",")
        return {k: [
                    x for x in v if not tag_filter.match(x)
                ] for k, v in tag_groups.items()}

    def __filter_tags(self, tag_groups: dict[str:list[str]], filters: list[FilterData]):
        if not filters:
            return tag_groups

        filtered_tags = {}
        joint_filter = FilterData.merge(*filters)
        for group, tags in tag_groups.items():
            filtered_tags[group] = []
            for tag in tags:
                if joint_filter.match_subst(tag):
                    filtered_tags[group].append(joint_filter.substitutions[tag])
                    continue
                if not joint_filter.match(tag):
                    filtered_tags[group].append(tag)
        return filtered_tags

    def choose_prompts(self,
                       model: str,
                       template: str = None,
                       n: int = 1,
                       tag_filter_str: str = "",
                       allowed_ratings: list[str] = None,
                       filters: list[FilterData] = None
                       ) -> list[list[str]]:
        if not self.tag_data:
            raise ValueError("No prompts are currently loaded.")

        raw_tags = self.tag_data.raw_tags
        source = self.__sm.sources[self.tag_data.source]

        # TODO: get rid of magical constants and refactor LPP ratings with
        # enum or, possibly, a class
        if allowed_ratings and len(allowed_ratings) < 3:
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
            formatted_tags = asdict(format_func(raw_tags))
            filtered_tags = self.__filter_tags_legacy(formatted_tags, tag_filter_str)\
                if tag_filter_str\
                else self.__filter_tags(formatted_tags, filters)
            processed_prompts.append(
                self.__apply_template(
                    filtered_tags, Models.get_default_template(model), template
                )
            )
        return processed_prompts

    def get_loaded_prompts_count(self) -> int:
        return len(self.tag_data.raw_tags) if self.tag_data else 0


class LppDataManager(ABC):
    def __init__(self, cache_file: str, work_dir: str = "."):
        self._cache_file = cache_file
        self._work_dir: str = work_dir
        self._data: dict[str:object] = self._load_cache()

    def _load_cache(self) -> dict[str:object]:
        cache_file = path.join(self._work_dir, self._cache_file)
        if not path.exists(cache_file):
            return {}

        with open(cache_file, "rb") as f:
            try:
                return pickle.load(f)
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

    def get_item(self, name: str) -> object:
        if name not in self._data:
            raise KeyError(f"No name '{name}' in cache")
        return deepcopy(self._data[name])

    def delete_item(self, name: str) -> None:
        if name not in self._data:
            raise KeyError(f"No name '{name}' in cache")
        del self._data[name]
        self._dump_cache()


class CacheManager(LppDataManager):
    def __init__(self, work_dir: str = "."):
        super().__init__("tag_cache.dat", work_dir)

    def get_saved_names(self, source: str = None) -> list[str]:
        if not source:
            return list(self._data.keys())
        return [
            k for k, v in self._data.items() if v.source == source
        ]

    def save_item(self,
                  name: str,
                  data: TagData,
                  tag_filter: str = None,
                  filters: list[str] = None) -> None:
        if not name:
            raise ValueError("Empty \"name\" parameter")
        new_item = deepcopy(data)
        if filters is not None:
            new_item.other_params["filters"] = deepcopy(filters)

        self._data[name] = new_item
        self._dump_cache()

    def extract_legacy_filters(self) -> dict[str:FilterData]:
        converted_filters = {}
        LEGACY_FILTER = "tag_filter"
        NEW_FILTER = "filters"
        for name, tag_data in self._data.items():
            filter_name = f"[F] {name}"
            params = tag_data.other_params
            if LEGACY_FILTER in params and params[LEGACY_FILTER]:
                converted_filters[filter_name] = \
                    FilterData.from_string(params[LEGACY_FILTER], ",")
                if NEW_FILTER in params and filter_name not in params[NEW_FILTER]:
                    params[NEW_FILTER] += [filter_name]
                else:
                    params[NEW_FILTER] = [filter_name]
        self._dump_cache()
        return converted_filters

    # INFO: Left these for compatibility
    def cache_tag_data(
        self, name: str, data: TagData, tag_filter: str = None
    ) -> None:
        self.save_item(name, data, tag_filter)

    def get_tag_data(self, name: str) -> TagData:
        return self.get_item(name)

    def delete_tag_data(self, name: str) -> None:
        self.delete_item(name)


class FiltersManager(LppDataManager):
    def __init__(self, work_dir: str = "."):
        super().__init__("filters.dat", work_dir)

    def save_item(self, name: str, data: FilterData):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        new_item = deepcopy(data)
        self._data[name] = new_item
        self._dump_cache()

    def get_filter_names(self) -> list[str]:
        return list(self._data.keys())

    def import_filters(self, filters: dict[str:FilterData]) -> int:
        count = 0
        for name, lpp_filter in filters.items():
            if name not in self._data.keys():
                self.save_item(name, lpp_filter)
                count += 1
        return count
