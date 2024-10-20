import sys
from os.path import dirname
from copy import deepcopy
from random import randint
LPP_ROOT_DIR = dirname(__file__)
sys.path.append(LPP_ROOT_DIR)

from .lpp.sources import Derpibooru, E621
from .lpp.backend import SourcesManager, PromptsManager, CacheManager

sm = SourcesManager(LPP_ROOT_DIR)
cm = CacheManager(LPP_ROOT_DIR)


class ComfyTagSourceBase:
    tag_source_input_types_base = {
        "required": {
            "query": ("STRING", {
                "multiline": True
            }),
            "tag_filter": ("STRING", {
                "multiline": False
            }),
            "count": ("INT", {
                "default": 100,
                "min": 5,
                "max": 300,
                "step": 5,
                "display": "slider"
            }),
            "send_request": ("BOOLEAN", {
                "default": False
            })
        },
        "optional": {
            "update_dummy": ("INT", {
                "default": 0,
                "min": 0,
                "max": 0xffffffffffffffff,
            }),
            "prompt_template": ("STRING", {
                "multiline": False
            })
        }
    }

    def __init__(self, source):
        self._sm: SourcesManager = SourcesManager(LPP_ROOT_DIR, [source])
        self._pm: PromptsManager = PromptsManager(self._sm)

    RETURN_TYPES = ("STRING", "LPP_TAG_DATA")
    RETURN_NAMES = ("Prompt", "LPP Tag Data")
    CATEGORY = "LPP/sources"
    FUNCTION = "get_prompt"

    def get_prompt(self):
        pass


class ComfyDerpibooru(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, Derpibooru)

    @classmethod
    def INPUT_TYPES(self):
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["filter"] = (sm.sources["Derpibooru"].get_filters(),)
        types["required"]["sort_by"] = (sm.sources["Derpibooru"].get_sort_options(),)
        types["required"]["format"] = (sm.sources["Derpibooru"].supported_models,)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_DERPIBOORU",)
        return types

    def get_prompt(
        self, query, count, filter, sort_by, format, tag_filter,
        send_request, tag_data=None, update_dummy=0, prompt_template=""
    ):
        if tag_data:
            self._pm.tag_data = tag_data
        elif self._pm.get_loaded_prompts_count() == 0 or send_request:
            self._pm.tag_data = self._sm.request_prompts(
                "Derpibooru", query, count, filter, sort_by
            )
        return (
            self._pm.choose_prompts(format, prompt_template, 1, tag_filter)[0],
            (self._pm.tag_data, tag_filter)
        )


class ComfyE621(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, E621)

    @classmethod
    def INPUT_TYPES(self):
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["rating"] = (sm.sources["E621"].get_ratings(),)
        types["required"]["sort_by"] = (sm.sources["E621"].get_sort_options(),)
        types["required"]["format"] = (sm.sources["E621"].supported_models,)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_E621",)
        return types

    def get_prompt(
        self, query, count, rating, sort_by, format, tag_filter,
        send_request, tag_data=None, update_dummy=0, prompt_template=""
    ):
        if tag_data:
            self._pm.tag_data = tag_data
        elif self._pm.get_loaded_prompts_count() == 0 or send_request:
            self._pm.tag_data = self._sm.request_prompts(
                "E621", query, count, rating, sort_by
            )
        return (
            self._pm.choose_prompts(format, prompt_template, 1, tag_filter)[0],
            (self._pm.tag_data, tag_filter)
        )


class LPPSaver:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "tag_data": ("LPP_TAG_DATA",),
                "name": ("STRING", {
                    "multiline": False,
                }),
                "overwrite": ("BOOLEAN", {
                    "default": False
                })
            }
        }
    RETURN_TYPES = ()
    CATEGORY = "LPP"
    FUNCTION = "save_tag_data"
    OUTPUT_NODE = True

    def save_tag_data(self, tag_data, name, overwrite):
        existing_names = cm.get_saved_names()
        if (name in existing_names and overwrite) \
                or name not in existing_names:
            cm.cache_tag_data(name, tag_data[0], tag_data[1])
        return {}


class ForceRunBase:
    @classmethod
    def IS_CHANGED(self):
        return randint(0, 0xffffffffffffffff)


class LPPLoaderDerpibooru(ForceRunBase):
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (cm.get_saved_names("Derpibooru"),)
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_DERPIBOORU",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm.get_tag_data(collection_name),)


class LPPLoaderE621(ForceRunBase):
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (cm.get_saved_names("E621"),)
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_E621",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm.get_tag_data(collection_name),)


class LPPDeleter(ForceRunBase):
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (cm.get_saved_names(),)
            }
        }
    RETURN_TYPES = ()
    CATEGORY = "LPP"
    FUNCTION = "delete_tag_data"
    OUTPUT_NODE = True

    def delete_tag_data(self, collection_name):
        cm.delete_tag_data(collection_name)
        return {}


NODE_CLASS_MAPPINGS = {
    "LPP_Derpibooru": ComfyDerpibooru,
    "LPP_E621": ComfyE621,
    "LPP_Saver": LPPSaver,
    "LPP_Loader_Derpibooru": LPPLoaderDerpibooru,
    "LPP_Loader_E621": LPPLoaderE621,
    "LPP_Deleter": LPPDeleter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LPP_Derpibooru": "Derpibooru",
    "LPP_E621": "E621",
    "LPP_Saver": "Tag Data Saver",
    "LPP_Loader_Derpibooru": "Tag Data Loader (Derpibooru)",
    "LPP_Loader_E621": "Tag Data Loader (E621)",
    "LPP_Deleter": "Tag Data Deleter"
}
