from typing import List

from discord import Embed

from discordgsm.gamedig import GamedigPlayer
from discordgsm.styles.medium import Medium
from discordgsm.translator import t


class Large(Medium):
    """Large style"""

    @property
    def standalone(self) -> str:
        return True

    @property
    def display_name(self) -> str:
        return t('style.large.display_name', self.locale)

    @property
    def description(self) -> str:
        return t('style.large.description', self.locale)

    def embed(self) -> Embed:
        embed = super().embed()
        field_name = t(
            f"embed.field.{'members' if self.server.game_id == 'discord' else 'player_list'}.name", self.locale)
        self.add_player_list_fields(
            embed, field_name, self.server.result['players'])

        return embed

    def add_player_list_fields(self, embed: Embed, field_name: str, players: List[GamedigPlayer]):
        if players is None:
            embed.add_field(name=field_name, value='The game does not support this feature.')
            return embed

        empty_value = '*​*'
        filtered_players = [
            player for player in players if player['name'].strip()]
        filtered_players = sorted(
            filtered_players, key=lambda player: player['name'])

        counts = [0, 0, 0]
        values = ['', '', '']
        player_count = 0

        for i, player in enumerate(filtered_players):
            name = player['name'][:23]

            if len(player['name']) > 23:
                name = name[:-3] + '...'

            # Replace Markdown
            # https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-
            name = name.replace('*', '\\*').replace('_', '\\_').replace('~', '\\~')
            name = name.replace('`', '\\`').replace('>', '\\>') + '\n'

            index = i % len(values)
            counts[index] += len(name)

            player_left = len(filtered_players) - player_count
            remaining_players_message = f'... {player_left} more player{"" if player_left <= 1 else "s"}'

            # Embed must be 1024 or fewer in length.
            if (counts[index] + len(remaining_players_message)) >= 1024:
                values[index] += remaining_players_message
                break

            values[index] += name
            player_count += 1

        for i, name in enumerate([field_name, empty_value, empty_value]):
            embed.add_field(
                name=name, value=values[i] if values[i] else empty_value)

        return embed
