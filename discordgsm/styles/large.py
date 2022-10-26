from discord import Embed
from discordgsm.styles.medium import Medium
from discordgsm.styles.style import Style
from discordgsm.translator import t


class Large(Medium, Style):
    """Large style"""

    @property
    def display_name(self) -> str:
        return t('style.large.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.large.description', self.locale)

    def embed(self) -> Embed:
        embed = super().embed()
        empty_value = '*​*'
        field_name = t(f"embed.field.{'members' if self.server.game_id == 'discord' else 'player_list'}.name", self.locale)
        players = [player for player in self.server.result['players'] if player['name'].strip()]
        bots = [bot for bot in self.server.result['bots'] if bot['name'].strip()]
        values = ['', '', '']

        for i, player in enumerate(sorted(players, key=lambda player: player['name'])):
            values[i % len(values)] += f"{player['name']}\n"

        for i, bot in enumerate(sorted(bots, key=lambda bot: bot['name'])):
            values[i % len(values)] += f"🤖{bot['name']}\n"

        for i, name in enumerate([field_name, empty_value, empty_value]):
            embed.add_field(name=name, value=values[i] if values[i] else empty_value)

        return embed
