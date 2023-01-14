import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GPortal(Protocol):
    def __init__(self, address: str, query_port: int, server_id: str):
        super().__init__(address, query_port)
        self.server_id = server_id

    async def query(self):
        url = f'https://api.g-portal.com/gameserver/query/{self.server_id}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                end = time.time()

        if self.address != data['ipAddress'] or self.query_port != data['port']:
            raise Exception('Invalid address or port')

        if not data['online']:
            raise Exception('Server offline')

        result: GamedigResult = {
            'name': data['name'],
            'map': '',
            'password': False,
            'numplayers': data['currentPlayers'],
            'numbots': 0,
            'maxplayers': data['maxPlayers'],
            'players': [],
            'bots': [],
            'connect': f"{data['ipAddress']}:{data['port']}",
            'ping': int((end - start) * 1000),
            'raw': data
        }

        return result
