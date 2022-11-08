import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Samp(Protocol):
    async def query(self):
        samp = opengsq.Samp(self.address, self.query_port, self.timeout)

        async def get_players():
            try:
                return await samp.get_players()
            except Exception:
                # Server may not response when numplayers > 100
                return []

        start = time.time()
        status, players, rules = await asyncio.gather(samp.get_status(), get_players(), samp.get_rules())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status['servername'],
            'map': rules.get('mapname', ''),
            'password': status['password'] == 1,
            'maxplayers': status['maxplayers'],
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': {
                'info': status,
                'rules': rules
            }
        }

        return result
