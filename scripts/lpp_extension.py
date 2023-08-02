import gradio as gr
import modules.scripts as scripts
from lpp import LazyPonyPrompter as LPP
from lpp_utils import get_merged_config_entry

base_dir = scripts.basedir()


class Scripts(scripts.Script):
    def __init__(self):
        self.lpp = LPP(base_dir)
        self.config = get_merged_config_entry("a1111_ui", base_dir)

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):

        def get_lpp_status():
            n_prompts = self.lpp.get_loaded_prompts_count()
            return f"**{n_prompts}** prompts loaded. Ready to generate." \
                if n_prompts > 0 \
                else "No prompts loaded. Not ready to generate."

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

            # Derpibooru Query Panel ------------------------------------------
            with gr.Row():
                with gr.Column(scale=3):
                    query_textbox = gr.Textbox(
                        placeholder="Type in your Derpibooru query here",
                        show_label=False
                    )
                with gr.Column(scale=1):
                    send_btn = gr.Button(value="Send")

            # Extra Options Panel ---------------------------------------------
            with gr.Accordion(
                "Extra Options",
                open=self.config["extra_options_start_unfolded"]
            ):
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

            # Save/Load Prompts Panel -----------------------------------------
            with gr.Accordion("Saving & Loading", open=False):
                with gr.Row():
                    save_prompts_name = gr.Textbox(
                        label="Save Current Prompts as"
                    )
                    load_prompts_name = gr.Dropdown(
                        label="Load Saved Prompts",
                        choices=self.lpp.get_cached_prompts_names()
                    )
                with gr.Row():
                    save_prompts_btn = gr.Button(value="Save")
                    load_prompts_btn = gr.Button(value="Load")

            # Status Bar ------------------------------------------------------
            status_bar = gr.Markdown(
                value=f"&nbsp;&nbsp;{get_lpp_status()}"
            )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            def set_no_config(*args):
                for control in args:
                    setattr(control, "do_not_save_to_config", True)

            set_no_config(enabled, auto_negative_prompt, query_textbox,
                          prompts_count, filter_type, sort_type, prefix,
                          suffix, tag_filter, send_btn, status_bar,
                          save_prompts_name, load_prompts_name,
                          save_prompts_btn, load_prompts_btn)

            # Button Click Handlers -------------------------------------------
            # "Send"
            def send_derpibooru_request(*args, **kwargs):
                try:
                    self.lpp.send_derpibooru_request(*args, **kwargs)
                    return f"&nbsp;&nbsp;Successfully fetched tags from Derpibooru. {get_lpp_status()}"
                except Exception as e:
                    return f"&nbsp;&nbsp;Filed to fetch tags: {str(e)}"

            send_btn.click(
                lambda *args: send_derpibooru_request(*args),
                inputs=[query_textbox, prompts_count, filter_type, sort_type],
                outputs=[status_bar],
                show_progress="full"
            )

            # "Save"
            def save_prompts(name):
                try:
                    self.lpp.cache_current_prompts(name)
                    return (
                        f"&nbsp;&nbsp;Prompts saved as \"{name}\". {get_lpp_status()}",
                        gr.Dropdown.update(
                            choices=list(self.lpp.get_cached_prompts_names())
                        )
                    )
                except Exception as e:
                    return (
                        f"&nbsp;&nbsp;Failed to save prompts: {str(e)}. {get_lpp_status()}",
                        gr.Dropdown.update(
                            choices=list(self.lpp.get_cached_prompts_names())
                        )
                    )

            save_prompts_btn.click(
                lambda name: save_prompts(name),
                inputs=[save_prompts_name],
                outputs=[status_bar, load_prompts_name]
            )

            # "Load"
            def load_prompts(name):
                try:
                    self.lpp.load_cached_prompts(name)
                    return f"&nbsp;&nbsp;Loaded \"{name}\". {get_lpp_status()}"
                except Exception as e:
                    return f"&nbsp;&nbsp;Failed to load prompts: {str(e)}. {get_lpp_status()}"

            load_prompts_btn.click(
                lambda name: load_prompts(name),
                inputs=[load_prompts_name],
                outputs=[status_bar]
            )
        return [enabled, auto_negative_prompt, prefix, suffix, tag_filter]

    def process(self, p, enabled, auto_negative_prompt, prefix, suffix, tag_filter):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.choose_prompts(n_images, prefix, suffix, tag_filter)

        if auto_negative_prompt:
            for i, np in enumerate(p.all_negative_prompts):
                p.all_negative_prompts[i] = ", ".join(
                    [x for x in [p.negative_prompt, self.lpp.get_negative_prompt()] if x]
                )
