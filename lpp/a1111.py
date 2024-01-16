from lpp.backend import SourcesManager, PromptsManager, CacheManager, TagData
from lpp.log import get_logger

logger = get_logger()


class LPP_A1111:
    def __init__(self, work_dir: str = ".",
                 derpi_api_key: str = None,
                 logging_level: object = None):
        self.__work_dir: str = work_dir
        if logging_level:
            logger.setLevel(logging_level)
        self.__sources_manager: SourcesManager = SourcesManager(self.__work_dir)

        # TODO: need better way of handling this
        if "Derpibooru" in self.__sources_manager.sources.keys():
            self.__sources_manager.sources["Derpibooru"].set_api_key(derpi_api_key)

        self.__prompts_manager: PromptsManager = PromptsManager(
            self.__sources_manager)
        self.__cache_manager: CacheManager = CacheManager(self.__work_dir)

    @property
    def source_names(self):
        return self.__sources_manager.get_source_names()

    @property
    def sources(self) -> dict[str:list[object]]:
        return self.__sources_manager.sources

    @property
    def tag_data(self) -> TagData:
        return self.__prompts_manager.tag_data

    @tag_data.setter
    def tag_data(self, value: TagData) -> None:
        self.__prompts_manager.tag_data = value

    def get_model_names(self, source: str) -> list[str]:
        return self.__sources_manager.sources[source].get_model_names()

    @property
    def saved_collections_names(self) -> list[str]:
        return self.__cache_manager.get_saved_names()

    def __get_lpp_status(self) -> str:
        n_prompts = self.__prompts_manager.get_loaded_prompts_count()
        return f"**{n_prompts}** prompts loaded. Ready to generate." \
            if n_prompts > 0 \
            else "No prompts loaded. Not ready to generate."

    def format_status_msg(self, msg: str = "") -> str:
        m = f"{msg}. " if msg else ""
        return f"&nbsp;&nbsp;{m}{self.__get_lpp_status()}"

    def __try_exec_command(
        self, lpp_method: callable, success_msg: str,
        failure_msg: str, *args: object
    ) -> str:
        try:
            lpp_method(*args)
            return success_msg
        except Exception as e:
            logger.warning(f"{failure_msg} {str(e)} ({type(e).__name__})")
            return failure_msg + f" {str(e)}"

    def try_save_prompts(self, name: str, tag_filter: str) -> str:
        return self.format_status_msg(
            self.__try_exec_command(
                self.__cache_manager.cache_tag_data,
                f"Successfully saved \"{name}\"",
                f"Failed to save \"{name}\":",
                name, self.__prompts_manager.tag_data, tag_filter
            )
        )

    def try_load_prompts(self, name: str) -> str:
        def load_new_tag_data(name: str) -> None:
            self.__prompts_manager.tag_data = self.__cache_manager.get_tag_data(
                name)
        return self.format_status_msg(
            self.__try_exec_command(
                load_new_tag_data,
                f"Successfully loaded \"{name}\"",
                f"Failed to load \"{name}\":",
                name
            )
        )

    def try_delete_prompts(self, name: str) -> str:
        return self.format_status_msg(
            self.__try_exec_command(
                self.__cache_manager.delete_tag_data,
                f"Successfully deleted \"{name}\"",
                f"Failed to delete \"{name}\":",
                name
            )
        )

    def try_send_request(self, *args: object) -> str:
        def load_new_tag_data(*args: object) -> None:
            self.__prompts_manager.tag_data = self.__sources_manager.request_prompts(
                *args)
        return self.format_status_msg(
            self.__try_exec_command(
                load_new_tag_data,
                f"Successfully fetched tags from \"{args[0]}\"",
                f"Failed to fetch tags from \"{args[0]}\":",
                *args
            )
        )

    def try_get_tag_data_json(self, name: str) -> (bool, dict[str:object]):
        try:
            target = self.__cache_manager.get_tag_data(name)
            return True, {
                "source": target.source,
                "query": target.query,
                "other parameters": target.other_params,
                "count": len(target.raw_tags)
            }
        except KeyError:
            return False, {}

    def try_choose_prompts(self,
                           model: str,
                           template: str = None,
                           n: int = 1,
                           tag_filter_str: str = ""
                           ) -> list[list[str]]:
        try:
            return self.__prompts_manager.choose_prompts(
                model, template, n, tag_filter_str
            )
        except IndexError:
            logger.error(
                "Failed to choose prompts because no prompts are currently loaded")
        except Exception:
            logger.exception("Failed to choose prompts", exc_info=True)
