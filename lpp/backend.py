from copy import deepcopy
from lpp.log import get_logger
from lpp.sources import TagSourceBase
from lpp.utils import TagData, glob_match
from os import path
from random import choices
import json
import pickle
import shutil

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

    def choose_prompts(
            self, model: str, n: int = 1, tag_filter_str: str = ""
    ) -> list[list[str]]:
        chosen_prompts = choices(self.tag_data.raw_tags, k=n)

        source = self.tag_data.source
        format_func = self.__sm.sources[source].formatters[model]

        extra_tag_filter = {
            t.strip() for t in tag_filter_str.split(",") if t
        }

        processed_prompts = []
        for prompt_core in chosen_prompts:
            formatted_prompt = format_func(prompt_core)
            filtered_prompt = [
                t for t in formatted_prompt
                if not glob_match(t, extra_tag_filter)
            ]
            processed_prompts.append(
                ", ".join(filtered_prompt)
                    .replace("(", "\\(")
                    .replace(")", "\\)")
            )
        return processed_prompts

    def get_loaded_prompts_count(self) -> int:
        return len(self.tag_data.raw_tags) if self.tag_data else 0


class CacheManager:
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.__tag_data_cache: dict[str:list[TagData]] = self.__load_cache()

    def __convert_legacy_cache_file(self):
        old_cache_file = path.join(self.__work_dir, "cache.json")
        new_cache_file = path.join(self.__work_dir, "tag_cache.dat")
        if not path.exists(old_cache_file) or path.exists(new_cache_file):
            return

        backup_cache_file = path.join(
            self.__work_dir, "cache.231021.bak.json"
        )
        if not path.exists(backup_cache_file):
            shutil.copy(old_cache_file, backup_cache_file)

        new_cache = {}
        source_lookup = {"derpi": "Derpibooru", "e621": "E621"}
        with open(old_cache_file, "r") as f:
            cache_json = json.load(f)
            for name, tag_data in cache_json.items():
                other_params = {
                    k: v for k, v in tag_data.items()
                    if k not in ["source", "raw_tags", "query"]
                }
                new_cache[name] = TagData(
                    source_lookup[tag_data["source"]],
                    tag_data["query"],
                    tag_data["raw_tags"],
                    other_params
                )
        with open(new_cache_file, "wb") as f:
            pickle.dump(new_cache, f)

    def __load_cache(self) -> dict[str:list[TagData]]:
        # INFO: Convert old cache file to new format. This will be removed
        # after some time.
        try:
            self.__convert_legacy_cache_file()
        except Exception:
            logger.exception(
                "Error occured while trying to convert old cache file",
                exc_info=True
            )
            return {}

        cache_file = path.join(self.__work_dir, "tag_cache.dat")
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

    def __dump_cache(self) -> None:
        cache_file = path.join(self.__work_dir, "tag_cache.dat")
        with open(cache_file, "wb") as f:
            pickle.dump(self.__tag_data_cache, f)

    def get_saved_names(self, source: str = None) -> list[str]:
        if not source:
            return list(self.__tag_data_cache.keys())
        return [
            k for k, v in self.__tag_data_cache.items() if v.source == source
        ]

    def cache_tag_data(
        self, name: str, data: TagData, tag_filter: str = None
    ) -> None:
        if not name:
            raise ValueError("Empty \"name\" parameter")
        tag_data = deepcopy(data)
        tag_data.other_params["tag_filter"] = tag_filter if tag_filter else ""

        self.__tag_data_cache[name] = tag_data
        self.__dump_cache()

    def get_tag_data(self, name: str) -> TagData:
        if name not in self.__tag_data_cache:
            raise KeyError(f"No name '{name}' in cache")
        return deepcopy(self.__tag_data_cache[name])

    def delete_tag_data(self, name: str) -> None:
        if name not in self.__tag_data_cache:
            raise KeyError(f"No name '{name}' in cache")
        del self.__tag_data_cache[name]
        self.__dump_cache()
