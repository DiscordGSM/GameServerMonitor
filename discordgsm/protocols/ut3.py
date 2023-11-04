import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class UT3(Protocol):
    name = 'ut3'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        gamespy4 = opengsq.GameSpy4(host, port, self.timeout)
        start = time.time()
        status = await gamespy4.get_status()
        ping = int((time.time() - start) * 1000)
        info = status['info']
        players = status['player']

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['p1073741825'],
            'password': int(info['s7']) != 0,
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': int(info['maxplayers']),
            'players': [{'name': player['player'], 'raw': player} for player in players],
            'bots': None,
            'connect': f"{host}:{info.get('hostport', port)}",
            'ping': ping,
            'raw': info
        }

        return result
