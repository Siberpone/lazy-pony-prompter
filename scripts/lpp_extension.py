from lpp.a1111 import LPP_A1111, DefaultLppMessageService
from lpp.utils import Models, FilterData
from dataclasses import dataclass
from modules import scripts
from modules import shared
from modules import script_callbacks
from modules.ui_components import InputAccordion, FormRow, FormColumn, FormGroup, ToolButton
import gradio as gr
import inspect
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
                              ).needs_reload_ui(),
        "lpp_editors_count":
            shared.OptionInfo(3,
                              "Number of filter editor panels",
                              gr.Number,
                              {"precision": 0, "minimum": 1, "maximum": 8}
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


class ConfirmationDialog:
    def __init__(self, gradio_upd_func, gradio_outputs):
        def action_decorator(func):
            def inner():
                self.__action()
                ret = func(*self.__gradio_upd_func_args)
                return (*ret, gr.update(visible=False))
            return inner
        self.__gradio_upd_func = action_decorator(gradio_upd_func)
        self.__gradio_outputs = gradio_outputs

    def set_action(self, action, *args):
        self.__action = action
        self.__gradio_upd_func_args = args

    def ui(self):
        with FormRow(variant="panel", visible=False) as dialog:
            self.dialog = dialog
            with FormColumn():
                with FormRow():
                    self.msg = gr.Markdown()
                with FormRow():
                    self.confirm_btn = gr.Button("Confirm", variant="stop")
                    self.cancel_btn = gr.Button("Cancel")
        self.confirm_btn.click(
            self.__gradio_upd_func,
            None,
            self.__gradio_outputs + [self.dialog],
            show_progress="hidden"
        )
        self.cancel_btn.click(
            lambda: gr.update(visible=False),
            None,
            [self.dialog],
            show_progress="hidden"
        )
        return self.dialog, self.msg


class FilterEditor:
    external_inputs = []  # ui components to update when saving a filter

    def __init__(self):
        self.current_text = ""

    def ui(self):
        with FormColumn(variant="panel", scale=1, min_width=300):
            with FormRow():
                self.filter_name = gr.Dropdown(
                    label="Choose a filter to edit:",
                    choices=lpp.filters
                )
                self.save_btn = ToolButton("💾")
                self.refresh_btn = ToolButton("🗘")
            with FormRow():
                self.patterns_textarea = gr.Textbox(
                    label="Filter Patterns",
                    interactive=True,
                    lines=7,
                    max_lines=15
                )

        set_no_config(self.filter_name, self.patterns_textarea)

        def filter_name_change(name):
            filter_text = str(lpp.try_load_filter(name))
            self.current_text = filter_text
            return gr.update(value=filter_text)

        self.filter_name.change(
            filter_name_change,
            [self.filter_name],
            [self.patterns_textarea],
            show_progress="hidden"
        )

        self.patterns_textarea.change(
            lambda p: gr.update(label="Filter Patterns *(unsaved)")
            if self.current_text != p else gr.update(label="Filter Patterns"),
            [self.patterns_textarea],
            [self.patterns_textarea],
            show_progress="hidden"
        )

        def save_btn_click(name, patterns):
            self.current_text = patterns
            lpp.try_save_filter(name, FilterData.from_string(patterns))
            return [gr.update(label="Filter Patterns")]\
                + [gr.update(choices=lpp.filters)]\
                * len(FilterEditor.external_inputs)

        self.save_btn.click(
            save_btn_click,
            [self.filter_name, self.patterns_textarea],
            [self.patterns_textarea, *FilterEditor.external_inputs],
            show_progress="hidden"
        )

        self.refresh_btn.click(
            lambda: gr.update(choices=lpp.filters),
            [],
            [self.filter_name],
            show_progress="hidden"
        )


@dataclass
class QueryPanel:
    panel: gr.Group
    send_btn: gr.Button
    params: list[object]


def get_query_panels(active_panel_name: str):
    panels = {}
    for name, source in lpp.sources.items():
        with FormGroup(
            visible=(active_panel_name == name)
        ) as panel:
            gr.Markdown(
                f"[🔗 {name} Syntax Help]({source.syntax_help_url})")
            with FormRow():
                query = gr.Textbox(
                    placeholder=source.query_hint,
                    show_label=False
                )
            with FormRow():
                with FormColumn():
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=5,
                        maximum=1500,
                        step=5,
                        value=100
                    )
                with FormColumn():
                    with FormRow():
                        extra_params = inspect.getfullargspec(
                            getattr(source, "request_tags")
                        )[0][3:]
                        extra_controls = []
                        for p in extra_params:
                            obj = source.extra_query_params[p]
                            control = gr.Dropdown(
                                label=obj.display_name,
                                choices=obj()
                            )
                            control.value = control.choices[0]
                            extra_controls.append(control)
            with FormRow():
                send_btn = gr.Button(value="Send")
            controls = [query, prompts_count] + extra_controls
            set_no_config(*controls)
            panels[name] = QueryPanel(panel, send_btn, controls)
    return panels


class Scripts(scripts.Script):
    def __init__(self):
        self.query_panels = {}
        self.prompt_info_visible = False

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
                    # Prompt Collections Management Panel ---------------------
                    with FormColumn():
                        with FormRow():
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=lpp.saved_collections_names,
                                allow_custom_value=True
                            )
                            prompts_info_btn = ToolButton("📋")
                            save_prompts_btn = ToolButton("💾")
                            load_prompts_btn = ToolButton("📤")
                            delete_prompts_btn = ToolButton("❌")

                        prompts_manager_metadata = gr.Markdown(
                            label="Prompts Info",
                            show_label=True,
                            render=False
                        )
                        pm_dialog = ConfirmationDialog(
                            lambda name: [
                                gr.Dropdown.update(
                                    choices=list(lpp.saved_collections_names),
                                    value=name
                                ),
                                gr.update(
                                    value=lpp.try_get_tag_data_markdown(name)
                                )
                            ],
                            [prompts_manager_input, prompts_manager_metadata]
                        )
                        pm_dialog_panel, pm_dialog_msg = pm_dialog.ui()

                        with FormRow(visible=False, variant="panel") as prompts_info_panel:
                            prompts_manager_metadata.render()
                        with FormRow():
                            models = ["Auto"]
                            if lpp.tag_data:
                                source = lpp.sources[lpp.tag_data.source]
                                models += source.supported_models

                            prompts_format = gr.Dropdown(
                                label="Prompts Format",
                                choices=models,
                                value="Auto",
                                scale=8
                            )
                            autofill_tags_filter = gr.Checkbox(
                                label="Autoload Filters",
                                value=True,
                                elem_id="lpp-autofill-filter-chbox",
                                scale=2,
                                min_width=120
                            )
                        # Booru Query & Promts Info Panels --------------------
                        with FormRow(variant="panel", elem_id="lpp-query-panel"):
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
                                self.query_panels = get_query_panels(source.value)

                    # Filtering Options Panel ---------------------------------
                    with FormColumn():
                        with FormRow():
                            quick_filter = gr.Textbox(
                                label="Quick Filter",
                                lines=1,
                                max_lines=1,
                                interactive=True,
                                placeholder="Type in comma-separated patterns here to filter them out"
                            )
                            clear_qfilter_btn = ToolButton("🧹")
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
                                elem_id="lpp-chbox-group"
                            )

            # Filter Editor ###################################################
            with gr.Tab("Filter Editor"):
                with FormRow():
                    # Filter Managment Panel ----------------------------------
                    with FormColumn(scale=1, min_width=300):
                        with FormRow():
                            fe_filter_name = gr.Dropdown(
                                label="Create or delete a filter:",
                                choices=lpp.filters,
                                allow_custom_value=True
                            )
                            fe_save_btn = ToolButton("✨")
                            fe_delete_btn = ToolButton("❌", visible=False)
                        fe_dialog = ConfirmationDialog(
                            lambda name: [
                                gr.Dropdown.update(choices=lpp.filters),
                                gr.Dropdown.update(
                                    value=name, choices=lpp.filters
                                ),
                                gr.Button.update(visible=True),
                                gr.Button.update(visible=False)
                            ],
                            [filters, fe_filter_name, fe_save_btn, fe_delete_btn]
                        )
                        fe_dialog_panel, fe_dialog_msg = fe_dialog.ui()
                        with FormRow():
                            fe_legacy_filters_btn = gr.Button(
                                "Import Legacy Filters"
                            )
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

                    # Filter Editors ------------------------------------------
                    FilterEditor.external_inputs += [filters, fe_filter_name]
                    filter_editors = []
                    for i in range(get_opt("lpp_editors_count", 3)):
                        filter_editors.append(FilterEditor())
                        filter_editors[i].ui()

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(source, prompts_format, prompts_manager_input,
                          filters, fe_filter_name)

            # Prompt Manager Event Handlers ###################################
            # Send Query Buttons
            def send_request_click(source, prompts_format, *params):
                models = ["Auto"] + lpp.sources[source].supported_models
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

            # Source Radio Change
            source.change(
                lambda s: [
                    gr.update(
                        visible=(s == x)
                    ) for x in self.query_panels.keys()
                ],
                [source],
                [x.panel for x in self.query_panels.values()],
                show_progress="hidden"
            )

            # Prompts Info Button Click
            def prompts_info_click():
                self.prompt_info_visible = not self.prompt_info_visible
                variant = "primary" if self.prompt_info_visible else "secondary"
                return (
                    gr.update(visible=self.prompt_info_visible),
                    gr.update(variant=variant)
                )

            prompts_info_btn.click(
                prompts_info_click,
                [],
                [prompts_info_panel, prompts_info_btn],
                show_progress="hidden"
            )

            # Save Button Click
            def save_prompts_click(name, filters):
                pm_dialog.set_action(
                    lambda: lpp.try_save_prompts(name, filters),
                    name
                )
                if name in lpp.saved_collections_names:
                    return (
                        gr.update(),
                        gr.update(),
                        f"Are you sure you want to overwrite \"{name}\"?",
                        gr.update(visible=True)
                    )
                else:
                    lpp.try_save_prompts(name, filters)
                    return (
                        gr.Dropdown.update(
                            choices=lpp.saved_collections_names
                        ),
                        gr.update(value=lpp.try_get_tag_data_markdown(name)),
                        "", gr.update(visible=False)
                    )

            save_prompts_btn.click(
                save_prompts_click,
                [prompts_manager_input, filters],
                [prompts_manager_input, prompts_manager_metadata,
                 pm_dialog_msg, pm_dialog_panel],
                show_progress="hidden"
            )

            # Load Button Click
            def load_prompts_click(name, autofill_tags_filter, current_model):
                lpp.try_load_prompts(name)
                filters_update = gr.update()
                if lpp.tag_data:
                    source = lpp.tag_data.source
                    models = ["Auto"] + lpp.sources[source].supported_models
                    models_update = gr.update(
                        choices=models,
                        value=current_model if current_model in models
                        else models[0]
                    )

                    params = lpp.tag_data.other_params
                    if "filters" in params and params["filters"] and autofill_tags_filter:
                        filters_update = gr.update(value=params["filters"])
                else:
                    models_update = gr.update()

                return (
                    lpp.status,
                    filters_update,
                    models_update
                )
            load_prompts_btn.click(
                load_prompts_click,
                [prompts_manager_input, autofill_tags_filter, prompts_format],
                [status_bar, filters, prompts_format],
                show_progress="hidden"
            )

            # Delete Button Click
            def delete_click(name):
                pm_dialog.set_action(lambda: lpp.try_delete_prompts(name), "")
                return (f"Are you sure you want to delete \"{name}\"?",
                        gr.update(visible=True))

            delete_prompts_btn.click(
                delete_click,
                [prompts_manager_input],
                [pm_dialog_msg, pm_dialog_panel],
                show_progress="hidden"
            )

            # Load Prompts Dropdown Change
            prompts_manager_input.change(
                lambda n: lpp.try_get_tag_data_markdown(n),
                [prompts_manager_input],
                [prompts_manager_metadata],
                show_progress="hidden"
            )

            # Quick Filter Button
            clear_qfilter_btn.click(
                lambda: gr.update(value=""),
                [],
                [quick_filter],
                show_progress="hidden"
            )

            # Filters Editor Event Handlers ###################################
            # Filter Name Dropdown Change -------------------------------------
            fe_filter_name.change(
                lambda n: (gr.update(visible=False), gr.update(visible=True))
                if n in lpp.filters
                else (gr.update(visible=True), gr.update(visible=False)),
                [fe_filter_name],
                [fe_save_btn, fe_delete_btn]
            )

            # Save Button -----------------------------------------------------
            def fe_save_click(name: str):
                lpp.try_save_filter(name, FilterData.from_string(""))
                return (
                    gr.update(choices=lpp.filters),
                    gr.update(choices=lpp.filters),
                    gr.update(visible=False),
                    gr.update(visible=True)
                )

            fe_save_btn.click(
                fe_save_click,
                [fe_filter_name],
                [filters, fe_filter_name, fe_save_btn, fe_delete_btn],
                show_progress="hidden"
            )

            # Delete Button ---------------------------------------------------
            def fe_delete_click(name: str):
                fe_dialog.set_action(lambda: lpp.try_delete_filter(name), "")
                return (gr.update(visible=True),
                        f"Are you sure you want ot delete \"{name}\"?")

            fe_delete_btn.click(
                fe_delete_click,
                [fe_filter_name],
                [fe_dialog_panel, fe_dialog_msg],
                show_progress="hidden"
            )

            # Import Legacy Filters Button ------------------------------------
            def fe_legacy_filters_click():
                lpp.import_legacy_filters()
                return (gr.update(choices=lpp.filters),
                        gr.update(choices=lpp.filters))

            fe_legacy_filters_btn.click(
                fe_legacy_filters_click,
                None,
                [filters, fe_filter_name]
            )
        return [lpp_enable, prompts_format, rating_filter, quick_filter, filters]

    def process(self, p, enabled, prompts_format, allowed_ratings,
                quick_filter, filter_names):
        if not enabled:
            return p

        if prompts_format == "Auto":
            model_hashes = {
                "67ab2fd8ec": Models.PDV56.value,   # PD V6 XL
                "6fdb703d7d": Models.PDV56.value,   # PD V5.5
                "51e44370f4": Models.PDV56.value,   # PD V5
                "821628644e": Models.EF.value,      # EasyFluff V11.2
                "461c3bbd5c": Models.SEAART.value,  # SeaArt Furry v1.0
                "821aa5537f": Models.ANIME.value,   # AutismMix_pony
                "ac006fdd7e": Models.ANIME.value,   # AutismMix_confetti
            }
            if p.sd_model_hash not in model_hashes:
                prompts_format = Models.PDV56.value
            else:
                prompts_format = model_hashes[p.sd_model_hash]

        n_images = p.batch_size * p.n_iter
        filters = lpp.get_filters(filter_names)
        if quick_filter:
            filters += [FilterData.from_string(quick_filter, ",")]
        p.all_prompts = lpp.try_choose_prompts(
            prompts_format, p.prompt, n_images, None, allowed_ratings, filters
        )

        p.all_prompts = [
            shared.prompt_styles.apply_styles_to_prompt(x, p.styles)
            for x in p.all_prompts
        ]

        if p.enable_hr:
            p.all_hr_prompts = p.all_prompts
            p.all_hr_negative_prompts = [p.negative_prompt] * n_images
