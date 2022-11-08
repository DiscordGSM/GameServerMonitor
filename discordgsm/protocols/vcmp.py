import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Vcmp(Protocol):
    async def query(self):
        samp = opengsq.Vcmp(self.address, self.query_port, self.timeout)

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
            'maxplayers': status['maxplayers'],
            'players': players,
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': status
        }

        return result
