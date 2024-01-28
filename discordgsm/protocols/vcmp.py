import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Vcmp(Protocol):
    name = 'vcmp'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        vcmp = opengsq.Vcmp(host, port, self.timeout)

        async def get_players():
            try:
                return await vcmp.get_players()
            except Exception:
                # Server may not response when numplayers > 100
                return []

        start = time.time()
        status, players = await asyncio.gather(vcmp.get_status(), get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status.server_name,
            'map': status.language,
            'password': status.password,
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': status.max_players,
            'players': players,
            'bots': None,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': status.__dict__
        }

        return result
