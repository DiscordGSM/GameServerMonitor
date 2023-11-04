import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Terraria(Protocol):
    name = 'terraria'

    async def query(self):
        host, port, token = str(self.kv['host']), int(str(self.kv['port'])), str(self.kv['_token'])
        url = f'http://{host}:{port}/v2/server/status?players=true&rules=false&token={token}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                end = time.time()

        result: GamedigResult = {
            'name': data['name'],
            'map': data['world'],
            'password': data['serverpassword'],
            'numplayers': len(data['players']),
            'numbots': 0,
            'maxplayers': data['maxplayers'],
            'players': [{'name': player['nickname'], 'raw': player} for player in data['players']],
            'bots': None,
            'connect': f"{host}:{data['port']}",
            'ping': int((end - start) * 1000),
            'raw': {}
        }

        return result
