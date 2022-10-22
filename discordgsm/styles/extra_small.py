from discord import Embed
from discordgsm.styles.style import Style
from discordgsm.translator import t


class ExtraSmall(Style):
    """Extra Small style"""

    @property
    def display_name(self) -> str:
        return t('style.extra_small.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.extra_small.description', self.locale)

    def embed(self) -> Embed:
        title, description, color = self.embed_data()
        embed = Embed(description=description if description else None, color=color)
        embed.set_author(name=title)

        self.add_game_field(embed)
        self.add_address_field(embed)
        self.add_players_field(embed)

        embed.set_image(url=self.server.style_data.get('image_url'))
        embed.set_thumbnail(url=self.server.style_data.get('thumbnail_url'))

        return embed
