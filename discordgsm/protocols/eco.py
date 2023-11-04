import re
import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Eco(Protocol):
    name = 'eco'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'http://{host}:{port}/info'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                ping = int((time.time() - start) * 1000)

        name = re.sub(r'<color=\w*>|<(color=)?#[0-9a-fA-F]{6}>|<\/color>', '', data['Description'])
        name = re.sub(r'</?b>', '', name)
        name = re.sub(r'</?i>', '_', name)

        result: GamedigResult = {
            'name': name,
            'map': '',
            'password': data['HasPassword'],
            'numplayers': data['OnlinePlayers'],
            'numbots': 0,
            'maxplayers': data['MaxActivePlayers'],
            'players': [{'name': player, 'raw': player} for player in data['OnlinePlayersNames']],
            'bots': None,
            'connect': data['JoinUrl'],
            'ping': ping,
            'raw': data
        }

        return result
