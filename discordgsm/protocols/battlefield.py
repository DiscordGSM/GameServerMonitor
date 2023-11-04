import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Battlefield(Protocol):
    name = 'battlefield'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        battlefield = opengsq.Battlefield(host, port, self.timeout)
        start = time.time()
        info, players = await asyncio.gather(battlefield.get_info(), battlefield.get_players())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': info['hostname'],
            'map': info['map'],
            'password': info['password'],
            'numplayers': info['numplayers'],
            'numbots': 0,
            'maxplayers': info['maxplayers'],
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': None,
            'connect': info['ip_port'],
            'ping': ping,
            'raw': info
        }

        return result
