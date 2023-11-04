import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Discord(Protocol):
    name = 'discord'

    async def query(self):
        guild_id = str(self.kv['host'])
        url = f'https://discord.com/api/guilds/{guild_id}/widget.json?v={int(time.time())}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': data['name'],
            'map': '',
            'password': False,
            'numplayers': data['presence_count'],
            'numbots': 0,
            'maxplayers': -1,
            'players': [{'name': player['username'], 'raw': player} for player in data['members']],
            'bots': None,
            'connect': data['instant_invite'],
            'ping': ping,
            'raw': {}
        }

        return result
