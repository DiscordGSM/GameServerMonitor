import asyncio
import time
from typing import TYPE_CHECKING

import opengsq
from opengsq.responses.source import Player, SourceInfo, GoldSourceInfo, Visibility

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
        players.sort(key=lambda x: x.duration)
        bots: list[Player] = []

        while len(bots) < info['Bots']:
            bots.append(players.pop() if len(players) > 0 else {})

        if isinstance(info, SourceInfo):
            connect = f"{host}:{info.port}"
        elif isinstance(info, GoldSourceInfo):
            connect = info.address

        result: GamedigResult = {
            'name': info.name,
            'map': info.map,
            'password': info.visibility == Visibility.Private,
            'numplayers': info.players,
            'numbots': info.bots,
            'maxplayers': info.max_players,
            'players': [{'name': player.name, 'raw': player.__dict__} for player in players],
            'bots': [{'name': bot.name, 'raw': bot.__dict__} for bot in bots],
            'connect': connect,
            'ping': ping,
            'raw': info
        }

        return result
