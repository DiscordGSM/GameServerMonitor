from typing import List, Optional, Type

from .extra_large import ExtraLarge
from .extra_small import ExtraSmall
from .large import Large
from .medium import Medium
from .small import Small
from .style import Style

if __name__ == '__main__':
    from server import Server
else:
    from discordgsm.server import Server

styles: List[Type[Style]] = [ExtraSmall, Small, Medium, Large, ExtraLarge]
_styles = {style.__name__: style for style in styles}


class Styles:
    @staticmethod
    def contains(style_id: str):
        return style_id in _styles

    @staticmethod
    def types() -> List[Type[Style]]:
        return styles

    @staticmethod
    def get(server: Server, style_id: Optional[str] = None) -> Style:
        return _styles.get(style_id if style_id else server.style_id, _styles['Medium'])(server)
