import sys
import os.path as path
from copy import deepcopy

LPP_ROOT_DIR = path.join(path.dirname(__file__), "..", "..")
sys.path.append(LPP_ROOT_DIR)

from lpp.sources.common import TagSourceBase
from lpp.sources.derpibooru import Derpibooru
from lpp.sources.e621 import E621
from lpp.sources.danbooru import Danbooru
from lpp.sources.utils import get_sources
from lpp.prompts import PromptPool
from lpp.data import FilterData, CacheManager

lpp_sources = get_sources(LPP_ROOT_DIR)
cm = CacheManager(LPP_ROOT_DIR)


class ComfyTagSourceBase:
    def __init__(self, source: TagSourceBase):
        self._source: TagSourceBase = source
        self._prompt_pool: PromptPool = None

    SOURCE_NAME = ""

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

    RETURN_TYPES = ("STRING", "LPP_TAG_DATA")
    RETURN_NAMES = ("Prompt", "LPP Tag Data")
    CATEGORY = "LPP/sources"
    FUNCTION = "get_prompt"

    def get_prompt(self,
                   format,
                   tag_filter,
                   send_request,
                   tag_data=None,
                   prompt_template="",
                   **query_args):
        if tag_data:
            self._prompt_pool = PromptPool(tag_data, LPP_ROOT_DIR)
        elif not self._prompt_pool or send_request:
            self._prompt_pool = PromptPool(
                    self._source.request_tags(**query_args),
                    LPP_ROOT_DIR
            )
        tf = FilterData.from_string(tag_filter, ",")
        chosen_prompts = self._prompt_pool.choose_prompts(1, None)
        prompt = chosen_prompts\
            .apply_formatting(format)\
            .extra_tag_formatting(
                lambda x: x.filter(tf).escape_parentheses()
            )\
            .apply_template(format, prompt_template)\
            .sanitize()\
            .first()
        return (prompt, (self._prompt_pool.tag_data, tf))

    @classmethod
    def IS_CHANGED(self, *args, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        types = deepcopy(cls.tag_source_input_types_base)
        s = lpp_sources[cls.SOURCE_NAME]

        for p, get_values_func in s.extra_query_params.items():
            types["required"][p] = (get_values_func(),)
        types["required"]["format"] = (s.supported_models,)
        types["optional"]["tag_data"] = (f"LPP_TAG_DATA_{cls.SOURCE_NAME.upper()}",)
        return types


class ComfyDerpibooru(ComfyTagSourceBase):
    SOURCE_NAME = Derpibooru.__name__

    def __init__(self):
        ComfyTagSourceBase.__init__(self, Derpibooru(LPP_ROOT_DIR))


class ComfyE621(ComfyTagSourceBase):
    SOURCE_NAME = E621.__name__

    def __init__(self):
        ComfyTagSourceBase.__init__(self, E621(LPP_ROOT_DIR))


class ComfyDanbooru(ComfyTagSourceBase):
    SOURCE_NAME = Danbooru.__name__

    def __init__(self):
        ComfyTagSourceBase.__init__(self, Danbooru(LPP_ROOT_DIR))


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


class LPPLoaderBase:
    SOURCE_NAME = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "collection_name": (
                    cm.get_item_names(lambda k, v: (v.source == cls.SOURCE_NAME)),
                )
            }
        }
    RETURN_NAMES = ("tag data",)
    CATEGORY = "LPP/loaders"
    FUNCTION = "load_tag_data"

    def load_tag_data(self, collection_name):
        return (cm[collection_name],)


class LPPLoaderDerpibooru(LPPLoaderBase):
    SOURCE_NAME = Derpibooru.__name__
    RETURN_TYPES = (f"LPP_TAG_DATA_{SOURCE_NAME.upper()}",)


class LPPLoaderE621(LPPLoaderBase):
    SOURCE_NAME = E621.__name__
    RETURN_TYPES = (f"LPP_TAG_DATA_{SOURCE_NAME.upper()}",)


class LPPLoaderDanbooru(LPPLoaderBase):
    SOURCE_NAME = Danbooru.__name__
    RETURN_TYPES = (f"LPP_TAG_DATA_{SOURCE_NAME.upper()}",)


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
