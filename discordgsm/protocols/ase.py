import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class ASE:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        ase = opengsq.ASE(self.address, self.query_port, 10)
        start = time.time()
        status = await ase.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['hostname'],
            'map': status['map'] if status['map'] != 'None' else '',
            'password': int(status['password']) != 0,
            'maxplayers': int(status['maxplayers']),
            'players': [{'name': player['name'], 'raw': player} for player in status['players']],
            'bots': [],
            'connect': f"{self.address}:{status.get('gameport', self.query_port)}",
            'ping': ping,
            'raw': status
        }

        return result


if __name__ == '__main__':
    import asyncio

    async def main():
        ase = ASE('79.137.97.3', 22126)
        print(await ase.query())

    asyncio.run(main())
