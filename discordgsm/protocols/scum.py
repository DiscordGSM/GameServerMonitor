import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Scum(Protocol):
    name = 'scum'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'https://api.hellbz.de/scum/api.php?address={host}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                end = time.time()

        if not data['success']:
            raise Exception(data['error'])

        servers = data['data']

        if server := next((x for x in servers if int(x['q_port']) == port), None):
            result: GamedigResult = {
                'name': server['name'],
                'map': '',
                'password': server['password'] == 1,
                'numplayers': server['players'],
                'numbots': 0,
                'maxplayers': server['players_max'],
                'players': [],
                'bots': [],
                'connect': f"{host}:{server['port']}",
                'ping': int((end - start) * 1000),
                'raw': server
            }

            return result

        raise Exception('Invalid query port')
