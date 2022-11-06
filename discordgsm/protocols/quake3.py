import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Quake3(Protocol):
    async def query(self):
        quake3 = opengsq.Quake3(self.address, self.query_port, self.timeout)
        start = time.time()
        status = await quake3.get_status(strip_color=True)
        ping = int((time.time() - start) * 1000)
        info = status['info']
        players = []
        bots = []

        for player in status['players']:
            (bots if player['ping'] == 0 else players).append({'name': player['name'], 'raw': player})

        result: GamedigResult = {
            'name': info.get('hostname', info.get('sv_hostname', '')),
            'map': info.get('mapname', ''),
            'password': int(info.get('g_needpass', '0')) == 1,
            'maxplayers': int(info.get('sv_maxclients', '0')),
            'players': players,
            'bots': bots,
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': info
        }

        return result
