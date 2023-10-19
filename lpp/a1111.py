from lpp.backend import SourcesManager, CacheManager


class LPPWrapper():
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.sources_manager: SourcesManager = SourcesManager(self.__work_dir)
        self.cache_manager: CacheManager = CacheManager(self.__work_dir)

    def __get_lpp_status(self):
        n_prompts = self.sources_manager.get_loaded_prompts_count()
        return f"**{n_prompts}** prompts loaded. Ready to generate." \
            if n_prompts > 0 \
            else "No prompts loaded. Not ready to generate."

    def format_status_msg(self, msg=""):
        return f"&nbsp;&nbsp;{msg} {self.__get_lpp_status()}"

    def __try_exec_command(self, lpp_method, success_msg, failure_msg, *args):
        try:
            lpp_method(*args)
            return success_msg
        except Exception as e:
            return failure_msg + f" {str(e)}"

    def try_save_prompts(self, name, tag_filter):
        return self.format_status_msg(
            self.__try_exec_command(
                self.cache_manager.cache_tag_data,
                f"Successfully saved \"{name}\".",
                f"Failed to save \"{name}\":",
                name, self.sources_manager.tag_data, tag_filter
            )
        )

    def try_load_prompts(self, name):
        def load_new_tag_data(name):
            self.sources_manager.tag_data = self.cache_manager.get_tag_data(
                name)
        return self.format_status_msg(
            self.__try_exec_command(
                load_new_tag_data,
                f"Successfully loaded \"{name}\".",
                f"Failed to load \"{name}\":",
                name
            )
        )

    def try_delete_prompts(self, name):
        return self.format_status_msg(
            self.__try_exec_command(
                self.cache_manager.delete_tag_data,
                f"Successfully deleted \"{name}\".",
                f"Failed to delete \"{name}\":",
                name
            )
        )

    def try_send_request(self, *args):
        return self.format_status_msg(
            self.__try_exec_command(
                self.sources_manager.request_prompts,
                f"Successfully fetched tags from \"{args[0]}\".",
                f"Failed to delete \"{args[0]}\":",
                *args
            )
        )

    def try_get_tag_data_json(self, name: str) -> (bool, str):
        try:
            target = self.cache_manager.get_tag_data(name)
            return True, {
                "source": target.source,
                "query": target.query,
                "other parameters": target.other_params,
                "count": len(target.raw_tags)
            }
        except Exception as e:
            return False, {}
