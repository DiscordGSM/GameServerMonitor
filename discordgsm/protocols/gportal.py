import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class GPortal(Protocol):
    name = 'gportal'

    async def query(self):
        host, port, server_id = str(self.kv['host']), int(str(self.kv['port'])), str(self.kv['serverId'])
        url = f'https://api.g-portal.com/gameserver/query/{server_id}'
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                end = time.time()

        if host != data['ipAddress'] or port != data['port']:
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
            'players': None,
            'bots': None,
            'connect': f"{data['ipAddress']}:{data['port']}",
            'ping': int((end - start) * 1000),
            'raw': data
        }

        return result
