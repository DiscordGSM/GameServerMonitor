from datetime import date, datetime
from typing import Dict, Optional, Union

from discord import Color, Embed, Emoji, PartialEmoji, TextStyle
from discord.ui import TextInput
from discordgsm.service import ZoneInfo, gamedig
from discordgsm.styles.style import Style
from discordgsm.version import __version__


class Small(Style):
    """Small style"""

    @property
    def display_name(self) -> str:
        return 'Small'

    @property
    def description(self) -> str:
        return 'A small-sized style that displays less server information.'

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

    async def default_style_data(self):
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

        embed = Embed(title=title, description=None if not description else description, color=color)
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

        advertisement = '📺 Game Server Monitor'

        # Easter Egg
        today = str(date.today())  # 2020-12-23
        if '-12-25' in today:
            advertisement = '🎅 Merry Christmas!'
        elif '-01-01' in today:
            advertisement = '🎉 Happy New Year!'

        time_format = '%Y-%m-%d %I:%M:%S%p' if int(self.server.style_data.get('clock_format', '12')) == 12 else '%Y-%m-%d %H:%M:%S'
        last_update = datetime.now(tz=ZoneInfo(self.server.style_data.get('timezone', 'Etc/UTC'))).strftime(time_format)
        icon_url = 'https://avatars.githubusercontent.com/u/61296017'
        embed.set_footer(text=f'DiscordGSM {__version__} | {advertisement} | Last update: {last_update}', icon_url=icon_url)

        return embed
