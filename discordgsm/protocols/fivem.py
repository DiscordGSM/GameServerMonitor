import asyncio
import time
from typing import TYPE_CHECKING

import aiohttp
import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class FiveM():
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        quake3 = opengsq.Quake3(self.address, self.query_port, 10)
        start = time.time()
        info, players = await asyncio.gather(quake3.get_info(strip_color=True), self.query_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info.get('hostname', ''),
            'map': info.get('mapname', ''),
            'password': False,
            'maxplayers': int(info.get('sv_maxclients', '0')),
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': {
                'numplayers': int(info.get('clients', '0')),
            }
        }

        return result

    async def query_info(self):
        url = f'http://{self.address}:{self.query_port}/info.json?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)

    async def query_players(self):
        url = f'http://{self.address}:{self.query_port}/players.json?v={int(time.time())}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json(content_type=None)


if __name__ == '__main__':
    async def main():
        fivem = FiveM('85.215.99.119', 30112)
        print(await fivem.query())

    asyncio.run(main())
