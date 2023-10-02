from random import choices
from lpp_utils import update_legacy_prompt_cache
import fnmatch
import json
import importlib.util
import glob
import os


class LazyPonyPrompter():
    def __init__(self, work_dir="."):
        self.__work_dir = work_dir
        self.__prompt_cache = self.__load_prompt_cache()
        self.sources = self.__load_sources()
        self.source_names = {
            self.sources[x]["pretty_name"]: x for x in self.sources.keys()
        }
        self.__prompts = {
            "source": "",
            "quiery": "",
            "filter_type": "",
            "sort_type": "",
            "raw_tags": []
        }

    def __load_prompt_cache(self):

        # Update legacy cache file format
        update_legacy_prompt_cache(self.__work_dir)

        cache_file = os.path.join(self.__work_dir, "cache.json")
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                return json.load(f)
        else:
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
            for attr in filter(lambda x: not x.startswith("_"), dir(instance)):
                obj = getattr(instance, attr)
                if hasattr(obj, "is_formatter"):
                    source_models[obj.pretty_model_name] = obj

            sources[source_name] = {
                "instance": instance,
                "pretty_name": instance.pretty_name,
                "models": source_models
            }
        return sources

    def get_sources(self):
        return [x["pretty_name"] for x in self.sources.values()]

    def get_models(self, source):
        return list(self.sources[self.source_names[source]]["models"].keys())

    def request_prompts(self, source, *args):
        self.__prompts = self.sources[self.source_names[source]]["instance"].request_tags(
            *args)

    def choose_prompts(self, model, n=1, tag_filter_str=""):
        chosen_prompts = choices(self.__prompts["raw_tags"], k=n)

        source = self.__prompts["source"]
        format_func = self.sources[source]["models"][model]

        extra_tag_filter = set(
            filter(None, [t.strip() for t in tag_filter_str.split(",")])
        )

        processed_prompts = []
        for prompt_core in chosen_prompts:
            formatted_prompt = format_func(prompt_core)
            filtered_prompt = filter(
                lambda tag: not any(
                    [fnmatch.fnmatch(tag, x) for x in extra_tag_filter]
                ),
                formatted_prompt
            )
            processed_prompts.append(
                ", ".join(filtered_prompt)
                    .replace("(", "\\(")
                    .replace(")", "\\)")
            )
        return processed_prompts

    def get_loaded_prompts_count(self):
        return len(self.__prompts["raw_tags"])

    def get_cached_prompts_names(self):
        return list(self.__prompt_cache.keys())

    def cache_current_prompts(self, name, tag_filter=None):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        prompts_data = self.__prompts

        def set_param(param, key):
            prompts_data[key] = param if param else ""

        set_param(tag_filter, "tag_filter")
        self.__prompt_cache[name] = prompts_data
        self.__dump_prompts_cache()

    def load_cached_prompts(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        self.__prompts = self.__prompt_cache[name]

    def delete_cached_prompts(self, name):
        if name not in self.__prompt_cache.keys():
            raise KeyError(f"Can't find \"{name}\" in prompts cache")
        del self.__prompt_cache[name]
        self.__dump_prompts_cache()

    def get_prompts_metadata(self, name=None):
        if name is None:
            prompts_data = dict(self.__prompts)
        else:
            if name in self.__prompt_cache.keys():
                prompts_data = dict(self.__prompt_cache[name])
            else:
                raise KeyError(f"Can't find \"{name}\" in prompts cache")
        prompts_data["prompts_count"] = len(prompts_data["raw_tags"])
        del prompts_data["raw_tags"]
        return prompts_data

    def __dump_prompts_cache(self):
        cache_file = os.path.join(self.__work_dir, "cache.json")
        with open(cache_file, "w") as f:
            json.dump(self.__prompt_cache, f, indent=4)
