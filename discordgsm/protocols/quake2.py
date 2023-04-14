import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Quake2(Protocol):
    name = 'quake2'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        quake2 = opengsq.Quake2(host, port, self.timeout)
        start = time.time()
        status = await quake2.get_status()
        ping = int((time.time() - start) * 1000)
        info = dict(status['info'])
        players = []
        bots = []

        for player in status['players']:
            (bots if player['ping'] == 0 else players).append({'name': player['name'], 'raw': player})

        result: GamedigResult = {
            'name': info.get('hostname', info.get('sv_hostname', '')),
            'map': info.get('mapname', ''),
            'password': int(info.get('g_needpass', info.get('needpass', '0'))) == 1,
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
