from discord import Embed
from discordgsm.styles.medium import Medium
from discordgsm.styles.style import Style


class Large(Medium, Style):
    """Large style"""

    @property
    def display_name(self) -> str:
        return 'Large'

    @property
    def description(self) -> str:
        return 'A large-sized style that shows server info and player list.'

    def embed(self) -> Embed:
        embed = super().embed()
        empty_value = '*​*'
        field_names = ['Members' if self.server.game_id == 'discord' else 'Player List', empty_value, empty_value]
        players = [player for player in self.server.result['players'] if player['name'].strip()]
        values = ['', '', '']

        for i, player in enumerate(sorted(players, key=lambda player: player['name'])):
            values[i % len(values)] += f"{player['name']}\n"

        for i, name in enumerate(field_names):
            embed.add_field(name=name, value=values[i] if values[i] else empty_value)

        return embed
