import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Unreal2(Protocol):
    name = 'unreal2'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        unreal2 = opengsq.Unreal2(host, port, self.timeout)
        start = time.time()
        details = await unreal2.get_details()
        ping = int((time.time() - start) * 1000)
        players = await unreal2.get_players() if details.num_players > 0 else []

        result: GamedigResult = {
            'name': details.server_name,
            'map': details.map_name,
            'password': False,
            'numplayers': details.num_players,
            'numbots': 0,
            'maxplayers': details.max_players,
            'players': [{'name': player.name, 'raw': player.__dict__} for player in players],
            'bots': None,
            'connect': f"{host}:{details.game_port}",
            'ping': ping,
            'raw': details.__dict__
        }

        return result
