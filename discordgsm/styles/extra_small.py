from typing import Dict, Optional, Union

from discord import Color, Embed, Emoji, PartialEmoji, TextStyle
from discord.ui import TextInput
from discordgsm.service import gamedig
from discordgsm.styles.style import Style


class ExtraSmall(Style):
    """Extra Small style"""

    @property
    def display_name(self) -> str:
        return 'Extra Small'

    @property
    def description(self) -> str:
        return 'A extra small-sized style that shows less information.'

    @property
    def emoji(self) -> Optional[Union[str, Emoji, PartialEmoji]]:
        return '🔘'

    @property
    def default_edit_fields(self) -> Dict[str, TextInput]:
        return {
            'description': TextInput(label='Description', default=self.server.style_data.get('description', ''), required=False, style=TextStyle.long, placeholder='The description of the embed.'),
            'fullname': TextInput(label='Full Name', default=self.server.style_data.get('fullname', ''), placeholder='The display name of the game.'),
            'image_url': TextInput(label='Image URL', default=self.server.style_data.get('image_url', ''), required=False, placeholder='The source URL for the image. Only HTTP(S) is supported.'),
            'thumbnail_url': TextInput(label='Thumbnail URL', default=self.server.style_data.get('thumbnail_url', ''), required=False, placeholder='The source URL for the thumbnail. Only HTTP(S) is supported.'),
        }

    def default_style_data(self):
        game = gamedig.find(self.server.game_id)
        style_data = {'fullname': game['fullname']}

        if self.server.game_id == 'discord' and self.server.result['connect']:
            style_data['description'] = f'Instant Invite: {self.server.result["connect"]}'
        elif gamedig.default_port(self.server.game_id) == 27015 and gamedig.game_port(self.server.result) == int(self.server.query_port):
            style_data['description'] = f'Connect: steam://connect/{self.server.address}:{self.server.query_port}'

        return style_data

    def embed(self) -> Embed:
        players = self.server.result.get('raw', {}).get('numplayers', len(self.server.result['players']))
        bots = len(self.server.result['bots'])

        if self.server.status:
            color = Color.from_rgb(88, 101, 242)
        else:
            color = Color.from_rgb(32, 34, 37)  # dark

        title = (self.server.result['password'] and ':lock: ' or '') + self.server.result['name']
        description = self.server.style_data.get('description', '').strip()

        embed = Embed(description=None if not description else description, color=color)
        embed.set_author(name=title)
        embed.add_field(name='Game', value=self.server.style_data.get('fullname', self.server.game_id), inline=True)

        game_port = gamedig.game_port(self.server.result)

        if self.server.game_id == 'discord':
            embed.add_field(name='Guild ID', value=f'`{self.server.address}`', inline=True)
        elif game_port is None or game_port == int(self.server.query_port):
            embed.add_field(name='Address:Port', value=f'`{self.server.address}:{self.server.query_port}`', inline=True)
        else:
            embed.add_field(name='Address:Port (Query)', value=f'`{self.server.address}:{game_port} ({self.server.query_port})`', inline=True)

        if self.server.status:
            players_string = str(players)  # example: 20

            if bots > 0:
                players_string += f' ({bots})'  # example: 20 (2)
        else:
            players_string = '0'  # example: 0

        maxplayers = int(self.server.result['maxplayers'])

        if maxplayers >= 0:
            percentage = 0 if maxplayers <= 0 else int(players / int(self.server.result['maxplayers']) * 100)
            players_string = f'{players_string}/{maxplayers} ({percentage}%)'

        embed.add_field(name='Presence' if self.server.game_id == 'discord' else 'Players', value=players_string, inline=True)

        embed.set_image(url=self.server.style_data.get('image_url'))
        embed.set_thumbnail(url=self.server.style_data.get('thumbnail_url'))

        return embed
