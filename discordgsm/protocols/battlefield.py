import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Battlefield(Protocol):
    async def query(self):
        battlefield = opengsq.Battlefield(self.address, self.query_port, self.timeout)
        start = time.time()
        info, players = await asyncio.gather(battlefield.get_info(), battlefield.get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['map'],
            'password': info['password'],
            'maxplayers': info['maxplayers'],
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': info['ip_port'],
            'ping': ping,
            'raw': info
        }

        return result
