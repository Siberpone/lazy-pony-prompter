from lpp.ui.a1111.controller import A1111_Controller
from lpp.ui.a1111.utils import set_no_config, get_opt, A1111LppMessageService, ConfirmationDialog, FilterEditor
from lpp.data import Models, FilterData, Ratings
from lpp.prompts import Prompts
from dataclasses import dataclass
from modules import scripts
from modules import shared
from modules import script_callbacks
from modules.ui_components import InputAccordion, FormRow, FormColumn, FormGroup, ToolButton
import gradio as gr
import logging

base_dir = scripts.basedir()


saved_prompt_collections = []


lpp: A1111_Controller = A1111_Controller(
    base_dir,
    get_opt("lpp_derpibooru_api_key", None),
    get_opt("lpp_logging_level", None),
    A1111LppMessageService()
)


def refresh_saved_collections():
    global saved_prompt_collections
    saved_prompt_collections = ["None"] + lpp.prompt_collections


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
                lambda: {"choices": ["None"] + lpp.prompt_collections},
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


@dataclass
class QueryPanel:
    panel: gr.Group
    buttons: dict[str:gr.Button]
    params: list[object]


def get_query_panels(active_panel_name: str, is_img2img: bool):
    panels = {}
    for name, source in lpp.sources.items():
        controls = []
        buttons = {}
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
                controls.append(query)
            with FormRow():
                if not is_img2img:
                    with FormColumn():
                        prompts_count = gr.Slider(
                            label="Number of Prompts to Load",
                            minimum=5,
                            maximum=1500,
                            step=5,
                            value=100
                        )
                    controls.append(prompts_count)
                with FormColumn():
                    with FormRow():
                        for p, get_values_func in source.extra_query_params.items():
                            control = gr.Dropdown(
                                label=get_values_func.display_name,
                                choices=get_values_func(),
                                value=get_values_func()[0]
                            )
                            controls.append(control)
            with FormRow():
                send_btn = gr.Button(value="Send")
                buttons["send"] = send_btn
            set_no_config(*controls)
            panels[name] = QueryPanel(panel, buttons, controls)
    return panels


class LPP_Txt2Img:
    def __init__(self):
        self.query_panels = {}
        self.prompt_info_visible = False

        startup_collection = get_opt("lpp_default_collection", "None")
        if startup_collection != "None":
            lpp.try_load_prompts(startup_collection)

    def ui(self):
        with InputAccordion(
                value=False,
                label="💤 Lazy Pony Prompter",) as lpp_enable:
            with lpp_enable.extra():
                status_bar = gr.HTML(lpp.status, elem_id="lpp-status-bar")

            # Prompts Manager #################################################
            with gr.Tab("Prompts Manager"):
                with FormRow():
                    # Prompt Collections Management Panel ---------------------
                    with FormColumn():
                        with FormRow():
                            prompts_manager_input = gr.Dropdown(
                                label="Prompts Collection Name",
                                choices=lpp.prompt_collections,
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
                                    choices=lpp.prompt_collections,
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
                                self.query_panels = get_query_panels(
                                    source.value, False
                                )

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
                                choices=[x.value for x in Ratings],
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
                            import_export_panel = gr.File(
                                label="Prompts & filters import/export",
                                file_count="single",
                                file_types=[".json"],
                                interactive=True,
                            )

                        with FormRow():
                            export_btn = gr.Button(
                                value="Export Prompts and Filters"
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
                        filter_editors.append(FilterEditor(lpp))
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
                panel.buttons["send"].click(
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
                if name in lpp.prompt_collections:
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
                            choices=lpp.prompt_collections
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

            # Import Export Panel ---------------------------------------------
            export_btn.click(
                lpp.try_export_json,
                [],
                [import_export_panel]
            )

            def import_export_upload(temp_file_obj):
                if lpp.try_import_json(temp_file_obj):
                    return (
                        gr.update(choices=lpp.prompt_collections),
                        gr.update(choices=lpp.filters),
                        gr.update(choices=lpp.filters)
                    )
                else:
                    return (gr.update() * 3)

            import_export_panel.upload(
                import_export_upload,
                [import_export_panel],
                [prompts_manager_input, filters, fe_filter_name]
            )
        return [lpp_enable, prompts_format, rating_filter, quick_filter, filters]


class LPP_Img2Img:
    def __init__(self, prompt, image, width, height):
        self.__prompt_tbox = prompt
        self.__image_area = image
        self.__width_slider = width
        self.__height_slider = height
        self.__image_data = None
        self.__prev_query = None
        self.__prev_source = None

    def ui(self):
        with gr.Accordion(
            label="💤 Lazy Pony Prompter",
            open=False
        ):
            with FormRow():
                source = gr.Radio(
                    label="Tags Source",
                    choices=lpp.source_names,
                    value=lambda: lpp.source_names[0],
                    elem_id="lpp-chbox-group",
                    scale=5
                )
                models = lpp.sources[lpp.source_names[0]].supported_models
                prompts_format = gr.Dropdown(
                    label="Prompts Format",
                    choices=models,
                    value=lambda: models[0],
                    scale=3
                )
            with FormRow(variant="panel"):
                self.query_panels = get_query_panels(
                    source.value, True
                )
            with FormRow():
                prev_btn = ToolButton("🡄 ")
                page = gr.Number(
                    label="Page",
                    value=1,
                    precision=0,
                    show_label=True
                )
                next_btn = ToolButton("🡆")
            with FormRow():
                gallery = gr.Gallery(
                    columns=4, allow_preview=False, interactive=False,
                    label="Click image to send it to i2i"
                )

            def send_request_click(source, *query_params):
                self.__image_data, thumbs = lpp.try_get_thumbs(
                    source, 1, *query_params
                )
                if not self.__image_data:
                    return [gr.update()] * 2

                self.__prev_query = query_params
                self.__prev_source = source
                return (
                    gr.update(value=1),
                    gr.update(value=thumbs)
                )

            for panel in self.query_panels.values():
                panel.buttons["send"].click(
                    send_request_click,
                    [source, *panel.params],
                    [page, gallery]
                )

            def change_page_click(page_delta, current_page):
                if not self.__prev_query:
                    return [gr.update()] * 2

                page_to_load = current_page + page_delta
                self.__image_data, thumbs = lpp.try_get_thumbs(
                    self.__prev_source, page_to_load, *self.__prev_query
                )
                if not self.__image_data:
                    return [gr.update()] * 2

                return (
                    gr.update(value=page_to_load),
                    gr.update(value=thumbs)
                )

            prev_btn.click(
                lambda p: change_page_click(-1, p),
                [page],
                [page, gallery]
            )
            next_btn.click(
                lambda p: change_page_click(1, p),
                [page],
                [page, gallery]
            )
            page.submit(
                lambda p: change_page_click(0, p),
                [page],
                [page, gallery]
            )

            def gallery_select(evt: gr.SelectData, prompt_format):
                if not evt.selected:
                    return [gr.update()] * 2

                img_data = self.__image_data[evt.index]
                img = lpp.try_get_image(img_data)
                if not img:
                    return [gr.update()] * 2

                prompt = Prompts([img_data.raw_tags], lpp.sources[img_data.source])\
                    .apply_formatting(prompt_format)\
                    .extra_tag_formatting(lambda x: x.escape_parentheses())\
                    .apply_template(prompt_format)\
                    .sanitize()\
                    .first()
                return (
                    gr.update(value=img),
                    gr.update(value=prompt)
                )

            gallery.select(
                gallery_select,
                [prompts_format],
                [self.__image_area, self.__prompt_tbox]
            )

            source.change(
                lambda s, f: [
                    gr.update(
                        visible=(s == x)
                    ) for x in self.query_panels.keys()
                ] + [
                        gr.update(
                            choices=lpp.sources[s].supported_models,
                            value=f
                            if f in lpp.sources[s].supported_models
                            else lpp.sources[s].supported_models[0]
                        )
                    ],
                [source, prompts_format],
                [x.panel for x in self.query_panels.values()] + [prompts_format],
                show_progress="hidden"
            )
            # A1111 will cache ui control values in ui_config.json and "freeze"
            # them without this attribute.
            set_no_config(source, prompts_format)

            # We don't do any processing in i2i tab, so we just return dummy
            # controls to instantly trigger guard clause in process(...)
            dummy_controls = [gr.Checkbox(value=False, visible=False)] + \
                [gr.HTML(visible=False)] * 4
        return dummy_controls


class Scripts(scripts.Script):
    i2i_components = {}

    def title(self):
        return "Lazy Pony Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        if is_img2img:
            return LPP_Img2Img(**self.i2i_components).ui()
        return LPP_Txt2Img().ui()

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
                "821aa5537f": Models.PDV56.value,   # AutismMix_pony
                "ac006fdd7e": Models.PDV56.value,   # AutismMix_confetti
                "ff827fc345": Models.NOOBAI.value   # NoobAI XL v1.0
            }
            if p.sd_model_hash not in model_hashes:
                prompts_format = Models.PDV56.value
            else:
                prompts_format = model_hashes[p.sd_model_hash]

        n_images = p.batch_size * p.n_iter
        filters = lpp.get_filters(filter_names)
        if quick_filter:
            filters += [FilterData.from_string(quick_filter, ",")]

        chosen_prompts = lpp.try_choose_prompts(n_images, allowed_ratings)
        p.all_prompts = chosen_prompts\
            .apply_formatting(prompts_format)\
            .extra_tag_formatting(
                lambda x: x.filter(*filters).escape_parentheses()
            )\
            .apply_template(prompts_format, p.prompt)\
            .sanitize()\
            .as_list()

        p.all_prompts = [
            shared.prompt_styles.apply_styles_to_prompt(x, p.styles)
            for x in p.all_prompts
        ]

        if p.enable_hr:
            p.all_hr_prompts = p.all_prompts
            p.all_hr_negative_prompts = [p.negative_prompt] * n_images

    def after_component(self, component, *args, **kwargs):
        if kwargs.get("elem_id") == "img2img_prompt":
            self.i2i_components["prompt"] = component
        if kwargs.get("elem_id") == "img2img_image":
            self.i2i_components["image"] = component
        if kwargs.get("elem_id") == "img2img_width":
            self.i2i_components["width"] = component
        if kwargs.get("elem_id") == "img2img_height":
            self.i2i_components["height"] = component
