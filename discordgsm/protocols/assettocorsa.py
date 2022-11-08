import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class AssettoCorsa(Protocol):
    async def query(self):
        start = time.time()
        info, data = await asyncio.gather(self.query_info(), self.query_json())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info['name'],
            'map': info['track'],
            'password': info['pass'],
            'maxplayers': info['maxclients'],
            'players': [{'name': car['DriverName'], 'raw': car} for car in data['Cars'] if car['IsConnected']],
            'bots': [],
            'connect': f'{self.address}:{info["port"]}',
            'ping': ping,
            'raw': {
                'Info': info,
                'Json': data
            }
        }

        return result

    async def query_info(self):
        url = f'http://{self.address}:{self.query_port}/INFO?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)

    async def query_json(self):
        url = f'http://{self.address}:{self.query_port}/JSON|{int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)
