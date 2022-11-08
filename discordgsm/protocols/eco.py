import time
from typing import TYPE_CHECKING

from discordgsm.protocols.protocol import Protocol
import aiohttp

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Eco(Protocol):
    async def query(self):
        url = f'http://{self.address}:{self.query_port}/info'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': data['Description'],
            'map': '',
            'password': data['HasPassword'],
            'maxplayers': data['MaxActivePlayers'],
            'players': [{'name': player, 'raw': player} for player in data['OnlinePlayersNames']],
            'bots': [],
            'connect': data['JoinUrl'],
            'ping': ping,
            'raw': {
                'numplayers': data['OnlinePlayers'],
            }
        }

        return result
