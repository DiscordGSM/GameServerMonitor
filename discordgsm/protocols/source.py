import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

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
            info['Name'] = rules['ServerName_s']  # Override the info server name
        else:
            info, players = await asyncio.gather(source.get_info(), get_players())

        ping = int((time.time() - start) * 1000)
        players.sort(key=lambda x: x['Duration'], reverse=True)
        players, bots = players[info['Bots']:], players[:info['Bots']]

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

        if tags := info.get('Keywords'):
            result['raw']['tags'] = str(tags).split(',')

        if game_id := info.get('GameID'):
            if game_id == 629760:  # mordhau, fix numplayers
                result['numplayers'] = int(
                    next((tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'B:'), '0'))
            elif game_id == 252490:  # rust, fix maxplayers
                result['maxplayers'] = int(next(
                    (tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'mp'), result['maxplayers']))
            elif game_id == 346110:  # arkse, fix numplayers
                result['numplayers'] = len(result['players'])

        return result
