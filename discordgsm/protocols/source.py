import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Source(Protocol):
    async def query(self):
        source = opengsq.Source(self.address, self.query_port, self.timeout)

        async def get_players():
            try:
                return await source.get_players()
            except Exception:
                # CSGO doesn't respond to player query if host_players_show is not 2
                # Conan Exiles never responds to player query
                return []

        start = time.time()
        info, players = await asyncio.gather(source.get_info(), get_players())
        ping = int((time.time() - start) * 1000)
        players.sort(key=lambda x: x['Duration'], reverse=True)
        players, bots = players[info['Bots']:], players[:info['Bots']]

        result: GamedigResult = {
            'name': info['Name'],
            'map': info['Map'],
            'password': info['Visibility'] != 0,
            'maxplayers': info['MaxPlayers'],
            'players': [{'name': player['Name'], 'raw': {'score': player['Score'], 'time': player['Duration']}} for player in players],
            'bots': [{'name': bot['Name'], 'raw': {'score': bot['Score'], 'time': bot['Duration']}} for bot in bots],
            'connect': f"{self.address}:{info.get('GamePort', self.query_port)}",
            'ping': ping,
            'raw': {
                'numplayers': info['Players'],
                'numbots': info['Bots']
            }
        }

        if tags := info.get('Keywords'):
            result['raw']['tags'] = str(tags).split(',')

        if info.get('GameID') == 629760:  # mordhau
            result['raw']['numplayers'] = int(next((tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'B:'), '0'))
        elif info.get('GameID') == 252490:  # rust
            result['maxplayers'] = int(next((tag[2:] for tag in result['raw']['tags'] if tag[:2] == 'mp'), result['maxplayers']))

        return result
