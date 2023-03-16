import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Satisfactory(Protocol):
    def __init__(self, address: str, query_port: int):
        super().__init__(address, query_port)

    async def query(self):
        satisfactory = opengsq.Satisfactory(self.address, self.query_port, self.timeout)
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
            'players': [],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': status
        }

        return result
