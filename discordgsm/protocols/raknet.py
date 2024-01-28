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
        raknet = opengsq.RakNet(host, port, self.timeout)
        start = time.time()
        status = await raknet.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status.motd_line1,
            'map': status.motd_line2,
            'password': False,
            'numplayers': status.num_players,
            'numbots': 0,
            'maxplayers': status.max_players,
            'players': None,
            'bots': None,
            'connect': f"{host}:{status.port_ipv4}",
            'ping': ping,
            'raw': status
        }

        return result
