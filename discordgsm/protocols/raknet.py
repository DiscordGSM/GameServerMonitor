import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Raknet(Protocol):
    name = 'raknet'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        raknet = opengsq.Raknet(host, port, self.timeout)
        start = time.time()
        status = await raknet.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status.get('motd_line_1', ''),
            'map': status.get('motd_line_2', ''),
            'password': False,
            'numplayers': int(status.get('num_players', '')),
            'numbots': 0,
            'maxplayers': int(status.get('max_players', '')),
            'players': None,
            'bots': None,
            'connect': f"{host}:{status.get('port_ipv4', port)}",
            'ping': ping,
            'raw': status
        }

        return result
