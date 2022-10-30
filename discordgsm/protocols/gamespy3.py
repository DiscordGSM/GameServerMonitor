import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GameSpy3:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        gamespy3 = opengsq.GameSpy3(self.address, self.query_port, 10)
        start = time.time()
        status = await gamespy3.get_status()
        ping = int((time.time() - start) * 1000)
        info = status['info']
        players = status['player']

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['mapname'],
            'password': int(info['password']) != 0,
            'maxplayers': int(info['maxplayers']),
            'players': [{'name': player['player'], 'raw': player} for player in players],
            'bots': [],
            'connect': f"{self.address}:{info.get('hostport', self.query_port)}",
            'ping': ping,
            'raw': info
        }

        return result
