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
            'name': status.hostname,
            'map': status.map if status.map != 'None' else '',
            'password': status.password,
            'numplayers': status.num_players,
            'numbots': 0,
            'maxplayers': status.max_players,
            'players': [{'name': player.name, 'raw': player.__dict__} for player in status.players],
            'bots': None,
            'connect': f"{host}:{status.game_port}",
            'ping': ping,
            'raw': status.__dict__
        }

        return result
