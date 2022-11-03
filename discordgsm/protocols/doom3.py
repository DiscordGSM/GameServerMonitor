import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Doom3:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        doom3 = opengsq.Doom3(self.address, self.query_port, 10)
        start = time.time()
        info = await doom3.get_info()
        ping = int((time.time() - start) * 1000)
        players = info.pop('players')

        result: GamedigResult = {
            'name': info.get('si_name', ''),
            'map': info.get('si_map', ''),
            'password': info.get('si_usepass', info.get('si_needPass', '0')) == 1,
            'maxplayers': int(info.get('si_maxplayers', info.get('si_maxPlayers', '0'))),
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': info
        }

        return result


if __name__ == '__main__':
    import asyncio

    async def main():
        doom3 = Doom3('88.99.0.7', 28007)
        print(await doom3.query())

    asyncio.run(main())
