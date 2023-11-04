import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class ASE(Protocol):
    name = 'ase'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        ase = opengsq.ASE(host, port, self.timeout)
        start = time.time()
        status = await ase.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['hostname'],
            'map': status['map'] if status['map'] != 'None' else '',
            'password': int(status['password']) != 0,
            'numplayers': int(status['numplayers']),
            'numbots': 0,
            'maxplayers': int(status['maxplayers']),
            'players': [{'name': player['name'], 'raw': player} for player in status['players']],
            'bots': None,
            'connect': f"{host}:{status.get('gameport', port)}",
            'ping': ping,
            'raw': status
        }

        return result
