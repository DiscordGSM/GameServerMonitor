import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Minecraft:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        start = time.time()
        minecraft = opengsq.Minecraft(self.address, self.query_port, 10)
        status = await minecraft.get_status(strip_color=True)
        ping = int((time.time() - start) * 1000)
        name = ''

        if isinstance(status['description'], str):
            name = status['description']

        if 'text' in status['description'] and isinstance(status['description']['text'], str):
            name = status['description']['text']

        if 'extra' in status['description'] and isinstance(status['description']['extra'], list):
            name = ''.join(data.get('text', '') for data in status['description']['extra'])

        name = '\n'.join(row.strip() for row in name.split('\n'))

        result: GamedigResult = {
            'name': name,
            'map': '',
            'password': False,
            'maxplayers': int(status.get('players', {}).get('max', '0')),
            'players': [{'name': player.get('name', ''), 'raw': player} for player in status.get('players', {}).get('sample', [])],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': status
        }

        result['raw']['numplayers'] = int(status.get('players', {}).get('online', '0'))

        return result


if __name__ == '__main__':
    async def main():
        minecraft = Minecraft('minecraft.hypixel.net', 25565)
        print(await minecraft.query())

    asyncio.run(main())
