import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GameSpy2(Protocol):
    async def query(self):
        gamespy2 = opengsq.GameSpy2(self.address, self.query_port, self.timeout)
        start = time.time()
        status = await gamespy2.get_status()
        ping = int((time.time() - start) * 1000)
        info = status['info']
        players = status['players']

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['mapname'],
            'password': str(info['password']).lower() != 'false',
            'maxplayers': int(info['maxplayers']),
            'players': [{'name': player['player'], 'raw': player} for player in players],
            'bots': [],
            'connect': f"{self.address}:{info.get('hostport', self.query_port)}",
            'ping': ping,
            'raw': info
        }

        return result
