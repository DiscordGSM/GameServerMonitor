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
        numplayers = int(details['NumPlayers'])
        players = await unreal2.get_players() if numplayers > 0 else []

        result: GamedigResult = {
            'name': details['ServerName'],
            'map': details['MapName'],
            'password': False,
            'numplayers': numplayers,
            'numbots': 0,
            'maxplayers': int(details['MaxPlayers']),
            'players': [{'name': player['Name'], 'raw': player} for player in players],
            'bots': None,
            'connect': f"{host}:{details.get('GamePort', port)}",
            'ping': ping,
            'raw': details
        }

        return result
