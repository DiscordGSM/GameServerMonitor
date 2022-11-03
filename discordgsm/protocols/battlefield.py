import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Battlefield:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        battlefield = opengsq.Battlefield(self.address, self.query_port, 10)
        start = time.time()
        info, players = await asyncio.gather(battlefield.get_info(), battlefield.get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['map'],
            'password': info['password'],
            'maxplayers': info['maxplayers'],
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': info['ip_port'],
            'ping': ping,
            'raw': info
        }

        return result


if __name__ == '__main__':
    async def main():
        battlefield = Battlefield('74.91.124.140', 47200)
        print(await battlefield.query())

    asyncio.run(main())
