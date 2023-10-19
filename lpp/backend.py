from random import choices
from lpp.utils import glob_match
from dataclasses import dataclass
import pickle
import importlib.util
import glob
import os
import copy


@dataclass
class SourceData():
    instance: object
    pretty_name: str
    models: dict


@dataclass
class TagData():
    source: str
    query: str
    raw_tags: list
    other_params: dict


class SourcesManager():
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.tag_data: TagData = None
        self.sources: dict[str:SourceData] = self.__load_sources()
        self.__source_names: dict[str:str] = {
            self.sources[x].pretty_name: x for x in self.sources
        }

    def __load_sources(self) -> dict[str:SourceData]:
        sources_dir = os.path.join(self.__work_dir, "sources")
        source_files = glob.glob("*.py", root_dir=sources_dir)
        sources = {}
        for file in source_files:
            source_name = file.split(".")[0]
            filepath = os.path.join(sources_dir, file)
            spec = importlib.util.spec_from_file_location(
                source_name, filepath)
            source = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(source)
            instance = source.TagSource(self.__work_dir)

            source_models = {}
            for attr in [x for x in dir(instance) if not x.startswith("_")]:
                obj = getattr(instance, attr)
                if hasattr(obj, "is_formatter"):
                    source_models[obj.pretty_model_name] = obj

            sources[source_name] = SourceData(
                instance,
                instance.pretty_name,
                source_models
            )
        return sources

    def __resolve_source_name(self, source_name: str) -> str:
        if source_name in self.sources:
            return source_name
        if source_name in self.__source_names:
            return self.__source_names[source_name]
        raise KeyError("No such source: \"{source_name}\"")

    def get_sources(self) -> list[str]:
        return [x.pretty_name for x in self.sources.values()]

    def get_models(self, source: str = None) -> list[str]:
        source_name = self.tag_data.source if source is None \
            else self.__resolve_source_name(source)
        return list(self.sources[source_name].models.keys())

    def request_prompts(self, source: str, *args) -> None:
        self.tag_data = self.sources[
            self.__resolve_source_name(source)
        ].instance.request_tags(*args)

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


class CacheManager():
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.__tag_data_cache: dict[str:list[TagData]] = self.__load_cache()

    def __load_cache(self) -> dict[str:list[TagData]]:
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

    def get_collection_names(self) -> list[str]:
        return list(self.__tag_data_cache.keys())

    def cache_tag_data(
            self, name: str, data: TagData, tag_filter: str = None) -> None:
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
