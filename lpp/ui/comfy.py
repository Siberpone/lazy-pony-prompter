import sys
import os.path as path
from copy import deepcopy

LPP_ROOT_DIR = path.join(path.dirname(__file__), "..", "..")
sys.path.append(LPP_ROOT_DIR)
print(LPP_ROOT_DIR)

from lpp.sources.common import TagSourceBase
from lpp.sources.derpibooru import Derpibooru
from lpp.sources.e621 import E621
from lpp.sources.danbooru import Danbooru
from lpp.core import PromptsManager, CacheManager, get_sources
from lpp.data import FilterData

lpp_sources = get_sources(LPP_ROOT_DIR)
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
                "max": 1500,
                "step": 5,
                "display": "slider"
            }),
            "send_request": ("BOOLEAN", {
                "default": False
            })
        },
        "optional": {
            "prompt_template": ("STRING", {
                "multiline": False
            })
        }
    }

    def __init__(self, source: TagSourceBase):
        self._source: TagSourceBase = source
        self._pm: PromptsManager = PromptsManager(
            {source.__class__.__name__: self._source}
        )

    RETURN_TYPES = ("STRING", "LPP_TAG_DATA")
    RETURN_NAMES = ("Prompt", "LPP Tag Data")
    CATEGORY = "LPP/sources"
    FUNCTION = "get_prompt"

    def get_prompt(self):
        pass

    @classmethod
    def IS_CHANGED(self, *args, **kwargs):
        return float("NaN")


class ComfyDerpibooru(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, Derpibooru(LPP_ROOT_DIR))

    @classmethod
    def INPUT_TYPES(self):
        s = lpp_sources["Derpibooru"]
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["filter"] = (s.get_filters(),)
        types["required"]["sort_by"] = (s.get_sort_options(),)
        types["required"]["format"] = (s.supported_models,)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_DERPIBOORU",)
        return types

    def get_prompt(
        self, query, count, filter, sort_by, format, tag_filter,
        send_request, tag_data=None, prompt_template=""
    ):
        if tag_data:
            self._pm.tag_data = tag_data
        elif self._pm.prompts_count == 0 or send_request:
            self._pm.tag_data = self._source.request_tags(
                query, count, filter, sort_by
            )
        tf = FilterData.from_string(tag_filter, ",")
        return (
            self._pm.choose_prompts(format, prompt_template, 1, None, [tf])[0],
            (self._pm.tag_data, tf)
        )


class ComfyE621(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, E621(LPP_ROOT_DIR))

    @classmethod
    def INPUT_TYPES(self):
        s = lpp_sources["E621"]
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["rating"] = (s.get_ratings(),)
        types["required"]["sort_by"] = (s.get_sort_options(),)
        types["required"]["format"] = (s.supported_models,)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_E621",)
        return types

    def get_prompt(
        self, query, count, rating, sort_by, format, tag_filter,
        send_request, tag_data=None, prompt_template=""
    ):
        if tag_data:
            self._pm.tag_data = tag_data
        elif self._pm.prompts_count == 0 or send_request:
            self._pm.tag_data = self._source.request_tags(
                query, count, rating, sort_by
            )
        tf = FilterData.from_string(tag_filter, ",")
        return (
            self._pm.choose_prompts(format, prompt_template, 1, None, [tf])[0],
            (self._pm.tag_data, tf)
        )


class ComfyDanbooru(ComfyTagSourceBase):
    def __init__(self):
        ComfyTagSourceBase.__init__(self, Danbooru(LPP_ROOT_DIR))

    @classmethod
    def INPUT_TYPES(self):
        s = lpp_sources["Danbooru"]
        types = deepcopy(self.tag_source_input_types_base)
        types["required"]["rating"] = (s.get_ratings(),)
        types["required"]["sort_by"] = (s.get_sort_options(),)
        types["required"]["format"] = (s.supported_models,)
        types["optional"]["tag_data"] = ("LPP_TAG_DATA_DANBOORU",)
        return types

    def get_prompt(
        self, query, count, rating, sort_by, format, tag_filter,
        send_request, tag_data=None, prompt_template=""
    ):
        if tag_data:
            self._pm.tag_data = tag_data
        elif self._pm.prompts_count == 0 or send_request:
            self._pm.tag_data = self._source.request_tags(
                query, count, rating, sort_by
            )
        tf = FilterData.from_string(tag_filter, ",")
        return (
            self._pm.choose_prompts(format, prompt_template, 1, None, [tf])[0],
            (self._pm.tag_data, tf)
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
        existing_names = cm.get_item_names()
        if (name in existing_names and overwrite) \
                or name not in existing_names:
            cm.save_item(name, tag_data[0])
        return {}


class LPPLoaderDerpibooru:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (
                    cm.get_item_names(lambda k, v: (v.source == "Derpibooru")),
                )
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_DERPIBOORU",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm[collection_name],)


class LPPLoaderE621:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (
                    cm.get_item_names(lambda k, v: (v.source == "E621")),
                )
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_E621",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm[collection_name],)


class LPPLoaderDanbooru:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (
                    cm.get_item_names(lambda k, v: (v.source == "Danbooru")),
                )
            }
        }
    RETURN_TYPES = ("LPP_TAG_DATA_DANBOORU",)
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm[collection_name],)


class LPPDeleter:
    @classmethod
    def INPUT_TYPES(self):
        return {
            "required": {
                "collection_name": (cm.get_item_names(),)
            }
        }
    RETURN_TYPES = ()
    CATEGORY = "LPP"
    FUNCTION = "delete_tag_data"
    OUTPUT_NODE = True

    def delete_tag_data(self, collection_name):
        cm.delete_item(collection_name)
        return {}
