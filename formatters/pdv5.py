from lpp_utils import get_merged_config_entry
import os


class PromptFormatter():
    def __init__(self, work_dir="."):
        self.pretty_name = "Pony Diffusion V5"
        self.__work_dir = work_dir
        config = self.__load_config()
        self.__ratings = config["ratings"]
        self.__character_tags = config["character_tags"]
        self.__prioritized_tags = config["prioritized_tags"]
        self.__filtered_tags = config["filtered_tags"]

    def __load_config(self):
        p = os.path.join(self.__work_dir, "config", "pdv5")
        config = {}
        config["prioritized_tags"] = get_merged_config_entry(
            "prioritized_tags", p
        )
        config["character_tags"] = get_merged_config_entry("character_tags", p)
        config["filtered_tags"] = get_merged_config_entry("filtered_tags", p)
        config["ratings"] = get_merged_config_entry("ratings", p)
        return config

    def derpi_format(self, raw_image_tags):
        rating = None
        characters = []
        prioritized_tags = []
        prompt_tail = []
        for tag in raw_image_tags:
            if (any([tag.startswith(x) for x in self.__filtered_tags["starts_with"]])
                    or any([tag.endswith(x) for x in self.__filtered_tags["ends_with"]])
                    or tag in self.__filtered_tags["exact"]):
                continue
            if rating is None and tag in self.__ratings.keys():
                rating = self.__ratings[tag]
                continue
            if tag in self.__character_tags:
                characters.append(tag)
                continue
            if tag in self.__prioritized_tags:
                prioritized_tags.append(tag)
                continue
            prompt_tail.append(tag)
        return ([] if rating is None else [rating]) \
            + characters + prioritized_tags + prompt_tail
