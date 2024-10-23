from lpp.backend import SourcesManager, PromptsManager, CacheManager, FiltersManager
from lpp.log import get_logger
from lpp.utils import LppMessageService, TagData, FilterData, Ratings

logger = get_logger()


class DefaultLppMessageService(LppMessageService):
    def info(self, message):
        logger.info(message)

    def warning(self, message):
        logger.warning(message)

    def error(self, message):
        logger.error(message)


class LPP_A1111:
    def __init__(self, work_dir: str = ".",
                 derpi_api_key: str = None,
                 logging_level: object = None,
                 messenger: LppMessageService = DefaultLppMessageService()):
        self.__work_dir: str = work_dir
        if logging_level:
            logger.setLevel(logging_level)
        self.__sources_manager: SourcesManager = SourcesManager(self.__work_dir)

        # TODO: need better way of handling this
        if "Derpibooru" in self.__sources_manager.sources.keys():
            self.__sources_manager.sources["Derpibooru"].set_api_key(derpi_api_key)

        self.__prompts_manager: PromptsManager = PromptsManager(
            self.__sources_manager
        )
        self.__cache_manager: CacheManager = CacheManager(self.__work_dir)
        self.__filters_manager: FiltersManager = FiltersManager(self.__work_dir)

        self.__messenger = messenger
        self.__collection_name = ""

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

    @property
    def saved_collections_names(self) -> list[str]:
        return self.__cache_manager.get_saved_names()

    @property
    def filters(self) -> list[(str, FilterData)]:
        return self.__filters_manager.get_filter_names()

    @property
    def status(self) -> str:
        n_prompts = self.__prompts_manager.get_loaded_prompts_count()
        return f"\"{self.__collection_name}\" <b>[{n_prompts}]</b> ✅" \
            if n_prompts > 0 \
            else "No prompts loaded 🛑"

    def __try_exec_command(
        self, lpp_method: callable, success_msg: str,
        failure_msg: str, *args: object
    ) -> None:
        try:
            lpp_method(*args)
            self.__messenger.info(success_msg)
        except Exception as e:
            self.__messenger.warning(
                f"{failure_msg} {str(e)} ({type(e).__name__})"
            )

    def try_save_prompts(self, name: str, filters: list[str]) -> None:
        self.__try_exec_command(
            self.__cache_manager.save_item,
            f"Successfully saved \"{name}\"",
            f"Failed to save \"{name}\":",
            name, self.tag_data, filters
        )

    def try_load_prompts(self, name: str) -> None:
        def load_new_tag_data(name: str) -> None:
            self.tag_data = self.__cache_manager.get_item(name)
            self.__collection_name = name
        self.__try_exec_command(
            load_new_tag_data,
            f"Successfully loaded \"{name}\"",
            f"Failed to load \"{name}\":",
            name
        )

    def try_delete_prompts(self, name: str) -> None:
        self.__try_exec_command(
            self.__cache_manager.delete_item,
            f"Successfully deleted \"{name}\"",
            f"Failed to delete \"{name}\":",
            name
        )

    def try_save_filter(self, name: str, lpp_filter: FilterData) -> None:
        self.__try_exec_command(
            self.__filters_manager.save_item,
            f"Successfully saved filter \"{name}\"",
            f"Filed to save filter \"{name}\":",
            name, lpp_filter
        )

    def try_load_filter(self, name: str) -> FilterData:
        try:
            f = self.__filters_manager.get_item(name)
            self.__messenger.info(f"Successfully loaded filter \"{name}\"")
            return f
        except KeyError:
            self.__messenger.warning(f"Failed to load filter \"{name}\":")
            return None

    def try_delete_filter(self, name: str) -> None:
        self.__try_exec_command(
            self.__filters_manager.delete_item,
            f"Successfully deleted filter \"{name}\"",
            f"Failed to delete filter \"{name}\":",
            name
        )

    def get_filters(self, filter_names: str):
        filters = []
        failed_filters = []
        for f in filter_names:
            if f in self.filters:
                filters.append(self.__filters_manager.get_item(f))
            else:
                failed_filters.append(f)
        if failed_filters:
            self.__messenger.warning(f"Filed to load filters: {', '.join(failed_filters)}")
        return filters

    def try_send_request(self, *args: object) -> None:
        def load_new_tag_data(*args: object) -> None:
            self.tag_data = self.__sources_manager.request_prompts(*args)
            self.__collection_name = "from query"
        self.__try_exec_command(
            load_new_tag_data,
            f"Successfully fetched tags from \"{args[0]}\"",
            f"Failed to fetch tags from \"{args[0]}\":",
            *args
        )

    def try_get_tag_data_markdown(self, name: str) -> str:
        try:
            target = self.__cache_manager.get_item(name)
            ratings = {
                Ratings.SAFE.value: 0,
                Ratings.QUESTIONABLE.value: 0,
                Ratings.EXPLICIT.value: 0
            }
            source = self.__sources_manager.sources[target.source]
            for item in target.raw_tags:
                ratings[source.get_lpp_rating(item)] += 1
            filter_str = "Filters: " +\
                " ".join([f"`{x}`" for x in target.other_params["filters"]])
            other_params = ", ".join(
                [f"{k}: **{v}**" for k, v in target.other_params.items()
                    if k not in ["filters", "tag_filter"]]
            )
            main_info =\
f"""Source: **{target.source}** *({len(target.raw_tags)} total prompts)*

Safe: **{ratings[Ratings.SAFE.value]}** | Questionable: **{ratings[Ratings.QUESTIONABLE.value]}** | Explicit: **{ratings[Ratings.EXPLICIT.value]}**

```
{target.query}
```
"""
            return main_info + filter_str + "\n" + other_params
        except KeyError:
            return "no collection selected"

    def try_choose_prompts(self,
                           model: str,
                           template: str = None,
                           n: int = 1,
                           allowed_ratings: list[str] = None,
                           filters: list[FilterData] = None
                           ) -> list[list[str]]:
        try:
            return self.__prompts_manager.choose_prompts(
                model, template, n, allowed_ratings, filters
            )
        # HACK: these should really be errors and not warnings, but effing
        # A1111 or Gradio just refuses to display them. It is important to
        # explicitly alert the user about these problems, so for now I'll
        # leave it as is. Revisit this issue when A1111 updates.
        except ValueError as e:
            self.__messenger.warning(repr(e))
        except Exception:
            logger.exception("An error occured when trying to choose prompts.")
