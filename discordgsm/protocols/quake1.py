import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Quake1():
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        quake1 = opengsq.Quake1(self.address, self.query_port, 10)
        start = time.time()
        status = await quake1.get_status()
        ping = int((time.time() - start) * 1000)
        info = status['info']
        players = []
        bots = []

        for player in status['players']:
            (bots if player['ping'] == 0 else players).append({'name': player['name'], 'raw': player})

        result: GamedigResult = {
            'name': info.get('hostname', info.get('sv_hostname', '')),
            'map': info.get('map', info.get('mapname', '')),
            'password': False,
            'maxplayers': int(info.get('sv_maxclients', info.get('maxclients', '0'))),
            'players': players,
            'bots': bots,
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': info
        }

        return result
