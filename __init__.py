import sys
from os.path import dirname
from copy import deepcopy
LPP_ROOT_DIR = dirname(__file__)
sys.path.append(LPP_ROOT_DIR)

from .lpp.sources import Derpibooru, E621
from .lpp.backend import SourcesManager

sm = SourcesManager(LPP_ROOT_DIR)


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
                "step": 1,
                "display": "number"
            })
        }
    }

    def __init__(self, source):
        self._sm: SourcesManager = SourcesManager(LPP_ROOT_DIR, [source])

    RETURN_TYPES = ("STRING", "LPP_TAG_DATA")
    RETURN_NAMES = ("Prompt", "LPP Tag Data")
    CATEGORY = "LPP"
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
        types["required"]["format"] = (sm.sources["Derpibooru"].get_model_names(),)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_DERPIBOORU",)
        return types

    def get_prompt(
        self, query, count, filter, sort_by, format, tag_filter,
        send_request, tag_data=None, update_dummy=0
    ):
        if self._sm.get_loaded_prompts_count() == 0 or send_request:
            self._sm.request_prompts("Derpibooru", query, count, filter, sort_by)
        return (self._sm.choose_prompts(format, 1, tag_filter)[0], None)


class ComfyE621(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, E621)

    @classmethod
    def INPUT_TYPES(self):
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["rating"] = (sm.sources["E621"].get_ratings(),)
        types["required"]["sort_by"] = (sm.sources["E621"].get_sort_options(),)
        types["required"]["format"] = (sm.sources["E621"].get_model_names(),)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_E621",)
        return types

    def get_prompt(
        self, query, count, rating, sort_by, format, tag_filter,
        send_request, tag_data=None, update_dummy=0
    ):
        if self._sm.get_loaded_prompts_count() == 0 or send_request:
            self._sm.request_prompts("E621", query, count, rating, sort_by)
        return (self._sm.choose_prompts(format, 1, tag_filter)[0], None)


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

    def save_tag_data(self, tag_data, name, overwrite):
        pass


class LPPLoaderDerpibooru:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (["kek", "lol"],)
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_DERPIBOORU",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (None,)


class LPPLoaderE621:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (["kek", "lol"],)
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_E621",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (None,)


NODE_CLASS_MAPPINGS = {
    "LPP_Derpibooru": ComfyDerpibooru,
    "LPP_E621": ComfyE621,
    "LPP_Saver": LPPSaver,
    "LPP_Loader_Derpibooru": LPPLoaderDerpibooru,
    "LPP_Loader_E621": LPPLoaderE621
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LPP_Derpibooru": "LPP (Derpibooru)",
    "LPP_E621": "LPP (E621)",
    "LPP_Saver": "LPP Saver",
    "LPP_Loader_Derpibooru": "LPP Loader (Derpibooru)",
    "LPP_Loader_E621": "LPP Loader (E621)"
}
