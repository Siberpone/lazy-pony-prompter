from random import choices
from lpp.sources import TagSourceBase
from lpp.utils import TagData, glob_match
import pickle
import shutil
import json
import os
import copy


class SourcesManager:
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.tag_data: TagData = None
        self.sources: dict[str:TagSourceBase] = self.__load_sources()

    def __load_sources(self) -> dict[str:TagSourceBase]:
        return {x.__name__: x(self.__work_dir)
                for x in TagSourceBase.__subclasses__()}

    def get_source_names(self) -> list[str]:
        return list(self.sources.keys())

    def request_prompts(self, source: str, *args: object) -> None:
        self.tag_data = self.sources[source].request_tags(*args)

    def choose_prompts(
            self, model: str, n: int = 1, tag_filter_str: str = ""
    ) -> list[list[str]]:
        chosen_prompts = choices(self.tag_data.raw_tags, k=n)

        source = self.tag_data.source
        format_func = self.sources[source].models[model]

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
        old_cache_file = os.path.join(self.__work_dir, "cache.json")
        new_cache_file = os.path.join(self.__work_dir, "tag_cache.dat")
        if not os.path.exists(old_cache_file) or os.path.exists(new_cache_file):
            return

        backup_cache_file = os.path.join(
            self.__work_dir, "cache.231021.bak.json"
        )
        if not os.path.exists(backup_cache_file):
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
        self.__convert_legacy_cache_file()

        cache_file = os.path.join(self.__work_dir, "tag_cache.dat")
        if not os.path.exists(cache_file):
            return {}

        with open(cache_file, "rb") as f:
            try:
                return pickle.load(f)
            except Exception as e:
                return {}

    def __dump_cache(self) -> None:
        cache_file = os.path.join(self.__work_dir, "tag_cache.dat")
        with open(cache_file, "wb") as f:
            pickle.dump(self.__tag_data_cache, f)

    def get_saved_names(self) -> list[str]:
        return list(self.__tag_data_cache.keys())

    def cache_tag_data(
        self, name: str, data: TagData, tag_filter: str = None
    ) -> None:
        if not name:
            raise ValueError("Empty \"name\" parameter")
        tag_data = copy.deepcopy(data)
        tag_data.other_params["tag_filter"] = tag_filter if tag_filter else ""

        self.__tag_data_cache[name] = tag_data
        self.__dump_cache()

    def get_tag_data(self, name: str) -> TagData:
        if name not in self.__tag_data_cache:
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        return copy.deepcopy(self.__tag_data_cache[name])

    def delete_tag_data(self, name: str) -> None:
        if name not in self.__tag_data_cache:
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        del self.__tag_data_cache[name]
        self.__dump_cache()
