from lpp.sources.common import TagSourceBase, Tags
from lpp.sources.utils import get_sources
from lpp.data import TagData, Models, Ratings
from random import sample
import re


class Prompts:
    def __init__(self, chosen_prompts: list[object], source: TagSourceBase):
        self.__prompts = chosen_prompts
        self.__source = source
        self.__processed_tags = []
        self.__processed_prompts = []

    def apply_formatting(self, model: str):
        source = self.__source
        format_func = source.formatters[model]\
            if model in source.supported_models\
            else source.default_formatter
        for raw_tags in self.__prompts:
            self.__processed_tags.append(
                Tags(format_func(raw_tags))
            )
        return self

    def extra_tag_formatting(self, format_func: callable):
        self.__processed_tags = [format_func(x) for x in self.__processed_tags]
        return self

    def __replace_tokens(self,
                         flat_groups: dict[str:str],
                         template: str) -> str:
        result = template
        for token, prompt_fragment in flat_groups.items():
            result = result.replace(f"{{{token}}}", prompt_fragment)
        return result

    def apply_template(self, model: str, template: str = None, sep: str = ", "):
        default_template = Models.get_default_template(model)
        for flat_groups in [x.as_flat_groups() for x in self.__processed_tags]:
            tokens = set(flat_groups.keys())
            prompt = ""
            if template:
                if "{prompt}" in template:
                    for token in tokens:
                        template = template.replace(f"{{{token}}}", "")
                    template = template.replace("{prompt}", default_template)
                    prompt = self.__replace_tokens(flat_groups, template)
                elif any(f"{{{x}}}" in template for x in tokens):
                    for token in tokens:
                        prompt = self.__replace_tokens(flat_groups, template)
                else:
                    prompt = self.__replace_tokens(
                        flat_groups, sep.join([default_template, template])
                    )
            else:
                prompt = self.__replace_tokens(flat_groups, default_template)
            self.__processed_prompts.append(prompt)
        return self

    def sanitize(self, rules: dict[str:str] = None):
        if not rules:
            rules = {
                " +": " ",
                r"(, )\1+": r"\1",
                "^, +": "",
                ", +$": ""
            }
        sanitized_prompts = []
        for prompt in self.__processed_prompts:
            for re_pattern, replacement in rules.items():
                prompt = re.sub(re_pattern, replacement, prompt)
            sanitized_prompts.append(prompt)
        self.__processed_prompts = sanitized_prompts
        return self

    def as_list(self) -> list[str]:
        return self.__processed_prompts

    def first(self) -> str:
        return self.__processed_prompts[0]


class PromptPool:
    def __init__(self, tag_data: TagData, work_dir: str = "."):
        self.__source = get_sources(work_dir)[tag_data.source]
        self.tag_data = tag_data

    def choose_prompts(self,
                       n: int = 1,
                       allowed_ratings: list[str] = None
                       ) -> Prompts:
        if not self.tag_data:
            raise ValueError("No prompts are currently loaded.")

        raw_tags = self.tag_data.raw_tags
        source = self.__source

        if allowed_ratings and len(allowed_ratings) < len(Ratings):
            raw_tags = [
                x for x in raw_tags if (source.get_lpp_rating(x) in allowed_ratings)
            ]
            if len(raw_tags) == 0:
                raise ValueError(
                    "Current collection doesn't seem to have prompts with selected rating(s)."
                )

        # manually handle requests for more images than we have tags
        # because random.sample would raise a ValueError
        if n > len(raw_tags):
            factor = n // len(raw_tags) + 1  # +1 because // rounds down
            raw_tags = raw_tags * factor
        return Prompts(sample(raw_tags, k=n), self.__source)

    @property
    def prompts_count(self) -> int:
        return len(self.tag_data.raw_tags)
