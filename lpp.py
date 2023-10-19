from random import choices
from lpp_utils import glob_match
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


class LazyPonyPrompter():
    def __init__(self, work_dir="."):
        self.__work_dir = work_dir
        self.__prompt_cache = self.__load_prompt_cache()
        self.sources = self.__load_sources()
        self.__source_names = {
            self.sources[x].pretty_name: x for x in self.sources
        }
        self.__prompts: TagData = None

    def __load_prompt_cache(self):
        cache_file = os.path.join(self.__work_dir, "tag_cache.dat")
        if not os.path.exists(cache_file):
            return {}

        with open(cache_file, "rb") as f:
            try:
                return pickle.load(f)
            except Exception as e:
                return {}

    def __load_sources(self):
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

    def __resolve_source_name(self, source_name):
        if source_name in self.sources:
            return source_name
        if source_name in self.__source_names:
            return self.__source_names[source_name]
        raise KeyError("No such source: \"{source_name}\"")

    def get_sources(self):
        return [x.pretty_name for x in self.sources.values()]

    def get_models(self, source=None):
        source_name = self.__prompts.source if source is None \
            else self.__resolve_source_name(source)
        return list(self.sources[source_name].models.keys())

    def request_prompts(self, source, *args):
        self.__prompts = self.sources[
            self.__resolve_source_name(source)
        ].instance.request_tags(*args)

    def choose_prompts(self, model, n=1, tag_filter_str=""):
        chosen_prompts = choices(self.__prompts.raw_tags, k=n)

        source = self.__prompts.source
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

    def get_loaded_prompts_count(self):
        return len(self.__prompts.raw_tags) if self.__prompts else 0

    def get_cached_prompts_names(self):
        return list(self.__prompt_cache.keys())

    def cache_current_prompts(self, name, tag_filter=None):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        prompts_data = copy.deepcopy(self.__prompts)
        prompts_data.other_params["tag_filter"] = tag_filter if tag_filter else ""

        self.__prompt_cache[name] = prompts_data
        self.__dump_prompts_cache()

    def load_cached_prompts(self, name):
        if name not in self.__prompt_cache:
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        self.__prompts = copy.deepcopy(self.__prompt_cache[name])

    def delete_cached_prompts(self, name):
        if name not in self.__prompt_cache:
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        del self.__prompt_cache[name]
        self.__dump_prompts_cache()

    def get_prompts_metadata(self, name=None):
        if name is None:
            if not self.__prompts:
                return {}
            p = self.__prompts
        else:
            if name in self.__prompt_cache:
                p = self.__prompt_cache[name]
            else:
                raise KeyError(f"Can't find \"{name}\" in prompts cache")
        return {
            "source": p.source,
            "query": p.query,
            "other_params": p.other_params,
            "count": len(p.raw_tags)
        }

    def __dump_prompts_cache(self):
        cache_file = os.path.join(self.__work_dir, "tag_cache.dat")
        with open(cache_file, "wb") as f:
            pickle.dump(self.__prompt_cache, f)
