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
        samp = opengsq.Vcmp(host, port, self.timeout)

        async def get_players():
            try:
                return await samp.get_players()
            except Exception:
                # Server may not response when numplayers > 100
                return []

        start = time.time()
        status, players = await asyncio.gather(samp.get_status(), get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['servername'],
            'map': status.get('language', ''),
            'password': status['password'] == 1,
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': status['maxplayers'],
            'players': players,
            'bots': None,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': status
        }

        return result
