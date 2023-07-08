import gradio as gr
import modules.scripts as scripts
from lpp import LazyPonyPrompter as LPP


class Scripts(scripts.Script):
    lpp = LPP(scripts.basedir())

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

        with gr.Accordion("Lazy Pony Prompter", open=False):
            enabled = gr.Checkbox(label="Enabled", value=False)
            auto_negative_prompt = gr.Checkbox(
                label="Include negative prompt",
                value=True
            )

            # Derpibooru Query Panel ------------------------------------------
            with gr.Column(variant="panel"):
                query_textbox = gr.Textbox(
                    label="Derpibooru Quiery"
                )
                with gr.Row():
                    prompts_count = gr.Slider(
                        label="Number of prompts to load",
                        minimum=1,
                        maximum=200,
                        step=1,
                        value=50
                    )
                    filter_type = gr.Dropdown(
                        label="Derpibooru Filter",
                        choices=self.lpp.filters.keys(),
                        scale=1
                    )
                    filter_type.value = filter_type.choices[0]
                    sort_type = gr.Dropdown(
                        label="Sort by",
                        choices=self.lpp.sort_params.keys()
                    )
                    sort_type.value = sort_type.choices[0]
                fetch_tags_btn = gr.Button(
                    value="Fetch Tags",
                    size="sm"
                )

            # Save/Load Prompts Panel -----------------------------------------
            with gr.Column(variant="panel"):
                with gr.Row(scale=4):
                    save_prompts_name = gr.Textbox(
                        label="Save Current Prompts As"
                    )
                    load_prompts_name = gr.Dropdown(
                        label="Load Saved Prompts",
                        choices=self.lpp.get_cached_prompts_names()
                    )
                with gr.Row(scale=1):
                    save_prompts_btn = gr.Button(
                        value="Save",
                        size="sm"
                    )
                    load_prompts_btn = gr.Button(
                        value="Load",
                        size="sm"
                    )

            # Status Bar ------------------------------------------------------
            with gr.Box():
                status_bar = gr.Markdown(
                    value=f"&nbsp;&nbsp;{get_lpp_status()}"
                )

            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            def set_no_config(*args):
                for control in args:
                    setattr(control, "do_not_save_to_config", True)

            set_no_config(enabled, auto_negative_prompt, query_textbox,
                          prompts_count, filter_type, sort_type, fetch_tags_btn,
                          status_bar, save_prompts_name, load_prompts_name,
                          save_prompts_btn, load_prompts_btn)

            # Button Click Handlers -------------------------------------------
            # "Fetch Tags"
            def fetch_prompts(*args, **kwargs):
                try:
                    self.lpp.fetch_prompts(*args, **kwargs)
                    return f"&nbsp;&nbsp;Successfully fetched tags from Derpibooru. {get_lpp_status()}"
                except Exception as e:
                    return f"&nbsp;&nbsp;Filed to fetch tags: {e=}, {type(e)=}"

            fetch_tags_btn.click(
                lambda q, n, f, s: fetch_prompts(q, n, f, s),
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
                    return f"&nbsp;&nbsp;Failed to save prompts: {e=}, {type(e)=}. {get_lpp_status()}"

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
                    return f"&nbsp;&nbsp;Failed to load \"{name}\": {e=}, {type(e)=}. {get_lpp_status()}"

            load_prompts_btn.click(
                lambda name: load_prompts(name),
                inputs=[load_prompts_name],
                outputs=[status_bar]
            )
        return [enabled, auto_negative_prompt]

    def process(self, p, enabled, auto_negative_prompt):
        if not enabled:
            return p

        n_images = p.batch_size * p.n_iter
        p.all_prompts = self.lpp.choose_prompts(n_images)

        if auto_negative_prompt:
            for i, np in enumerate(p.all_negative_prompts):
                p.all_negative_prompts[i] = ", ".join(
                    [x for x in [p.negative_prompt, self.lpp.get_negative_prompt()] if x]
                )
