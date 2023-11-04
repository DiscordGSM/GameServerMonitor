import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp
import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class FiveM(Protocol):
    name = 'fivem'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        quake3 = opengsq.Quake3(host, port, self.timeout)
        start = time.time()
        info, players = await asyncio.gather(quake3.get_info(strip_color=True), self.query_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info.get('hostname', ''),
            'map': info.get('mapname', ''),
            'password': False,
            'numplayers': int(info.get('clients', '0')),
            'numbots': 0,
            'maxplayers': int(info.get('sv_maxclients', '0')),
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': None,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': info
        }

        return result

    async def query_info(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'http://{host}:{port}/info.json?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)

    async def query_players(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'http://{host}:{port}/players.json?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)
