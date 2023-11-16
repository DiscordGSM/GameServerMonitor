from discord import Embed

from discordgsm.styles.large import Large
from discordgsm.translator import t


class ExtraLarge(Large):
    """Extra Large style"""

    @property
    def standalone(self) -> str:
        return True

    @property
    def display_name(self) -> str:
        return t('style.extra_large.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.extra_large.description', self.locale)

    def embed(self) -> Embed:
        embed = super().embed()
        field_name = t('embed.field.bot_list.name', self.locale)
        self.add_player_list_fields(embed, field_name, self.server.result['bots'])

        return embed
