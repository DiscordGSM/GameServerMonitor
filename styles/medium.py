import socket
from datetime import date, datetime
from typing import Optional, Union

import requests
from discord import Color, Embed, Emoji, PartialEmoji, TextStyle
from discord.ui import TextInput
from server import Server
from service import gamedig
from version import __version__

from styles.style import Style


class Medium(Style):
    """Medium style"""
    
    def __init__(self, server: Server):
        super().__init__(server)
    
    @property
    def display_name(self) -> str:
        return 'Medium'
    
    @property
    def description(self) -> str:
        return 'A medium-sized style that shows server information.'
    
    @property
    def emoji(self) -> Optional[Union[str, Emoji, PartialEmoji]]:
        return '🔘'
    
    @property
    def default_edit_fields(self) -> dict[str, TextInput]:
        return {
            'description': TextInput(label='Description', default=self.server.style_data.get('description', ''), required=False, style=TextStyle.long),
            'country': TextInput(label='Country', default=self.server.style_data.get('country', '')),
            'fullname': TextInput(label='Full Name', default=self.server.style_data.get('fullname', '')),
        }
        
    def default_style_data(self):
        game = gamedig.find(self.server.game_id)
        style_data = {'fullname': game['fullname']}
        
        try:
            if gamedig.default_port(self.server.game_id) == 27015:
                style_data['description'] = f'Connect: steam://connect/{self.server.address}:{self.server.query_port}'
        except:
            pass
        
        try:
            response = requests.get(f"https://ipinfo.io/{socket.gethostbyname(self.server.address)}/country")
            
            if '{' not in response.text:
                style_data['country'] = response.text.replace('\n', '').strip()
        except:
            pass
        
        return style_data
    
    def embed(self) -> Embed:
        emoji = self.server.status and ':green_circle:' or ':red_circle:'
        players = len(self.server.result['players'])
        
        if self.server.game_id == 'mordhau':
            for tag in self.server.result['raw'].get('tags', []):
                if tag[:2] == 'B:':
                    players = int(tag[2:])
                    break
        
        bots = len(self.server.result['bots'])
        
        if self.server.status:
            color = Color.from_rgb(88, 101, 242)
        else:
            color = Color.from_rgb(32, 34, 37) # dark

        title = (self.server.result['password'] and ':lock: ' or '') + f'{self.server.result["name"]}'
        description = self.server.style_data.get('description', '').strip()
        
        embed = Embed(title=title, description=None if not description else description, color=color)
        embed.add_field(name='Status', value=f"{emoji} **{self.server.status and 'Online' or 'Offline'}**", inline=True)
        embed.add_field(name='Address:Port', value=f'`{self.server.address}:{self.server.query_port}`', inline=True)

        flag_emoji = ('country' in self.server.style_data) and (':flag_' + self.server.style_data['country'].lower() + f': {self.server.style_data["country"]}') or ':united_nations: Unknown'
        embed.add_field(name='Country', value=flag_emoji, inline=True)

        game = 'fullname' in self.server.style_data and self.server.style_data['fullname'] or self.server.game_id
        embed.add_field(name='Game', value=game, inline=True)

        maps = (self.server.result['map'] and self.server.result['map'].strip()) and self.server.result['map'] or '-'
        embed.add_field(name='Current Map', value=maps, inline=True)

        if self.server.status:
            players_string = str(players) # example: 20
            
            if bots > 0:
                players_string += f' ({bots})' # example: 20 (2)
        else:
            players_string = '0' # example: 0
            
        players_string = f"{players_string}/{self.server.result['maxplayers']}"
        embed.add_field(name=f"Players", value=f"{players_string} ({int(players) / int(self.server.result['maxplayers']) * 100}%)", inline=True)

        if 'image_url' in self.server.style_data:
            image_url = str(self.server.style_data['image_url'])
            embed.set_thumbnail(url=image_url)
        
        advertisement = '📺 Game Servers Monitor'
        
        # Easter Egg
        today = str(date.today()) # 2020-12-23
        if '-12-25' in today:
            advertisement = '🎅 Merry Christmas!'
        elif '-01-01' in today:
            advertisement = '🎉 Happy New Year!'
        
        last_update = datetime.now().strftime('%Y-%m-%d %I:%M:%S%p')
        icon_url = 'https://avatars.githubusercontent.com/u/61296017'
        embed.set_footer(text=f'DiscordGSM {__version__} | {advertisement} | Last update: {last_update}', icon_url=icon_url)
        
        return embed
