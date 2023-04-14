import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Hexen2(Protocol):
    name = 'hexen2'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        quake1 = opengsq.Quake1(host, port, self.timeout)
        quake1._request_header = b'\xFFstatus\x0a'
        quake1._response_header = b'\xFFn'

        start = time.time()
        status = await quake1.get_status()
        ping = int((time.time() - start) * 1000)
        info = dict(status['info'])
        players = []
        bots = []

        for player in status['players']:
            (bots if player['ping'] == 0 else players).append({'name': player['name'], 'raw': player})

        result: GamedigResult = {
            'name': info.get('hostname', info.get('sv_hostname', '')),
            'map': info.get('map', info.get('mapname', '')),
            'password': False,
            'numplayers': len(players),
            'numbots': len(bots),
            'maxplayers': int(info.get('sv_maxclients', info.get('maxclients', '0'))),
            'players': players,
            'bots': bots,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': info
        }

        return result
