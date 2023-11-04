import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GameSpy2(Protocol):
    name = 'gamespy2'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        gamespy2 = opengsq.GameSpy2(host, port, self.timeout)
        start = time.time()
        status = await gamespy2.get_status()
        ping = int((time.time() - start) * 1000)
        info = dict(status['info'])
        players = status['players']
        password = str(info.get('password', '0')).lower()

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['mapname'],
            'password': password == 'true' or password == '1',
            'numplayers': int(info['numplayers']),
            'numbots': 0,
            'maxplayers': int(info['maxplayers']),
            'players': [{'name': player['player'], 'raw': player} for player in players],
            'bots': None,
            'connect': f"{host}:{info.get('hostport', port)}",
            'ping': ping,
            'raw': info
        }

        return result
