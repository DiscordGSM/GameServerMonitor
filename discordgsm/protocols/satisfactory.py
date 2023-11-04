import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Satisfactory(Protocol):
    name = 'satisfactory'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        satisfactory = opengsq.Satisfactory(host, port, self.timeout)
        start = time.time()
        status = await satisfactory.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': '',
            'map': '',
            'password': False,
            'numplayers': 0,
            'numbots': 0,
            'maxplayers': 0,
            'players': None,
            'bots': None,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': status
        }

        return result
