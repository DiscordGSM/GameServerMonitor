import time
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Discord:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    async def query(self):
        url = f'https://discord.com/api/guilds/{self.guild_id}/widget.json?v={int(time.time())}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': data['name'],
            'map': '',
            'password': False,
            'maxplayers': -1,
            'players': [{'name': player['username'], 'raw': player} for player in data['members']],
            'bots': [],
            'connect': data['instant_invite'],
            'ping': ping,
            'raw': {
                'numplayers': data['presence_count'],
            }
        }

        return result
