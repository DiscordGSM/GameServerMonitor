import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Unreal2(Protocol):
    async def query(self):
        unreal2 = opengsq.Unreal2(self.address, self.query_port, self.timeout)
        start = time.time()
        details = await unreal2.get_details()
        ping = int((time.time() - start) * 1000)
        numplayers = int(details['NumPlayers'])
        players = await unreal2.get_players() if numplayers > 0 else []

        result: GamedigResult = {
            'name': details['ServerName'],
            'map': details['MapName'],
            'password': False,
            'maxplayers': int(details['MaxPlayers']),
            'players': [{'name': player['Name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f"{self.address}:{details.get('GamePort', self.query_port)}",
            'ping': ping,
            'raw': details
        }

        return result
