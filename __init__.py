from .lpp.ui.comfy import ComfyDerpibooru, LPPLoaderDerpibooru
from .lpp.ui.comfy import ComfyE621, LPPLoaderE621
from .lpp.ui.comfy import ComfyDanbooru, LPPLoaderDanbooru
from .lpp.ui.comfy import LPPSaver, LPPDeleter


NODE_CLASS_MAPPINGS = {
    "LPP_Derpibooru": ComfyDerpibooru,
    "LPP_E621": ComfyE621,
    "LPP_Danbooru": ComfyDanbooru,
    "LPP_Saver": LPPSaver,
    "LPP_Loader_Derpibooru": LPPLoaderDerpibooru,
    "LPP_Loader_E621": LPPLoaderE621,
    "LPP_Loader_Danbooru": LPPLoaderDanbooru,
    "LPP_Deleter": LPPDeleter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LPP_Derpibooru": "Derpibooru",
    "LPP_E621": "E621",
    "LPP_Danbooru": "Danbooru",
    "LPP_Saver": "Tag Data Saver",
    "LPP_Loader_Derpibooru": "Tag Data Loader (Derpibooru)",
    "LPP_Loader_E621": "Tag Data Loader (E621)",
    "LPP_Loader_Danbooru": "Tag Data Loader (Danbooru)",
    "LPP_Deleter": "Tag Data Deleter"
}

__all__ = [NODE_CLASS_MAPPINGS]
