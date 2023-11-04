import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GameSpy3(Protocol):
    name = 'gamespy3'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        gamespy3 = opengsq.GameSpy3(host, port, self.timeout)
        start = time.time()
        status = await gamespy3.get_status()
        ping = int((time.time() - start) * 1000)
        info = dict(status['info'])
        players = status.get('player') if status.get('player') else []

        result: GamedigResult = {
            'name': info.get('hostname', ''),
            'map': info.get('mapname', info.get('map', '')),
            'password': int(info.get('password', '0')) != 0,
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
