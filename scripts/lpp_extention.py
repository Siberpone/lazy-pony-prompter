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

        def set_no_config(*args):
            for control in args:
                setattr(control, "do_not_save_to_config", True)

        with gr.Accordion("Lazy Pony Prompter", open=False):
            enabled = gr.Checkbox(label="Enabled", value=False)
            auto_negative_prompt = gr.Checkbox(
                label="Include negative prompt",
                value=True
            )
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
                        choices=self.lpp.filters.keys()
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
            status_bar = gr.Textbox(
                value=f"{self.lpp.get_loaded_prompts_count()} prompts currently loaded.",
                show_label=False,
                interactive=False,
                container=False
            )

            set_no_config(enabled, auto_negative_prompt, query_textbox,
                          prompts_count, filter_type, sort_type,
                          fetch_tags_btn, status_bar)

            def fetch_prompts(*args, **kwargs):
                try:
                    self.lpp.fetch_prompts(*args, **kwargs)
                    return f"Fetched {self.lpp.get_loaded_prompts_count()} prompts from Derpibooru."
                except Exception as e:
                    return f"Filed to fetch prompts: {e=}, {type(e)=}"

            fetch_tags_btn.click(
                lambda q, n, f, s: fetch_prompts(q, n, f, s),
                inputs=[query_textbox, prompts_count, filter_type, sort_type],
                outputs=[status_bar],
                show_progress="full"
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
