import asyncio
import time
from typing import TYPE_CHECKING

import opengsq
from opengsq.responses.source import SourceInfo, GoldSourceInfo, Visibility

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Source(Protocol):
    name = 'source'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        source = opengsq.Source(host, port, self.timeout)

        async def get_players():
            try:
                return await source.get_players()
            except Exception:
                # CSGO doesn't respond to player query if host_players_show is not 2
                # Conan Exiles never responds to player query
                return []

        start = time.time()

        # The Front incorrect info server name fix
        if self.kv['type'] == 'front':
            info, players, rules = await asyncio.gather(source.get_info(), get_players(), source.get_rules())
            info.name = rules['ServerName_s']  # Override the info server name
        else:
            info, players = await asyncio.gather(source.get_info(), get_players())

        if isinstance(info, SourceInfo):
            info: SourceInfo = info
            connect = f"{host}:{info.port}"
            game_id = info.game_id
            keywords = info.keywords
        elif isinstance(info, GoldSourceInfo):
            info: GoldSourceInfo = info
            connect = info.address
            game_id = None
            keywords = None

        ping = int((time.time() - start) * 1000)
        players.sort(key=lambda x: x.duration, reverse=True)
        players, bots = players[info.bots:], players[:info.bots]

        result: GamedigResult = {
            'name': info.name,
            'map': info.map,
            'password': info.visibility == Visibility.Private,
            'numplayers': info.players,
            'numbots': info.bots,
            'maxplayers': info.max_players,
            'players': [{'name': player.name, 'raw': {'score': player.score, 'time': player.duration}} for player in players],
            'bots': [{'name': bot.name, 'raw': {'score': bot.score, 'time': bot.duration}} for bot in bots],
            'connect': connect,
            'ping': ping,
            'raw': info.__dict__
        }

        if keywords:
            result['raw']['tags'] = str(keywords).split(',')

        if game_id == 629760:  # mordhau, fix numplayers
            result['numplayers'] = int(
                next((tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'B:'), '0'))
        elif game_id == 252490:  # rust, fix maxplayers
            result['maxplayers'] = int(next(
                (tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'mp'), result['maxplayers']))
        elif game_id == 346110:  # arkse, fix numplayers
            result['numplayers'] = len(result['players'])

        return result
