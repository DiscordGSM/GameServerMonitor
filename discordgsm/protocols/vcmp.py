import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Vcmp:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        samp = opengsq.Vcmp(self.address, self.query_port, 10)

        async def get_players():
            try:
                return await samp.get_players()
            except Exception:
                # Server may not response when numplayers > 100
                return []

        start = time.time()
        status, players = await asyncio.gather(samp.get_status(), get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['servername'],
            'map': status.get('language', ''),
            'password': status['password'] == 1,
            'maxplayers': status['maxplayers'],
            'players': players,
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': status
        }

        return result


if __name__ == '__main__':
    async def main():
        vcmp = Vcmp('91.121.134.5', 8192)
        print(await vcmp.query())

    asyncio.run(main())
