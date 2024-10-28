from lpp.log import get_logger
from lpp.sources.common import TagSourceBase, Tags
from lpp.data import TagData, FilterData, Models, Ratings
from random import sample
import re

logger = get_logger()


class PromptsManager:
    def __init__(self, sources: dict[str:TagSourceBase]):
        self.__sources: dict[str:TagSourceBase] = sources
        self.tag_data: TagData = None

    def __replace_tokens(self, flat_groups: dict[str:str], template: str) -> str:
        result = template
        for token, prompt_fragment in flat_groups.items():
            result = result.replace(f"{{{token}}}", prompt_fragment)
        return result

    def __apply_template(self,
                         flat_groups: dict[str:str],
                         default_template: str,
                         template: str = None,
                         sep: str = ", ",
                         sanitize: bool = True) -> str:
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

        if sanitize:
            rules = {
                " +": " ",
                r"(, )\1+": r"\1",
                "^, +": "",
                ", +$": ""
            }
            for re_pattern, replacement in rules.items():
                prompt = re.sub(re_pattern, replacement, prompt)
        return prompt

    def choose_prompts(self,
                       model: str,
                       template: str = None,
                       n: int = 1,
                       allowed_ratings: list[str] = None,
                       filters: list[FilterData] = None
                       ) -> list[str]:
        if not self.tag_data:
            raise ValueError("No prompts are currently loaded.")

        raw_tags = self.tag_data.raw_tags
        source = self.__sources[self.tag_data.source]

        if allowed_ratings and len(allowed_ratings) < len(Ratings):
            raw_tags = [
                x for x in raw_tags if (source.get_lpp_rating(x) in allowed_ratings)
            ]
            if len(raw_tags) == 0:
                raise ValueError("Current collection doesn't seem to have prompts with selected rating(s).")

        # manually handle requests for more images than we have tags
        # because random.sample would raise a ValueError
        if n > len(raw_tags):
            factor = n // len(raw_tags) + 1  # +1 because // rounds down
            raw_tags = raw_tags * factor
        chosen_prompts = sample(raw_tags, k=n)

        format_func = source.formatters[model]\
            if model in source.supported_models\
            else source.default_formatter

        processed_prompts = []
        for raw_tags in chosen_prompts:
            formatted_tags = Tags(format_func(raw_tags))\
                .escape_parentheses()\
                .filter(*filters)\
                .as_flat_groups()
            processed_prompts.append(
                self.__apply_template(
                    formatted_tags, Models.get_default_template(model), template
                )
            )
        return processed_prompts

    @property
    def prompts_count(self) -> int:
        return len(self.tag_data.raw_tags) if self.tag_data else 0
