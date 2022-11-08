import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Doom3(Protocol):
    async def query(self):
        doom3 = opengsq.Doom3(self.address, self.query_port, self.timeout)
        start = time.time()
        info = await doom3.get_info()
        ping = int((time.time() - start) * 1000)
        players = info.pop('players')

        result: GamedigResult = {
            'name': info.get('si_name', ''),
            'map': info.get('si_map', ''),
            'password': info.get('si_usepass', info.get('si_needPass', '0')) == 1,
            'maxplayers': int(info.get('si_maxplayers', info.get('si_maxPlayers', '0'))),
            'players': [{'name': player['name'], 'raw': player} for player in players],
            'bots': [],
            'connect': f'{self.address}:{self.query_port}',
            'ping': ping,
            'raw': info
        }

        return result
