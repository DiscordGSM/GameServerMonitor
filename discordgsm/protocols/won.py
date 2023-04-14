import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class WON(Protocol):
    name = 'won'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        won = opengsq.WON(host, port, self.timeout)
        start = time.time()
        info, players = await asyncio.gather(won.get_info(), won.get_players())
        ping = int((time.time() - start) * 1000)
        players.sort(key=lambda x: x['Duration'])
        bots = []

        while len(bots) < info['Bots']:
            bots.append(players.pop() if len(players) > 0 else {})

        result: GamedigResult = {
            'name': info['Name'],
            'map': info['Map'],
            'password': info['Visibility'] != 0,
            'numplayers': info['Players'],
            'numbots': info['Bots'],
            'maxplayers': info['MaxPlayers'],
            'players': [{'name': player['Name'], 'raw': {'score': player['Score'], 'time': player['Duration']}} for player in players],
            'bots': [{'name': bot['Name'], 'raw': {'score': bot['Score'], 'time': bot['Duration']}} for bot in bots],
            'connect': f"{host}:{info.get('GamePort', port)}",
            'ping': ping,
            'raw': info
        }

        return result
