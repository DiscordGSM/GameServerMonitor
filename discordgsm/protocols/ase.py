import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class ASE(Protocol):
    async def query(self):
        ase = opengsq.ASE(self.address, self.query_port, self.timeout)
        start = time.time()
        status = await ase.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['hostname'],
            'map': status['map'] if status['map'] != 'None' else '',
            'password': int(status['password']) != 0,
            'maxplayers': int(status['maxplayers']),
            'players': [{'name': player['name'], 'raw': player} for player in status['players']],
            'bots': [],
            'connect': f"{self.address}:{status.get('gameport', self.query_port)}",
            'ping': ping,
            'raw': status
        }

        return result
