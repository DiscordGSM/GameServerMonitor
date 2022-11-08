import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Raknet(Protocol):
    async def query(self):
        raknet = opengsq.Raknet(self.address, self.query_port, self.timeout)
        start = time.time()
        status = await raknet.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status.get('motd_line_1', ''),
            'map': status.get('motd_line_2', ''),
            'password': False,
            'maxplayers': int(status.get('max_players', '')),
            'players': [],
            'bots': [],
            'connect': f"{self.address}:{status.get('port_ipv4', self.query_port)}",
            'ping': ping,
            'raw': status
        }

        result['raw']['numplayers'] = int(status.get('num_players', ''))

        return result
