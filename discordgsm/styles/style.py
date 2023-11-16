import socket
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Dict, Optional, Union

import aiohttp
from discord import Color, Embed, Emoji, Locale, PartialEmoji, TextStyle
from discord.ui import TextInput

from discordgsm.server import Server
from discordgsm.service import gamedig, tz
from discordgsm.translator import t
from discordgsm.version import __version__


class Style(ABC):
    """DiscordGSM Message Style Abstract Class"""

    def __init__(self, server: Server):
        super().__init__()
        self.server = server

    @property
    def id(self) -> str:
        return self.__class__.__name__

    @property
    def locale(self) -> str:
        return str(self.server.style_data.get('locale', 'en-US'))

    @property
    def standalone(self) -> str:
        """Whether the embed should be within a single discord message"""
        return False

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError()

    @property
    def emoji(self) -> Optional[Union[str, Emoji, PartialEmoji]]:
        return '🔘'

    @property
    def default_edit_fields(self) -> Dict[str, TextInput]:
        return {
            'description': TextInput(
                label=t('embed.text_input.description.label', self.locale),
                style=TextStyle.long,
                placeholder=t('embed.text_input.description.placeholder', self.locale),
                default=self.server.style_data.get('description', ''),
                required=False,
                max_length=1024
            ),
            'fullname': TextInput(
                label=t('embed.text_input.fullname.label', self.locale),
                placeholder=t('embed.text_input.fullname.placeholder', self.locale),
                default=self.server.style_data.get('fullname', ''),
            ),
            'image_url': TextInput(
                label=t('embed.text_input.image_url.label', self.locale),
                placeholder=t('embed.text_input.image_url.placeholder', self.locale),
                default=self.server.style_data.get('image_url', ''),
                required=False
            ),
            'thumbnail_url': TextInput(
                label=t('embed.text_input.thumbnail_url.label', self.locale),
                placeholder=t('embed.text_input.thumbnail_url.placeholder', self.locale),
                default=self.server.style_data.get('thumbnail_url', ''),
                required=False
            )
        }

    async def default_style_data(self, locale: Optional[Locale]):
        game = gamedig.find(self.server.game_id)
        style_data = {'fullname': game['fullname'], 'locale': locale.value if locale else 'en-US'}

        if self.server.game_id == 'gportal' and (key := self.server.result["raw"].get('key', None)):
            style_data['fullname'] += f' ({key})'

        if self.server.game_id == 'discord' and self.server.result['connect']:
            style_data['description'] = t('embed.description.instant_invite', self.locale).format(url=self.server.result['connect'])
        elif gamedig.default_port(self.server.game_id) == 27015 and gamedig.game_port(self.server.result) == int(self.server.query_port):
            style_data['description'] = t('embed.description.connect', self.locale).format(url=f'steam://connect/{self.server.address}:{self.server.query_port}')

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://ipinfo.io/{socket.gethostbyname(self.server.address)}/country') as response:
                    data = await response.text()

            if '{' not in data:
                style_data['country'] = data.replace('\n', '').strip()
        except Exception:
            pass

        return style_data

    @abstractmethod
    def embed(self) -> Embed:
        raise NotImplementedError()

    def embed_data(self):
        title = (self.server.result['password'] and '🔒 ' or '') + self.server.result['name']

        if len(title) > 256:
            title = title[:256][:-3] + '...'

        description = str(self.server.style_data.get('description', '')).strip()
        description = description if description else None
        color = Color.from_rgb(88, 101, 242) if self.server.status else Color.from_rgb(32, 34, 37)

        return title, description, color

    def add_status_field(self, embed: Embed):
        name = t('embed.field.status.name', self.locale)
        value = t(f'embed.field.status.value.{"online" if self.server.status else "offline"}', self.locale)
        embed.add_field(name=name, value=value, inline=True)

    def add_address_field(self, embed: Embed):
        game_port = gamedig.game_port(self.server.result)

        if self.server.game_id == 'discord':
            name = t('modal.text_input.guild_id.label', self.locale)
            embed.add_field(name=name, value=f'`{self.server.address}`', inline=True)
        elif game_port is None or game_port == int(self.server.query_port):
            name = t('embed.field.address:port.name', self.locale)
            embed.add_field(name=name, value=f'`{self.server.address}:{self.server.query_port}`', inline=True)
        else:
            name = t('embed.field.address:port:query.name', self.locale)
            embed.add_field(name=name, value=f'`{self.server.address}:{game_port} ({self.server.query_port})`', inline=True)

    def add_game_field(self, embed: Embed):
        name = t('embed.field.game.name', self.locale)
        embed.add_field(name=name, value=self.server.style_data.get('fullname', self.server.game_id), inline=True)

    def add_players_field(self, embed: Embed):
        name = t(f"embed.field.{'presence' if self.server.game_id == 'discord' else 'players'}.name", self.locale)
        embed.add_field(name=name, value=self.get_players_display_string(self.server), inline=True)

    def set_footer(self, embed: Embed):
        advertisement = '📺 Game Server Monitor'

        # Easter Egg
        today = str(date.today())  # 2020-12-23
        if '-12-25' in today:
            advertisement = '🎅 Merry Christmas!'
        elif '-01-01' in today:
            advertisement = '🎉 Happy New Year!'

        time_format = '%Y-%m-%d %I:%M:%S%p' if int(self.server.style_data.get('clock_format', '12')) == 12 else '%Y-%m-%d %H:%M:%S'
        last_update = datetime.now(tz=tz(self.server.style_data.get('timezone', 'Etc/UTC'))).strftime(time_format)
        last_update = t('embed.field.footer.last_update', self.locale).format(last_update=last_update)
        icon_url = 'https://avatars.githubusercontent.com/u/61296017'
        embed.set_footer(text=f'DiscordGSM {__version__} | {advertisement} | {last_update}', icon_url=icon_url)

    def set_image_and_thumbnail(self, embed: Embed):
        image_url = str(self.server.style_data.get('image_url', ''))
        thumbnail_url = str(self.server.style_data.get('thumbnail_url', ''))

        if image_url.startswith('http://') or image_url.startswith('https://'):
            embed.set_image(url=image_url)

        if thumbnail_url.startswith('http://') or thumbnail_url.startswith('https://'):
            embed.set_thumbnail(url=thumbnail_url)

    @staticmethod
    def get_players_display_string(server: Server):
        players, bots, maxplayers = Style.get_player_data(server)
        return Style.to_players_string(players, bots, maxplayers)

    @staticmethod
    def get_player_data(server: Server):
        if 'numplayers' in server.result:
            players = int(server.result.get('numplayers', 0))
        else:
            players = int(server.result.get('raw', {}).get('numplayers', len(server.result['players'])))

        if 'numbots' in server.result:
            bots = int(server.result.get('numbots', 0))
        else:
            bots = int(server.result.get('raw', {}).get('numbots', len(server.result['bots'])))

        maxplayers = int(server.result.get('maxplayers', 0))

        return players, bots, maxplayers

    @staticmethod
    def to_players_string(players: int, bots: int, maxplayers: int):
        players_string = str(players)  # example: 20

        if bots > 0:
            players_string += f' ({bots})'  # example: 20 (2)

        if maxplayers > 0:
            percentage = 0 if maxplayers <= 0 else int(players / maxplayers * 100)
            players_string = f'{players_string}/{maxplayers} ({percentage}%)'

        return players_string
