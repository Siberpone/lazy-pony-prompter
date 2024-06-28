from lpp.a1111 import LPP_A1111, DefaultLppMessageService
from lpp.utils import Models, FilterData
from dataclasses import dataclass
from modules import scripts
from modules import shared
from modules import script_callbacks
from modules.ui_components import InputAccordion, FormRow, FormColumn, FormGroup, ToolButton
import gradio as gr
import logging

base_dir = scripts.basedir()


def set_no_config(*args: object) -> None:
    for control in args:
        setattr(control, "do_not_save_to_config", True)


def get_opt(option, default):
    return getattr(shared.opts, option, default)


saved_prompt_collections = []


def refresh_saved_collections():
    global saved_prompt_collections
    saved_prompt_collections = ["None"] + lpp.saved_collections_names


def on_ui_settings():
    LPP_SECTION = ("lpp", "Lazy Pony Prompter")

    lpp_options = {
        "lpp_default_collection":
        # TODO: try to fix this later.
        # "allow_custom_value" bugs out UI, so had to go with a constant
        # value indicating not to load anything on startup
            shared.OptionInfo(
                "None",
                "Load this collection on startup",
                gr.Dropdown,
                lambda: {"choices": ["None"] + lpp.saved_collections_names},
                refresh=refresh_saved_collections
            ),
        "lpp_logging_level":
            shared.OptionInfo(
                logging.WARNING,
                "Console nagging level",
                gr.Radio,
                {"choices": [
                    ("Error", logging.ERROR),
                    ("Warning", logging.WARNING),
                    ("Info", logging.INFO),
                    ("Debug", logging.DEBUG)]
                 }
            ).needs_reload_ui(),
        "lpp_derpibooru_api_key":
            shared.OptionInfo("",
                              "Derpibooru API Key",
                              gr.Textbox,
                              {"interactive": True, "type": "password"}
                              ).needs_reload_ui()
    }

    for key, opt in lpp_options.items():
        opt.section = LPP_SECTION
        shared.opts.add_option(key, opt)


script_callbacks.on_ui_settings(on_ui_settings)


class A1111LppMessageService(DefaultLppMessageService):
    def __init__(self):
        def modal_decorator(func, modal_func):
            def inner(message):
                func(self, message)
                modal_func(f"[LPP] {message}")
            return inner
        self.info = modal_decorator(super().info.__func__, gr.Info)
        self.warning = modal_decorator(super().warning.__func__, gr.Warning)
        self.error = modal_decorator(super().error.__func__, gr.Error)


lpp: LPP_A1111 = LPP_A1111(
    base_dir,
    get_opt("lpp_derpibooru_api_key", None),
    get_opt("lpp_logging_level", None),
    A1111LppMessageService()
)


@dataclass
class QueryPanelData:
    panel: object
    send_btn: object
    params: list


class QueryPanels:
    __PROMPTS_MIN = 5
    __PROMPTS_MAX = 1500
    __PROMPTS_STEP = 5
    __PROMPTS_DEFAULT = 100

    @staticmethod
    def Derpibooru(active_panel_name: str, lpp: LPP_A1111) -> QueryPanelData:
        NAME = "Derpibooru"
        with FormGroup(
            visible=(active_panel_name == NAME)
        ) as panel:
            gr.Markdown(
                "[🔗 Syntax Help](https://derpibooru.org/pages/search_syntax)")
            with FormRow():
                query = gr.Textbox(
                    placeholder="Derpibooru query or image URL",
                    show_label=False
                )
            with FormRow():
                with FormColumn():
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=QueryPanels.__PROMPTS_MIN,
                        maximum=QueryPanels.__PROMPTS_MAX,
                        step=QueryPanels.__PROMPTS_STEP,
                        value=QueryPanels.__PROMPTS_DEFAULT
                    )
                with FormColumn():
                    with FormRow():
                        filter_type = gr.Dropdown(
                            label="Derpibooru Filter",
                            choices=lpp.sources[NAME].get_filters()
                        )
                        filter_type.value = filter_type.choices[0]
                        sort_type = gr.Dropdown(
                            label="Sort by",
                            choices=lpp.sources[NAME].get_sort_options()
                        )
                        sort_type.value = sort_type.choices[0]
            with FormRow():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, filter_type, sort_type)
            return QueryPanelData(
                panel,
                send_btn,
                [query, prompts_count, filter_type, sort_type]
            )

    @staticmethod
    def E621(active_panel_name: str, lpp: LPP_A1111) -> QueryPanelData:
        NAME = "E621"
        with FormGroup(
            visible=(active_panel_name == NAME)
        ) as panel:
            gr.Markdown(
                "[🔗 Syntax Help](https://e621.net/help/cheatsheet)")
            with FormRow():
                query = gr.Textbox(
                    placeholder="E621 query or image URL",
                    show_label=False
                )
            with FormRow():
                with FormColumn():
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=QueryPanels.__PROMPTS_MIN,
                        maximum=QueryPanels.__PROMPTS_MAX,
                        step=QueryPanels.__PROMPTS_STEP,
                        value=QueryPanels.__PROMPTS_DEFAULT
                    )
                with FormColumn():
                    with FormRow():
                        rating = gr.Dropdown(
                            label="Rating",
                            choices=lpp.sources[NAME].get_ratings()
                        )
                        rating.value = rating.choices[0]
                        sort_type = gr.Dropdown(
                            label="Sort by",
                            choices=lpp.sources[NAME].get_sort_options()
                        )
                        sort_type.value = sort_type.choices[0]
            with FormRow():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, rating, sort_type)
            return QueryPanelData(
                panel,
                send_btn,
                [query, prompts_count, rating, sort_type]
            )


class Scripts(scripts.Script):
    def __init__(self):
        self.query_panels = {}
        self.prompt_manager_dialog_action = lambda: None

        startup_collection = get_opt("lpp_default_collection", "None")
        if startup_collection != "None":
            lpp.try_load_prompts(startup_collection)

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with InputAccordion(
                value=False,
                label="💤 Lazy Pony Prompter",) as lpp_enable:
            with lpp_enable.extra():
                status_bar = gr.HTML(
                    lpp.status, elem_id="lpp-status-bar", container=False
                )

            # Prompts Manager #################################################
            with gr.Tab("Prompts Manager"):
                with FormRow():
                    # Prompt collections Management Panel ---------------------
                    with FormColumn():
                        with FormRow():
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=lpp.saved_collections_names,
                                allow_custom_value=True
                            )
                            save_prompts_btn = ToolButton(value="💾")
                            load_prompts_btn = ToolButton(value="📤")
                            delete_prompts_btn = ToolButton("❌")
                        with FormRow(variant="panel", visible=False) as prompt_manager_dialog:
                            with FormColumn():
                                with FormRow():
                                    pm_dialog_msg = gr.Markdown()
                                with FormRow():
                                    pm_dialog_confirm_btn = gr.Button(
                                        "Confirm", variant="stop")
                                    pm_dialog_cancel_btn = gr.Button("Cancel")
                        with FormRow():
                            models = lpp.get_model_names(lpp.tag_data.source)\
                                if lpp.tag_data else []
                            prompts_format = gr.Dropdown(
                                label="Prompts Format",
                                choices=["Auto"] + models,
                                value="Auto"
                            )

                    # Filtering Options Panel ---------------------------------
                    with FormColumn():
                        with FormRow():
                            filters = gr.Dropdown(
                                label="Filters",
                                choices=lpp.filters,
                                multiselect=True
                            )
                        with FormRow():
                            rating_filter = gr.CheckboxGroup(
                                label="Rating Filter",
                                choices=["Safe", "Questionable", "Explicit"],
                                value="Safe",
                                elem_id="lpp-chbox-group",
                                scale=7
                            )
                            autofill_tags_filter = gr.Checkbox(
                                label="Autofill Tags Filter",
                                elem_id="lpp-autofill-filter-chbox",
                                scale=2
                            )

                # Booru Query Panels ------------------------------------------
                with gr.Accordion(
                    label="💬 Get prompts from Booru",
                    open=False
                ):
                    source = gr.Radio(
                        label="Tags Source",
                        choices=lpp.source_names,
                        value=lambda: lpp.source_names[0],
                        elem_id="lpp-chbox-group"
                    )
                    for attr in [
                        x for x in dir(QueryPanels) if not x.startswith("_")
                    ]:
                        query_panel = getattr(QueryPanels, attr)
                        self.query_panels[query_panel.__name__] = query_panel(
                            source.value, lpp
                        )

            # Filter Editor ###################################################
            with gr.Tab("Filter Editor"):
                # WARN: left this old input for compatibility for now.
                # !!! Remove after new filter system has been implemented.
                # -------------------------------------------------------------
                with FormRow(visible=False):
                    with FormColumn(scale=2):
                        tag_filter = gr.Textbox(
                            show_label=False,
                            placeholder="These tags (comma separated) will be pruned from prompts"
                        )
                    with FormColumn(scale=0, min_width=130):
                        gr.ClearButton(components=[tag_filter])
                # -------------------------------------------------------------
                with FormRow():
                    # Filter Managment Panel ----------------------------------
                    with FormColumn(scale=2):
                        with FormRow():
                            fe_filter_name = gr.Dropdown(
                                label="Filter Name",
                                choices=lpp.filters,
                                allow_custom_value=True
                            )
                            fe_save_btn = ToolButton(value="💾",)
                            fe_load_btn = ToolButton(value="📤")
                            fe_delete_btn = ToolButton(value="❌")
                        with FormRow():
                            with gr.Accordion("cheatsheet", open=False):
                                gr.Markdown(r"""
* patterns are separated with new lines
* patterns support simple globbing
  * `*` matches anything
  * `?` matches any single character
  * `[xyz]` matches specified characters
  * `[A-Z]` matches a range of characters
* you can specify a substitution for a pattern with `||`, for example:
`horn||wings` will substitute "horn" with "wings"
                                """)

                    # Filter Editing Text Area --------------------------------
                    with FormColumn(scale=3):
                        fe_patterns = gr.Textbox(
                            label="Filter Patterns",
                            interactive=True,
                            lines=7,
                            max_lines=15
                        )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(source, prompts_format, prompts_manager_input)

            # Prompt Manager Event Handlers ###################################
            # Send Query Buttons
            def send_request_click(source, prompts_format, *params):
                models = ["Auto"] + lpp.get_model_names(source)
                lpp.try_send_request(source, *params)
                return (
                    lpp.status,
                    gr.update(
                        choices=models,
                        value=prompts_format if prompts_format in models
                        else models[0]
                    )
                )

            for panel in self.query_panels.values():
                panel.send_btn.click(
                    send_request_click,
                    [source, prompts_format, *panel.params],
                    [status_bar, prompts_format],
                    show_progress="full"
                )

            # Source Dropdown Change
            source.change(
                lambda s: [
                    gr.update(
                        visible=(s == x)
                    ) for x in self.query_panels.keys()
                ],
                [source],
                [x.panel for x in self.query_panels.values()]
            )

            # Save Button Click
            def save_prompts_click(name, tag_filter):
                self.prompt_manager_dialog_action = lambda: \
                    lpp.try_save_prompts(name, tag_filter), \
                    name
                if name in lpp.saved_collections_names:
                    return (
                        gr.update(),
                        f"Are you sure you want to overwrite \"{name}\"?",
                        gr.update(visible=True)
                    )
                else:
                    lpp.try_save_prompts(name, tag_filter)
                    return (
                        gr.Dropdown.update(
                            choices=lpp.saved_collections_names
                        ),
                        "", gr.update(visible=False)
                    )

            save_prompts_btn.click(
                save_prompts_click,
                [prompts_manager_input, tag_filter],
                [prompts_manager_input, pm_dialog_msg, prompt_manager_dialog],
                show_progress="hidden"
            )

            # Load Button Click
            def load_prompts_click(name, autofill_tags_filter, current_model):
                lpp.try_load_prompts(name)
                if lpp.tag_data:
                    source = lpp.tag_data.source
                    models = ["Auto"] + lpp.get_model_names(source)
                    models_update = gr.update(
                        choices=models,
                        value=current_model if current_model in models
                        else models[0]
                    )
                    metadata = lpp.tag_data.other_params
                    tag_filter_update = metadata["tag_filter"] \
                        if "tag_filter" in metadata and autofill_tags_filter \
                        else ""
                else:
                    models_update = gr.update()
                    tag_filter_update = gr.update()

                return (
                    lpp.status,
                    tag_filter_update,
                    models_update
                )
            load_prompts_btn.click(
                load_prompts_click,
                [prompts_manager_input, autofill_tags_filter, prompts_format],
                [status_bar, tag_filter, prompts_format],
                show_progress="hidden"
            )

            # Delete Button Click
            def delete_click(name):
                self.prompt_manager_dialog_action = lambda: \
                    lpp.try_delete_prompts(name), \
                    ""
                return [f"Are you sure you want to delete \"{name}\"?",
                        gr.update(visible=True)]
            delete_prompts_btn.click(
                delete_click,
                [prompts_manager_input],
                [pm_dialog_msg, prompt_manager_dialog],
                show_progress="hidden"
            )

            # Prompt Manager Confirmation Dialog
            def invoke_action():
                self.prompt_manager_dialog_action[0]()
                selected_val = self.prompt_manager_dialog_action[1]
                return (
                    gr.Dropdown.update(
                        choices=list(lpp.saved_collections_names),
                        value=selected_val
                    ),
                    gr.update(visible=False)
                )
            pm_dialog_confirm_btn.click(
                invoke_action,
                None,
                [prompts_manager_input, prompt_manager_dialog],
                show_progress="hidden"
            )
            pm_dialog_cancel_btn.click(
                lambda: gr.update(visible=False),
                None,
                [prompt_manager_dialog],
                show_progress="hidden"
            )

            # Filters Editor Event Handlers ###################################
            # Save Button -----------------------------------------------------
            def fe_save_click(name: str, lpp_filter: FilterData):
                lpp.try_save_filter(name, FilterData.from_string(lpp_filter))
                return (gr.update(choices=lpp.filters),
                        gr.update(choices=lpp.filters))

            fe_save_btn.click(
                fe_save_click,
                [fe_filter_name, fe_patterns],
                [filters, fe_filter_name]
            )

            # Load Button -----------------------------------------------------
            fe_load_btn.click(
                lambda n: str(lpp.try_load_filter(n)),
                [fe_filter_name],
                [fe_patterns]
            )

            # Delete Button ---------------------------------------------------
            def fe_delete_click(name: str):
                lpp.try_delete_filter(name)
                return (gr.update(choices=lpp.filters),
                        gr.update(value="", choices=lpp.filters))

            fe_delete_btn.click(
                fe_delete_click,
                [fe_filter_name],
                [filters, fe_filter_name]
            )
        return [lpp_enable, prompts_format, tag_filter, rating_filter, filters]

    def process(self, p, enabled, prompts_format,
                tag_filter, allowed_ratings, filters):
        if not enabled:
            return p

        if prompts_format == "Auto":
            model_hashes = {
                "67ab2fd8ec": Models.PDV56.value,   # PD V6 XL
                "6fdb703d7d": Models.PDV56.value,   # PD V5.5
                "51e44370f4": Models.PDV56.value,   # PD V5
                "821628644e": Models.EF.value       # EasyFluff V11.2
            }
            if p.sd_model_hash not in model_hashes:
                prompts_format = Models.PDV56.value
            else:
                prompts_format = model_hashes[p.sd_model_hash]

        n_images = p.batch_size * p.n_iter
        p.all_prompts = lpp.try_choose_prompts(
            prompts_format, p.prompt, n_images, tag_filter, allowed_ratings,
            lpp.get_filters(filters))

        p.all_prompts = [
            shared.prompt_styles.apply_styles_to_prompt(x, p.styles)
            for x in p.all_prompts
        ]

        if p.enable_hr:
            p.all_hr_prompts = p.all_prompts
            p.all_hr_negative_prompts = [p.negative_prompt] * n_images
