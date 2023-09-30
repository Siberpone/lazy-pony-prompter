from lpp_utils import *
from random import choices
import json
import importlib.util
import glob
import os


class LazyPonyPrompter():
    def __init__(self, working_path="."):
        self.__working_path = working_path
        self.__prompt_cache = self.__load_prompt_cache()
        self.sources = {}
        self.source_names = {}
        self.__load_sources()
        self.__prompts = {
            "source": "",
            "quiery": "",
            "filter_type": "",
            "sort_type": "",
            "raw_tags": []
        }

        config = self.__load_config()
        self.__ratings = config["ratings"]
        self.__character_tags = config["character_tags"]
        self.__prioritized_tags = config["prioritized_tags"]
        self.__filtered_tags = config["filtered_tags"]
        self.__negative_prompt = config["negative_prompt"]

    def __load_sources(self):
        source_dir = os.path.join(self.__working_path, "sources")
        source_files = glob.glob("*.py", root_dir=source_dir)
        for file in source_files:
            source_name = file.split(".")[0]
            filepath = os.path.join(source_dir, file)
            print(filepath)
            spec = importlib.util.spec_from_file_location(
                source_name,
                filepath
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.sources[source_name] = module.TagSource(self.__working_path)
            self.source_names[self.sources[source_name].pretty_name] = source_name

    def get_sources(self):
        return list(self.source_names.keys())

    def choose_prompts(self, n=1, prefix=None, suffix=None, tag_filter_str=""):
        extra_tag_filter = set(
            filter(None, [t.strip() for t in tag_filter_str.split(",")])
        )

        chosen_prompts = choices(self.__prompts["raw_tags"], k=n)
        processed_prompts = []
        for prompt_core in chosen_prompts:
            kek = self.__process_raw_tags(prompt_core)
            filtered_prompt = filter(
                lambda tag: tag not in extra_tag_filter,
                kek
            )
            processed_prompts.append(
                ", ".join(
                    filter(
                        None,
                        [
                            prefix,
                            ", ".join(filtered_prompt)
                                .replace("(", "\\(")
                                .replace(")", "\\)"),
                            suffix
                        ]
                    )
                )
            )
        return processed_prompts

    def get_loaded_prompts_count(self):
        return len(self.__prompts["raw_tags"])

    def get_negative_prompt(self):
        return self.__negative_prompt

    def get_cached_prompts_names(self):
        return list(self.__prompt_cache.keys())

    def cache_current_prompts(self, name, prefix=None,
                              suffix=None, tag_filter=None):
        if not name:
            raise ValueError("Empty \"name\" parameter")
        prompts_data = self.__prompts

        def set_param(param, key):
            prompts_data[key] = param if param else ""

        set_param(prefix, "prefix")
        set_param(suffix, "suffix")
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

    def request_prompts(self, source, *args):
        self.__prompts = self.sources[self.source_names[source]].request_tags(
            *args)

    def __load_config(self):
        p = self.__working_path
        config = get_merged_config_entry("lpp", p)
        config["prioritized_tags"] = get_merged_config_entry(
            "prioritized_tags", p
        )
        config["character_tags"] = get_merged_config_entry("character_tags", p)
        config["filtered_tags"] = get_merged_config_entry("filtered_tags", p)
        return config

    def __load_prompt_cache(self):
        cache_file = os.path.join(self.__working_path, "cache.json")
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                return json.load(f)
        else:
            return {}

    def __dump_prompts_cache(self):
        cache_file = os.path.join(self.__working_path, "cache.json")
        with open(cache_file, "w") as f:
            json.dump(self.__prompt_cache, f, indent=4)

    def __process_raw_tags(self, raw_image_tags):
        rating = None
        characters = []
        prioritized_tags = []
        prompt_tail = []
        for tag in raw_image_tags:
            if (any([tag.startswith(x) for x in self.__filtered_tags["starts_with"]])
                    or any([tag.endswith(x) for x in self.__filtered_tags["ends_with"]])
                    or tag in self.__filtered_tags["exact"]):
                continue
            if rating is None and tag in self.__ratings.keys():
                rating = self.__ratings[tag]
                continue
            if tag in self.__character_tags:
                characters.append(tag)
                continue
            if tag in self.__prioritized_tags:
                prioritized_tags.append(tag)
                continue
            prompt_tail.append(tag)
        return ([] if rating is None else [rating]) \
            + characters + prioritized_tags + prompt_tail
