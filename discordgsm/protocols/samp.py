import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Samp:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        samp = opengsq.Samp(self.address, self.query_port, 10)

        async def get_players():
            try:
                return await samp.get_players()
            except Exception:
                # Server may not response when numplayers > 100
                return []

        start = time.time()
        status, players, rules = await asyncio.gather(samp.get_status(), get_players(), samp.get_rules())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['servername'],
            'map': rules.get('mapname', ''),
            'password': status['password'] == 1,
            'maxplayers': status['maxplayers'],
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': {
                'info': status,
                'rules': rules
            }
        }

        return result


if __name__ == '__main__':
    async def main():
        samp = Samp('51.254.178.238', 7777)
        print(await samp.query())

    asyncio.run(main())
