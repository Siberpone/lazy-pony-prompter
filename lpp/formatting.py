from dataclasses import asdict
from lpp.data import TagGroups, FilterData


class Tags:
    def __init__(self, tag_groups: TagGroups):
        self.__tag_groups: dict[str:list[str]] = asdict(tag_groups)

    def select(self, *groups: str):
        self.__tag_groups = {
            k: v if k in groups else [] for k, v in self.__tag_groups.items()
        }
        return self

    def modify(self, modifier: callable, *groups: str):
        if not groups:
            groups = set(self.__tag_groups.keys())
        for group in groups:
            self.__tag_groups[group] = [
                modifier(tag) for tag in self.__tag_groups[group]
            ]
        return self

    def replace_underscores(self, replace: bool = True, exclude: list[str] = []):
        if not replace:
            return self
        self.__tag_groups = {
            k: [
                x.replace("_", " ") if k not in exclude else x for x in v
            ] for k, v in self.__tag_groups.items()
        }
        return self

    def escape_parentheses(self, escape: bool = True):
        if not escape:
            return self
        self.__tag_groups = {
            k: [
                x.replace("(", "\\(").replace(")", "\\)") for x in v
            ] for k, v in self.__tag_groups.items()
        }
        return self

    def filter(self, *filters: FilterData):
        if not filters:
            return self

        filtered_tags = {}
        joint_filter = FilterData.merge(*filters)
        for group, tags in self.__tag_groups.items():
            filtered_tags[group] = []
            for tag in tags:
                if joint_filter.match_subst(tag):
                    filtered_tags[group].append(joint_filter.substitutions[tag])
                    continue
                if not joint_filter.match(tag):
                    filtered_tags[group].append(tag)
        self.__tag_groups = filtered_tags
        return self

    def as_tag_groups(self):
        return TagGroups(**self.__tag_groups)

    def as_flat_groups(self, sep: str = ", "):
        return {k: sep.join(v) for k, v in self.__tag_groups.items()}
