import gradio as gr
import modules.scripts as scripts
from lpp import LazyPonyPrompter as LPP
from lpp_utils import get_merged_config_entry
import os

base_dir = scripts.basedir()


def get_lpp_status(lpp):
    n_prompts = lpp.get_loaded_prompts_count()
    return f"**{n_prompts}** prompts loaded. Ready to generate." \
        if n_prompts > 0 \
        else "No prompts loaded. Not ready to generate."


def format_status_msg(lpp, msg=""):
    return f"&nbsp;&nbsp;{msg} {get_lpp_status(lpp)}"


def set_no_config(*args):
    for control in args:
        setattr(control, "do_not_save_to_config", True)


def try_send_request(lpp, *args):
    try:
        lpp.request_prompts(*args)
        return format_status_msg(
            lpp, "Successfully fetched tags from Derpibooru."
        )
    except Exception as e:
        return format_status_msg(
            lpp, f"Filed to fetch tags: {str(e)}"
        )


def try_save_prompts(lpp, name, prefix, suffix, tag_filter):
    try:
        lpp.cache_current_prompts(name, prefix, suffix, tag_filter)
        return format_status_msg(
            lpp, f"Prompts saved as \"{name}\"."
        )
    except Exception as e:
        return format_status_msg(
            lpp, f"Failed to save prompts: {str(e)}."
        )


def try_load_prompts(lpp, name):
    try:
        lpp.load_cached_prompts(name)
        return format_status_msg(lpp, f"Loaded \"{name}\".")
    except Exception as e:
        return format_status_msg(
            lpp, f"Failed to load prompts: {str(e)}."
        )


def try_delete_prompts(lpp, name):
    try:
        lpp.delete_cached_prompts(name)
        return format_status_msg(
            lpp, f"\"{name}\" deleted."
        )
    except Exception as e:
        return format_status_msg(
            lpp, f"Failed to delete prompts: {str(e)}."
        )


class Scripts(scripts.Script):
    def __init__(self):
        self.lpp = LPP(base_dir)
        self.config = get_merged_config_entry("a1111_ui", os.path.join(
                                              base_dir, "config"))

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Accordion(
            "Lazy Pony Prompter",
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
                prompts_format = gr.Dropdown(
                    label="Prompts Format",
                    choices=self.lpp.get_formatters()
                )
                prompts_format.value = prompts_format.choices[0]
            with gr.Column():
                # Derpibooru Query Panel --------------------------------------
                with gr.Accordion(
                    "Derpibooru Query",
                    open=self.config["derpibooru_query_start_unfolded"]
                ):
                    with gr.Row():
                        query_textbox = gr.Textbox(
                            placeholder="Type in your Derpibooru query here",
                            show_label=False
                        )
                    with gr.Row():
                        with gr.Column():
                            prompts_count = gr.Slider(
                                label="Number of Prompts to Load",
                                minimum=self.config["prompts_count"]["min"],
                                maximum=self.config["prompts_count"]["max"],
                                step=self.config["prompts_count"]["step"],
                                value=self.config["prompts_count"]["default"]
                            )
                        with gr.Column():
                            with gr.Row():
                                filter_type = gr.Dropdown(
                                    label="Derpibooru Filter",
                                    choices=self.lpp.sources["derpi"].get_filters(
                                    )
                                )
                                filter_type.value = filter_type.choices[0]
                                sort_type = gr.Dropdown(
                                    label="Sort by",
                                    choices=self.lpp.sources["derpi"].get_sort_options(
                                    )
                                )
                                sort_type.value = sort_type.choices[0]
                    with gr.Row():
                        send_btn = gr.Button(value="Send")

                # Extra Options Panel -----------------------------------------
                with gr.Accordion(
                    "Extra Options",
                    open=self.config["extra_options_start_unfolded"]
                ):
                    with gr.Row():
                        prefix = gr.Textbox(
                            label="Prompts Prefix:",
                            interactive=True,
                            value=self.config["prefix"],
                            placeholder="Prompts will begin with this text"
                        )
                        suffix = gr.Textbox(
                            label="Prompts Suffix:",
                            value=self.config["suffix"],
                            interactive=True,
                            placeholder="Prompts will end with this text"
                        )
                    with gr.Row():
                        tag_filter = gr.Textbox(
                            label="Prune These Tags from Prompts:",
                            placeholder="These tags (comma separated) will be pruned from prompts"
                        )

                # Save/Load Prompts Panel -------------------------------------
                with gr.Accordion("Prompts Manager", open=False):
                    with gr.Row():
                        with gr.Column(scale=2):
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=self.lpp.get_cached_prompts_names(),
                                allow_custom_value=True
                            )
                        with gr.Column(scale=0, min_width=200):
                            autofill_extra_options = gr.Checkbox(
                                label="Autofill Extra Options",
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
                    value=format_status_msg(self.lpp)
                )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(enabled, query_textbox, source, prompts_format,
                          prompts_count, filter_type, sort_type, prefix,
                          suffix, tag_filter, send_btn, status_bar,
                          prompts_manager_input, save_prompts_btn,
                          load_prompts_btn, prompts_manager_metadata,
                          delete_prompts_btn, confirm_action_btn,
                          cancel_action_btn, confirm_action_type,
                          confirm_action_name, autofill_extra_options)

            # Event Handlers --------------------------------------------------
            # Send Button Click
            send_btn.click(
                lambda *args: try_send_request(self.lpp, *args),
                [source, query_textbox, prompts_count, filter_type, sort_type],
                [status_bar],
                show_progress="full"
            )

            # Save Button Click
            def save_prompts_click(name, prefix, suffix, tag_filter):
                if name in self.lpp.get_cached_prompts_names():
                    return (
                        format_status_msg(self.lpp),
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
                        try_save_prompts(self.lpp, name, prefix,
                                         suffix, tag_filter),
                        gr.Dropdown.update(
                            choices=self.lpp.get_cached_prompts_names()
                        ),
                        "", "", "", gr.update(visible=False)
                    )

            save_prompts_btn.click(
                save_prompts_click,
                [prompts_manager_input, prefix, suffix, tag_filter],
                [status_bar, prompts_manager_input, confirm_action_msg,
                 confirm_action_type, confirm_action_name,
                 confirm_action_dialog]
            )

            # Load Button Click
            def load_prompts_click(name, autofill_extra_opts):
                try:
                    prompts_data = self.lpp.get_prompts_metadata(name)
                except Exception as e:
                    prompts_data = {}

                def get_param(key):
                    if autofill_extra_opts:
                        return gr.update(value=prompts_data[key]) \
                            if key in prompts_data.keys() \
                            else gr.update(value="")
                    else:
                        return gr.update()

                prefix_update = get_param("prefix")
                suffix_update = get_param("suffix")
                tag_filter_update = get_param("tag_filter")
                return (
                    try_load_prompts(self.lpp, name),
                    gr.update(visible=False),
                    prefix_update,
                    suffix_update,
                    tag_filter_update,
                )
            load_prompts_btn.click(
                load_prompts_click,
                [prompts_manager_input, autofill_extra_options],
                [status_bar, prompts_manager_metadata,
                 prefix, suffix, tag_filter]
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
            def invoke_action(name, action_type, prefix, suffix, tag_filter):
                if action_type == "delete":
                    msg = try_delete_prompts(self.lpp, name)
                    selected_val = ""
                if action_type == "overwrite":
                    msg = try_save_prompts(
                        self.lpp, name, prefix, suffix, tag_filter
                    )
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
                [confirm_action_name, confirm_action_type,
                 prefix, suffix, tag_filter],
                [status_bar, prompts_manager_input,
                 confirm_action_dialog, prompts_manager_metadata]
            )
            cancel_action_btn.click(
                lambda: gr.update(visible=False),
                None,
                [confirm_action_dialog]
            )
        return [enabled, prompts_format, prefix, suffix, tag_filter]

    def process(self, p, enabled, prompts_format, prefix, suffix, tag_filter):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.choose_prompts(prompts_format, n_images,
                                                prefix, suffix, tag_filter)
