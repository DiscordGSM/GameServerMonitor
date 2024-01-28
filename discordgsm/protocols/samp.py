import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Samp(Protocol):
    name = 'samp'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        samp = opengsq.Samp(host, port, self.timeout)

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
            'name': status.server_name,
            'map': rules.get('mapname', ''),
            'password': status.password,
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': status.max_players,
            'players': [{'name': player.name, 'raw': player.__dict__} for player in players],
            'bots': None,
            'connect': f'{host}:{port}',
            'ping': ping,
            'raw': {
                'info': status.__dict__,
                'rules': rules
            }
        }

        return result
