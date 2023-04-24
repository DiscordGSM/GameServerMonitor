import re
import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Factorio(Protocol):
    name = 'factorio'

    async def query(self):
        host, port, game_id = str(self.kv['host']), int(str(self.kv['port'])), str(self.kv['gameId']).strip()
        url = f'https://multiplayer.factorio.com/get-game-details/{game_id}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                ping = int((time.time() - start) * 1000)

        if 'message' in data:
            raise Exception(data['message'])

        if data['host_address'] != f'{host}:{port}':
            raise Exception(f'Incorrect address or query port, excepted value: {data["host_address"]}')

        # Remove the rich text formatting
        # https://wiki.factorio.com/Rich_text
        name = re.sub(r'\[\w*=\w*\]|\[\/\w*\]', '', data['name'])
        players = data['players'] if 'players' in data else []

        result: GamedigResult = {
            'name': name,
            'map': '',
            'password': data['has_password'],
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': data['max_players'],
            'players': [{'name': player, 'raw': player} for player in players],
            'bots': [],
            'connect': data['host_address'],
            'ping': ping,
            'raw': data
        }

        return result
