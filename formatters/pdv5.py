from lpp_utils import get_merged_config_entry
import os


class PromptFormatter():
    def __init__(self, work_dir="."):
        self.pretty_name = "Pony Diffusion V5"
        self.__work_dir = work_dir
        config = get_merged_config_entry(
            "formatters",
            os.path.join(self.__work_dir, "config")
        )
        self.__derpi_pdv5_ratings = config["derpi"]["ratings"]["pdv5"]
        self.__derpi_character_tags = config["derpi"]["character_tags"]
        self.__derpi_prioritized_tags = config["derpi"]["prioritized_tags"]
        self.__derpi_filtered_tags = config["derpi"]["filtered_tags"]

    def derpi_format(self, raw_image_tags):
        rating = None
        characters = []
        prioritized_tags = []
        prompt_tail = []
        for tag in raw_image_tags:
            if (any([tag.startswith(x) for x in self.__derpi_filtered_tags["starts_with"]])
                    or any([tag.endswith(x) for x in self.__derpi_filtered_tags["ends_with"]])
                    or tag.startswith("artist:")
                    or tag in self.__derpi_filtered_tags["exact"]):
                continue
            if rating is None and tag in self.__derpi_pdv5_ratings.keys():
                rating = self.__derpi_pdv5_ratings[tag]
                continue
            if tag in self.__derpi_character_tags:
                characters.append(tag)
                continue
            if tag in self.__derpi_prioritized_tags:
                prioritized_tags.append(tag)
                continue
            prompt_tail.append(tag)
        return ([] if rating is None else [rating]) \
            + characters + prioritized_tags + prompt_tail

    def e621_format(self, raw_image_tags):
        t = raw_image_tags
        return t["character"] + t["species"] + t["general"] + t["meta"]
