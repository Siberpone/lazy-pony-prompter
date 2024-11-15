from lpp.log import DefaultLppMessageService
from lpp.ui.a1111.controller import A1111_Controller
from lpp.data import FilterData
from modules import shared
from modules.ui_components import FormRow, FormColumn, ToolButton
import gradio as gr


def set_no_config(*args: object) -> None:
    for control in args:
        setattr(control, "do_not_save_to_config", True)


def get_opt(option, default):
    return getattr(shared.opts, option, default)


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

    def __init__(self, lpp: A1111_Controller):
        self.__lpp = lpp
        self.current_text = ""

    def ui(self):
        with FormColumn(variant="panel", scale=1, min_width=300):
            with FormRow():
                self.filter_name = gr.Dropdown(
                    label="Choose a filter to edit:",
                    choices=self.__lpp.filters
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
            filter_text = str(self.__lpp.try_load_filter(name))
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
            self.__lpp.try_save_filter(name, FilterData.from_string(patterns))
            return [gr.update(label="Filter Patterns")]\
                + [gr.update(choices=self.__lpp.filters)]\
                * len(FilterEditor.external_inputs)

        self.save_btn.click(
            save_btn_click,
            [self.filter_name, self.patterns_textarea],
            [self.patterns_textarea, *FilterEditor.external_inputs],
            show_progress="hidden"
        )

        self.refresh_btn.click(
            lambda: gr.update(choices=self.__lpp.filters),
            [],
            [self.filter_name],
            show_progress="hidden"
        )
