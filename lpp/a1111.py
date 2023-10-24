from lpp.backend import SourcesManager, CacheManager
from lpp.log import get_logger
from dataclasses import dataclass
import gradio as gr

logger = get_logger()


def set_no_config(*args: object) -> None:
    for control in args:
        setattr(control, "do_not_save_to_config", True)


class LPPWrapper:
    def __init__(self, work_dir: str = "."):
        self.__work_dir: str = work_dir
        self.sources_manager: SourcesManager = SourcesManager(self.__work_dir)
        self.cache_manager: CacheManager = CacheManager(self.__work_dir)

    def __get_lpp_status(self) -> str:
        n_prompts = self.sources_manager.get_loaded_prompts_count()
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
                self.cache_manager.cache_tag_data,
                f"Successfully saved \"{name}\"",
                f"Failed to save \"{name}\":",
                name, self.sources_manager.tag_data, tag_filter
            )
        )

    def try_load_prompts(self, name: str) -> str:
        def load_new_tag_data(name: str) -> None:
            self.sources_manager.tag_data = self.cache_manager.get_tag_data(
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
                self.cache_manager.delete_tag_data,
                f"Successfully deleted \"{name}\"",
                f"Failed to delete \"{name}\":",
                name
            )
        )

    def try_send_request(self, *args: object) -> str:
        return self.format_status_msg(
            self.__try_exec_command(
                self.sources_manager.request_prompts,
                f"Successfully fetched tags from \"{args[0]}\"",
                f"Failed to fetch tags from \"{args[0]}\":",
                *args
            )
        )

    def try_get_tag_data_json(self, name: str) -> (bool, dict[str:object]):
        try:
            target = self.cache_manager.get_tag_data(name)
            return True, {
                "source": target.source,
                "query": target.query,
                "other parameters": target.other_params,
                "count": len(target.raw_tags)
            }
        except KeyError:
            return False, {}

    def try_choose_prompts(
        self, model: str, n: int = 1, tag_filter_str: str = ""
    ) -> list[list[str]]:
        try:
            return self.sources_manager.choose_prompts(
                model, n, tag_filter_str
            )
        except IndexError:
            logger.error("Failed to choose prompts because no prompts are currently loaded")
        except Exception:
            logger.exception("Failed to choose prompts", exc_info=True)


@dataclass
class QueryPanelData:
    panel: object
    send_btn: object
    params: list


class QueryPanels:
    @staticmethod
    def Derpibooru(
        active_panel_name: str, lpp: LPPWrapper, config: dict[str:object]
    ) -> QueryPanelData:
        with gr.Accordion(
            "💬 Derpibooru Query",
            open=config["query_panel_start_unfolded"],
            visible=(active_panel_name == "Derpibooru")
        ) as panel:
            gr.Markdown(
                "[🔗 Syntax Help](https://derpibooru.org/pages/search_syntax)")
            with gr.Row():
                query = gr.Textbox(
                    placeholder="Type in your Derpibooru query here",
                    show_label=False
                )
            with gr.Row():
                with gr.Column():
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=config["prompts_count"]["min"],
                        maximum=config["prompts_count"]["max"],
                        step=config["prompts_count"]["step"],
                        value=config["prompts_count"]["default"]
                    )
                with gr.Column():
                    with gr.Row():
                        filter_type = gr.Dropdown(
                            label="Derpibooru Filter",
                            choices=lpp.sources_manager.sources[
                                "Derpibooru"
                            ].get_filters()
                        )
                        filter_type.value = filter_type.choices[0]
                        sort_type = gr.Dropdown(
                            label="Sort by",
                            choices=lpp.sources_manager.sources[
                                "Derpibooru"
                            ].get_sort_options()
                        )
                        sort_type.value = sort_type.choices[0]
            with gr.Row():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, filter_type, sort_type)
            return QueryPanelData(
                panel,
                send_btn,
                [query, prompts_count, filter_type, sort_type]
            )

    @staticmethod
    def E621(
        active_panel_name: str, lpp: LPPWrapper, config: dict[str:object]
    ) -> QueryPanelData:
        with gr.Accordion(
            "💬 E621 Query",
            open=config["query_panel_start_unfolded"],
            visible=(active_panel_name == "E621")
        ) as panel:
            gr.Markdown(
                "[🔗 Syntax Help](https://e621.net/help/cheatsheet)")
            with gr.Row():
                query = gr.Textbox(
                    placeholder="Type in Your E621 query here",
                    show_label=False
                )
            with gr.Row():
                with gr.Column():
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=config["prompts_count"]["min"],
                        maximum=config["prompts_count"]["max"],
                        step=config["prompts_count"]["step"],
                        value=config["prompts_count"]["default"]
                    )
                with gr.Column():
                    with gr.Row():
                        rating = gr.Dropdown(
                            label="Rating",
                            choices=lpp.sources_manager.sources[
                                "E621"
                            ].get_ratings()
                        )
                        rating.value = rating.choices[0]
                        sort_type = gr.Dropdown(
                            label="Sort by",
                            choices=lpp.sources_manager.sources[
                                "E621"
                            ].get_sort_options()
                        )
                        sort_type.value = sort_type.choices[0]
            with gr.Row():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, rating, sort_type)
            return QueryPanelData(
                panel,
                send_btn,
                [query, prompts_count, rating, sort_type]
            )
