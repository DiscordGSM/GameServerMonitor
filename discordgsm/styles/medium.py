from typing import Dict

from discord import Embed
from discord.ui import TextInput

from discordgsm.styles.style import Style
from discordgsm.translator import t


class Medium(Style):
    """Medium style"""

    @property
    def display_name(self) -> str:
        return t('style.medium.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.medium.description', self.locale)

    @property
    def default_edit_fields(self) -> Dict[str, TextInput]:
        fields = super().default_edit_fields
        fields.update({
            'country': TextInput(
                label=t('embed.text_input.country.label', self.locale),
                placeholder=t('embed.text_input.country.placeholder', self.locale),
                default=self.server.style_data.get('country', '')
            )
        })

        return fields

    def embed(self) -> Embed:
        title, description, color = self.embed_data()
        embed = Embed(title=title, description=description, color=color)

        self.add_status_field(embed)
        self.add_address_field(embed)

        flag_emoji = ('country' in self.server.style_data) and (':flag_' + self.server.style_data['country'].lower() + f': {self.server.style_data["country"]}') or ':united_nations: Unknown'
        name = t('embed.field.country.name', self.locale)
        embed.add_field(name=name, value=flag_emoji, inline=True)

        self.add_game_field(embed)

        if self.server.result['map'] and self.server.result['map'].strip():
            name = t('embed.field.current_map.name', self.locale)
            embed.add_field(name=name, value=self.server.result['map'].strip(), inline=True)
            self.add_players_field(embed)
        else:
            self.add_players_field(embed)
            embed.add_field(name='*​*', value='*​*', inline=True)

        self.set_image_and_thumbnail(embed)
        self.set_footer(embed)

        return embed
