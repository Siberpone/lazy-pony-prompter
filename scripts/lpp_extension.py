import gradio as gr
import modules.scripts as scripts
from lpp import LazyPonyPrompter as LPP
from lpp_utils import get_merged_config_entry

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


class Scripts(scripts.Script):
    def __init__(self):
        self.lpp = LPP(base_dir)
        self.config = get_merged_config_entry("a1111_ui", base_dir)

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
                auto_negative_prompt = gr.Checkbox(
                    label="Include Standard Negative Prompt",
                    value=self.config["include_standard_negative_prompt"]
                )

            with gr.Column(variant="compact"):
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
                                    choices=self.lpp.get_filter_names()
                                )
                                filter_type.value = filter_type.choices[0]
                                sort_type = gr.Dropdown(
                                    label="Sort by",
                                    choices=self.lpp.get_sort_option_names()
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
                with gr.Accordion("Saving & Loading", open=False):
                    with gr.Row():
                        with gr.Column():
                            save_prompts_name = gr.Textbox(
                                label="Save Current Prompts as"
                            )
                            save_prompts_btn = gr.Button(value="Save")
                        with gr.Column():
                            load_prompts_name = gr.Dropdown(
                                label="Load Saved Prompts",
                                choices=self.lpp.get_cached_prompts_names()
                            )
                            with gr.Row():
                                with gr.Column():
                                    load_prompts_btn = gr.Button(value="Load")
                                with gr.Column():
                                    with gr.Row():
                                        delete_prompts_btn = gr.Button("Delete")
                                        confirm_delete_prompts_btn = gr.Button("Confirm delete", variant="stop", visible=False)
                                        cancel_delete_prompts_btn = gr.Button("Cancel", visible=False)
                    with gr.Row():
                        load_prompts_metadata = gr.JSON(
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
            set_no_config(enabled, auto_negative_prompt, query_textbox,
                          prompts_count, filter_type, sort_type, prefix,
                          suffix, tag_filter, send_btn, status_bar,
                          save_prompts_name, load_prompts_name,
                          save_prompts_btn, load_prompts_btn,
                          load_prompts_metadata, delete_prompts_btn,
                          confirm_delete_prompts_btn, cancel_delete_prompts_btn)

            # Event Handlers --------------------------------------------------
            # Send Button Click
            def send_derpibooru_request(*args, **kwargs):
                try:
                    self.lpp.send_derpibooru_request(*args, **kwargs)
                    return format_status_msg(
                        self.lpp, "Successfully fetched tags from Derpibooru."
                    )
                except Exception as e:
                    return format_status_msg(
                        self.lpp, f"Filed to fetch tags: {str(e)}"
                    )

            send_btn.click(
                lambda *args: send_derpibooru_request(*args),
                inputs=[query_textbox, prompts_count, filter_type, sort_type],
                outputs=[status_bar],
                show_progress="full"
            )

            # Save Button Click
            def save_prompts(name):
                try:
                    self.lpp.cache_current_prompts(name)
                    msg = format_status_msg(
                        self.lpp, f"Prompts saved as \"{name}\"."
                    )
                except Exception as e:
                    msg = format_status_msg(
                        self.lpp, f"Failed to save prompts: {str(e)}."
                    )
                return (
                    msg,
                    gr.Dropdown.update(
                        choices=list(self.lpp.get_cached_prompts_names())
                    ),
                    gr.Textbox.update(value="")
                )

            save_prompts_btn.click(
                lambda name: save_prompts(name),
                inputs=[save_prompts_name],
                outputs=[status_bar, load_prompts_name, save_prompts_name]
            )

            # Load Button Click
            def load_prompts(name):
                try:
                    self.lpp.load_cached_prompts(name)
                    msg = format_status_msg(self.lpp, f"Loaded \"{name}\".")
                except Exception as e:
                    msg = format_status_msg(
                        self.lpp, f"Failed to load prompts: {str(e)}."
                    )
                return (msg, gr.JSON.update(visible=False))

            load_prompts_btn.click(
                lambda name: load_prompts(name),
                inputs=[load_prompts_name],
                outputs=[status_bar, load_prompts_metadata]
            )

            # Load Prompts Dropdown Change
            def load_prompts_metadata_update(name):
                try:
                    return gr.JSON.update(
                        value=self.lpp.get_cached_prompts_metadata(name),
                        visible=True
                    )
                except Exception as e:
                    return gr.JSON.update(visible=False)

            load_prompts_name.change(
                lambda name: load_prompts_metadata_update(name),
                inputs=[load_prompts_name],
                outputs=[load_prompts_metadata]
            )

            # Delete Prompts Buttons
            def delete_prompts(name):
                try:
                    self.lpp.delete_cached_prompts(name)
                    msg = format_status_msg(self.lpp, f"\"{name}\" deleted.")
                except Exception as e:
                    msg = format_status_msg(
                        self.lpp, f"Failed to delete prompts: {str(e)}."
                    )
                return (
                    msg,
                    gr.Dropdown.update(
                        choices=list(self.lpp.get_cached_prompts_names()),
                        value=""
                    ),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
            delete_prompts_buttons = [delete_prompts_btn,
                                      confirm_delete_prompts_btn,
                                      cancel_delete_prompts_btn]
            confirm_delete_prompts_btn.click(
                lambda name: delete_prompts(name),
                [load_prompts_name],
                [status_bar, load_prompts_name] + delete_prompts_buttons
            )
            delete_prompts_btn.click(
                lambda: [gr.update(visible=False),
                         gr.update(visible=True),
                         gr.update(visible=True)],
                None,
                delete_prompts_buttons
            )
            cancel_delete_prompts_btn.click(
                lambda: [gr.update(visible=True),
                         gr.update(visible=False),
                         gr.update(visible=False)],
                None,
                delete_prompts_buttons
            )
        return [enabled, auto_negative_prompt, prefix, suffix, tag_filter]

    def process(self, p, enabled, auto_negative_prompt,
                prefix, suffix, tag_filter):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.choose_prompts(n_images, prefix,
                                                suffix, tag_filter)
        if auto_negative_prompt:
            for i, np in enumerate(p.all_negative_prompts):
                p.all_negative_prompts[i] = ", ".join(
                    [x for x in
                        [p.negative_prompt, self.lpp.get_negative_prompt()]
                        if x]
                )
