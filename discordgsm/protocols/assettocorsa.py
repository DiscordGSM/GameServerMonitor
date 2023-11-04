import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class AssettoCorsa(Protocol):
    name = 'assettocorsa'

    async def query(self):
        host = str(self.kv['host'])
        start = time.time()
        info, data = await asyncio.gather(self.query_info(), self.query_json())
        ping = int((time.time() - start) * 1000)
        players = [{'name': car['DriverName'], 'raw': car} for car in data['Cars'] if car['IsConnected']]

        result: GamedigResult = {
            'name': info['name'],
            'map': info['track'],
            'password': info['pass'],
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': info['maxclients'],
            'players': players,
            'bots': None,
            'connect': f'{host}:{info["port"]}',
            'ping': ping,
            'raw': {
                'Info': info,
                'Json': data
            }
        }

        return result

    async def query_info(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'http://{host}:{port}/INFO?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)

    async def query_json(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        url = f'http://{host}:{port}/JSON|{int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)
