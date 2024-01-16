from lpp.a1111 import LPP_A1111
from dataclasses import dataclass
from modules import scripts
from modules import shared
from modules import script_callbacks
import gradio as gr
import logging

base_dir = scripts.basedir()


def set_no_config(*args: object) -> None:
    for control in args:
        setattr(control, "do_not_save_to_config", True)


def on_ui_settings():
    LPP_SECTION = ("lpp", "Lazy Pony Prompter")

    lpp_options = {
        "lpp_start_unfolded":
            shared.OptionInfo(False, "Start unfolded",),
        "lpp_query_panel_start_unfolded":
            shared.OptionInfo(
                False, "Query panel starts unfolded"
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


def get_opt(option, default):
    return getattr(shared.opts, option, default)


@dataclass
class QueryPanelData:
    panel: object
    send_btn: object
    params: list


class QueryPanels:
    __PROMPTS_MIN = 5
    __PROMPTS_MAX = 300
    __PROMPTS_STEP = 5
    __PROMPTS_DEFAULT = 100

    @staticmethod
    def Derpibooru(active_panel_name: str, lpp: LPP_A1111) -> QueryPanelData:
        NAME = "Derpibooru"
        with gr.Accordion(
            "💬 Derpibooru Query",
            open=get_opt("lpp_query_panel_start_unfolded", False),
            visible=(active_panel_name == NAME)
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
                        minimum=QueryPanels.__PROMPTS_MIN,
                        maximum=QueryPanels.__PROMPTS_MAX,
                        step=QueryPanels.__PROMPTS_STEP,
                        value=QueryPanels.__PROMPTS_DEFAULT
                    )
                with gr.Column():
                    with gr.Row():
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
            with gr.Row():
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
        with gr.Accordion(
            "💬 E621 Query",
            open=get_opt("lpp_query_panel_start_unfolded", False),
            visible=(active_panel_name == NAME)
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
                        minimum=QueryPanels.__PROMPTS_MIN,
                        maximum=QueryPanels.__PROMPTS_MAX,
                        step=QueryPanels.__PROMPTS_STEP,
                        value=QueryPanels.__PROMPTS_DEFAULT
                    )
                with gr.Column():
                    with gr.Row():
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
            with gr.Row():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, rating, sort_type)
            return QueryPanelData(
                panel,
                send_btn,
                [query, prompts_count, rating, sort_type]
            )


class Scripts(scripts.Script):
    def __init__(self):
        self.lpp: LPP_A1111 = LPP_A1111(
            base_dir,
            get_opt("lpp_derpibooru_api_key", None),
            get_opt("lpp_logging_level", None)
        )
        self.query_panels = {}
        self.prompt_manager_dialog_action = lambda: None

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Accordion(
            "💤 Lazy Pony Prompter",
            open=get_opt("lpp_start_unfolded", False)
        ):
            with gr.Row():
                enabled = gr.Checkbox(label="Enabled")
                source = gr.Dropdown(
                    label="Tags Source",
                    choices=self.lpp.source_names
                )
                source.value = source.choices[0]
                prompts_format = gr.Dropdown(label="Prompts Format")

            with gr.Column():
                # Query Panels ------------------------------------------------
                for attr in [
                    x for x in dir(QueryPanels) if not x.startswith("_")
                ]:
                    query_panel = getattr(QueryPanels, attr)
                    self.query_panels[query_panel.__name__] = query_panel(
                        source.value, self.lpp
                    )

                # Tags Filter -------------------------------------------------
                with gr.Accordion("🏷 Tags Filter", open=False):
                    with gr.Row():
                        with gr.Column(scale=2):
                            tag_filter = gr.Textbox(
                                show_label=False,
                                placeholder="These tags (comma separated) will be pruned from prompts"
                            )
                        with gr.Column(scale=0, min_width=130):
                            gr.ClearButton(components=[tag_filter])

                # Prompts Manager Panel ---------------------------------------
                with gr.Accordion("💾 Prompts Manager", open=False):
                    with gr.Row():
                        with gr.Column(scale=2):
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=self.lpp.saved_collections_names,
                                allow_custom_value=True
                            )
                        with gr.Column(scale=0, min_width=200):
                            autofill_tags_filter = gr.Checkbox(
                                label="Autofill Tags Filter"
                            )
                    with gr.Row():
                        save_prompts_btn = gr.Button(value="Save")
                        load_prompts_btn = gr.Button(value="Load")
                        delete_prompts_btn = gr.Button("Delete")
                    with gr.Row(variant="panel", visible=False) as prompt_manager_dialog:
                        with gr.Column():
                            with gr.Row():
                                pm_dialog_msg = gr.Markdown()
                            with gr.Row():
                                pm_dialog_confirm_btn = gr.Button(
                                    "Confirm", variant="stop")
                                pm_dialog_cancel_btn = gr.Button("Cancel")
                    with gr.Row():
                        prompts_manager_metadata = gr.JSON(
                            label="Prompts Info",
                            show_label=True,
                            visible=False
                        )

            # Status Bar ------------------------------------------------------
            with gr.Box():
                status_bar = gr.Markdown(
                    value=self.lpp.format_status_msg()
                )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(source, prompts_format, prompts_manager_input)

            # Event Handlers --------------------------------------------------
            # Send Query Buttons
            def send_request_click(source, prompts_format, *params):
                models = self.lpp.get_model_names(source)
                return (
                    self.lpp.try_send_request(source, *params),
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
                    self.lpp.try_save_prompts(name, tag_filter), \
                    name
                if name in self.lpp.saved_collections_names:
                    return (
                        self.lpp.format_status_msg(),
                        gr.update(),
                        f"Are you sure you want to overwrite \"{name}\"?",
                        gr.update(visible=True)
                    )
                else:
                    return (
                        self.lpp.try_save_prompts(name, tag_filter),
                        gr.Dropdown.update(
                            choices=self.lpp.saved_collections_names
                        ),
                        "", gr.update(visible=False)
                    )

            save_prompts_btn.click(
                save_prompts_click,
                [prompts_manager_input, tag_filter],
                [status_bar, prompts_manager_input, pm_dialog_msg,
                 prompt_manager_dialog]
            )

            # Load Button Click
            def load_prompts_click(name, autofill_tags_filter, current_model):
                msg = self.lpp.try_load_prompts(name)
                if self.lpp.tag_data:
                    source = self.lpp.tag_data.source
                    models = self.lpp.get_model_names(source)
                    models_update = gr.update(
                        choices=models,
                        value=current_model if current_model in models
                        else models[0]
                    )
                    metadata = self.lpp.tag_data.other_params
                    tag_filter_update = metadata["tag_filter"] \
                        if "tag_filter" in metadata and autofill_tags_filter \
                        else ""
                else:
                    models_update = gr.update()
                    tag_filter_update = gr.update()

                return (
                    msg,
                    gr.update(visible=False),
                    tag_filter_update,
                    models_update
                )
            load_prompts_btn.click(
                load_prompts_click,
                [prompts_manager_input, autofill_tags_filter, prompts_format],
                [status_bar, prompts_manager_metadata, tag_filter, prompts_format]
            )

            # Delete Button Click
            def delete_click(name):
                self.prompt_manager_dialog_action = lambda: \
                    self.lpp.try_delete_prompts(name), \
                    ""
                return [f"Are you sure you want to delete \"{name}\"?",
                        gr.update(visible=True)]
            delete_prompts_btn.click(
                delete_click,
                [prompts_manager_input],
                [pm_dialog_msg, prompt_manager_dialog]
            )

            # Load Prompts Dropdown Change
            def load_prompts_metadata_update(name):
                success, metadata = self.lpp.try_get_tag_data_json(name)
                if success:
                    return gr.JSON.update(value=metadata, visible=True)
                else:
                    return gr.JSON.update(visible=False)

            prompts_manager_input.change(
                load_prompts_metadata_update,
                [prompts_manager_input],
                [prompts_manager_metadata]
            )

            # Action Confirmation Dialog
            def invoke_action():
                msg = self.prompt_manager_dialog_action[0]()
                selected_val = self.prompt_manager_dialog_action[1]
                return (
                    msg,
                    gr.Dropdown.update(
                        choices=list(self.lpp.saved_collections_names),
                        value=selected_val
                    ),
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
            pm_dialog_confirm_btn.click(
                invoke_action,
                None,
                [status_bar, prompts_manager_input,
                 prompt_manager_dialog, prompts_manager_metadata]
            )
            pm_dialog_cancel_btn.click(
                lambda: gr.update(visible=False),
                None,
                [prompt_manager_dialog]
            )
        return [enabled, prompts_format, tag_filter]

    def process(self, p, enabled, prompts_format, tag_filter):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.try_choose_prompts(
            prompts_format, p.prompt, n_images, tag_filter
        )

        p.all_prompts = [
            shared.prompt_styles.apply_styles_to_prompt(x, p.styles)
            for x in p.all_prompts
        ]
