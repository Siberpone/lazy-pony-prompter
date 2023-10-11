from lpp import LazyPonyPrompter as LPP
from lpp_utils import get_merged_config_entry, LPPWrapper
from modules.styles import merge_prompts as merge_prompt_as_style
import gradio as gr
import modules.scripts as scripts
import modules.shared as shared
import os

base_dir = scripts.basedir()


def set_no_config(*args):
    for control in args:
        setattr(control, "do_not_save_to_config", True)


class QueryPanels():
    @staticmethod
    def derpi(active_panel_name, lpp, config):
        with gr.Accordion(
            "💬 Derpibooru Query",
            open=config["derpibooru_query_start_unfolded"],
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
                            choices=lpp.sources["derpi"]["instance"].get_filters()
                        )
                        filter_type.value = filter_type.choices[0]
                        sort_type = gr.Dropdown(
                            label="Sort by",
                            choices=lpp.sources["derpi"]["instance"].get_sort_options()
                        )
                        sort_type.value = sort_type.choices[0]
            with gr.Row():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count, filter_type, sort_type)
            return {
                "panel": panel,
                "send_btn": send_btn,
                "params": [query, prompts_count, filter_type, sort_type]
            }

    @staticmethod
    def e621(active_panel_name, lpp, config):
        with gr.Accordion(
            "💬 E621 Query",
            open=config["derpibooru_query_start_unfolded"],
            visible=(active_panel_name == "E621")
        ) as panel:
            gr.Markdown(
                "[🔗 Syntax Help](https://e621.net/help/cheatsheet)")
            with gr.Row():
                with gr.Column(scale=2):
                    query = gr.Textbox(
                        placeholder="Type in Your E621 query here",
                        show_label=False
                    )
                with gr.Column(scale=1):
                    prompts_count = gr.Slider(
                        label="Number of Prompts to Load",
                        minimum=config["prompts_count"]["min"],
                        maximum=config["prompts_count"]["max"],
                        step=config["prompts_count"]["step"],
                        value=config["prompts_count"]["default"]
                    )
            with gr.Row():
                send_btn = gr.Button(value="Send")
            set_no_config(query, prompts_count)
            return {
                "panel": panel,
                "send_btn": send_btn,
                "params": [query, prompts_count]
            }


class Scripts(scripts.Script):
    def __init__(self):
        self.lpp = LPP(base_dir)
        self.lpp_wrapper = LPPWrapper(self.lpp)
        self.config = get_merged_config_entry(
            "a1111_ui", os.path.join(base_dir, "config")
        )
        self.query_panels = {}

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Accordion(
            "💤 Lazy Pony Prompter",
            open=self.config["start_unfolded"]
        ):
            with gr.Row():
                enabled = gr.Checkbox(
                    label="Enabled",
                    value=self.config["enabled"]
                )
                source = gr.Dropdown(
                    label="Tags Source",
                    choices=self.lpp.get_sources()
                )
                source.value = source.choices[0]
                prompts_format = gr.Dropdown(label="Prompts Format")

            with gr.Column():
                # Query Panels ------------------------------------------------
                for attr in filter(
                    lambda x: not x.startswith("_"), dir(QueryPanels)
                ):
                    query_panel = getattr(QueryPanels, attr)
                    self.query_panels[query_panel.__name__] = query_panel(
                        source.value, self.lpp, self.config
                    )

                # Extra Tags Filter -------------------------------------------
                with gr.Accordion("🏷 Tags Filter", open=False):
                    with gr.Row():
                        tag_filter = gr.Textbox(
                            show_label=False,
                            placeholder="These tags (comma separated) will be pruned from prompts"
                        )

                # Prompts Manager Panel ---------------------------------------
                with gr.Accordion("💾 Prompts Manager", open=False):
                    with gr.Row():
                        with gr.Column(scale=2):
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=self.lpp.get_cached_prompts_names(),
                                allow_custom_value=True
                            )
                        with gr.Column(scale=0, min_width=200):
                            autofill_tags_filter = gr.Checkbox(
                                label="Autofill Tags Filter",
                                value=self.config["autofill_extra_options"]
                            )
                    with gr.Row():
                        save_prompts_btn = gr.Button(value="Save")
                        load_prompts_btn = gr.Button(value="Load")
                        delete_prompts_btn = gr.Button("Delete")
                    with gr.Row(variant="panel", visible=False) as confirm_action_dialog:
                        with gr.Column():
                            with gr.Row():
                                confirm_action_msg = gr.Markdown()
                                confirm_action_type = gr.Textbox(visible=False)
                                confirm_action_name = gr.Textbox(visible=False)
                            with gr.Row():
                                confirm_action_btn = gr.Button(
                                    "Confirm", variant="stop")
                                cancel_action_btn = gr.Button("Cancel")
                    with gr.Row():
                        prompts_manager_metadata = gr.JSON(
                            label="Prompts Info",
                            show_label=True,
                            visible=False
                        )

            # Status Bar ------------------------------------------------------
            with gr.Box():
                status_bar = gr.Markdown(
                    value=self.lpp_wrapper.format_status_msg()
                )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(enabled, source, prompts_format, tag_filter,
                          status_bar, prompts_manager_input, save_prompts_btn,
                          load_prompts_btn, prompts_manager_metadata,
                          delete_prompts_btn, confirm_action_btn,
                          cancel_action_btn, confirm_action_type,
                          confirm_action_name, autofill_tags_filter)

            # Event Handlers --------------------------------------------------
            # Send Query Buttlons
            for panel in self.query_panels.values():
                panel["send_btn"].click(
                    lambda s, *params: (
                        self.lpp_wrapper.try_send_request(s, *params),
                        gr.update(
                            choices=self.lpp.get_models(s),
                            value=self.lpp.get_models(s)[0]
                        )
                    ),
                    [source, *panel["params"]],
                    [status_bar, prompts_format],
                    show_progress="full"
                )

            # Source Dropdown Change
            source.change(
                lambda s: [
                    gr.update(visible=(
                        s == self.lpp.sources[x]["pretty_name"])
                    ) for x in self.query_panels.keys()
                ],
                [source],
                [x["panel"] for x in self.query_panels.values()]
            )

            # Save Button Click
            def save_prompts_click(name, tag_filter):
                if name in self.lpp.get_cached_prompts_names():
                    return (
                        self.lpp_wrapper.format_status_msg(),
                        gr.Dropdown.update(
                            choices=self.lpp.get_cached_prompts_names()
                        ),
                        f"Are you sure you want to overwrite \"{name}\"?",
                        "overwrite",
                        name,
                        gr.update(visible=True)
                    )
                else:
                    return (
                        self.lpp_wrapper.try_save_prompts(name, tag_filter),
                        gr.Dropdown.update(
                            choices=self.lpp.get_cached_prompts_names()
                        ),
                        "", "", "", gr.update(visible=False)
                    )

            save_prompts_btn.click(
                save_prompts_click,
                [prompts_manager_input, tag_filter],
                [status_bar, prompts_manager_input, confirm_action_msg,
                 confirm_action_type, confirm_action_name,
                 confirm_action_dialog]
            )

            # Load Button Click
            def load_prompts_click(name, autofill_extra_opts):
                try:
                    prompts_data = self.lpp.get_prompts_metadata(name)
                    models = self.lpp.get_models(prompts_data["source"])
                    models_update = gr.update(
                        choices=models,
                        value=models[0]
                    )
                except Exception as e:
                    prompts_data = {}
                    models_update = gr.update()

                def get_param(key):
                    if autofill_extra_opts:
                        return gr.update(value=prompts_data[key]) \
                            if key in prompts_data.keys() \
                            else gr.update(value="")
                    else:
                        return gr.update()

                tag_filter_update = get_param("tag_filter")
                return (
                    self.lpp_wrapper.try_load_prompts(name),
                    gr.update(visible=False),
                    tag_filter_update,
                    models_update
                )
            load_prompts_btn.click(
                load_prompts_click,
                [prompts_manager_input, autofill_tags_filter],
                [status_bar, prompts_manager_metadata, tag_filter, prompts_format]
            )

            # Delete Button Click
            delete_prompts_btn.click(
                lambda name: [f"Are you sure you want to delete \"{name}\"?",
                              "delete",
                              name,
                              gr.update(visible=True)],
                [prompts_manager_input],
                [confirm_action_msg, confirm_action_type,
                 confirm_action_name, confirm_action_dialog]
            )

            # Load Prompts Dropdown Change
            def load_prompts_metadata_update(name):
                try:
                    return gr.JSON.update(
                        value=self.lpp.get_prompts_metadata(name),
                        visible=True
                    )
                except Exception as e:
                    return gr.JSON.update(visible=False)

            prompts_manager_input.change(
                load_prompts_metadata_update,
                [prompts_manager_input],
                [prompts_manager_metadata]
            )

            # Action Confirmation Dialog
            def invoke_action(name, action_type, tag_filter):
                if action_type == "delete":
                    msg = self.lpp_wrapper.try_delete_prompts(name)
                    selected_val = ""
                if action_type == "overwrite":
                    msg = self.lpp_wrapper.try_save_prompts(name, tag_filter)
                    selected_val = name
                return (
                    msg,
                    gr.Dropdown.update(
                        choices=list(self.lpp.get_cached_prompts_names()),
                        value=selected_val
                    ),
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
            confirm_action_btn.click(
                invoke_action,
                [confirm_action_name, confirm_action_type, tag_filter],
                [status_bar, prompts_manager_input,
                 confirm_action_dialog, prompts_manager_metadata]
            )
            cancel_action_btn.click(
                lambda: gr.update(visible=False),
                None,
                [confirm_action_dialog]
            )
        return [enabled, prompts_format, tag_filter]

    def process(self, p, enabled, prompts_format, tag_filter):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.choose_prompts(
            prompts_format, n_images, tag_filter
        )

        if p.prompt:
            p.all_prompts = [
                merge_prompt_as_style(p.prompt, x) for x in p.all_prompts
            ]

        p.all_prompts = [
            shared.prompt_styles.apply_styles_to_prompt(x, p.styles)
            for x in p.all_prompts
        ]
