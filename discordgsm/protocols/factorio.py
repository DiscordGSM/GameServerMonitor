import re
from typing import TYPE_CHECKING

import aiohttp
from opengsq.socket_async import SocketAsync

from discordgsm.environment import env
from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Factorio(Protocol):
    pre_query_required = True
    name = 'factorio'
    master_servers = None

    async def pre_query(self):
        # Get FACTORIO_USERNAME and FACTORIO_TOKEN on https://www.factorio.com/profile
        # Notice: It requires to own Factorio on steam account
        username, token = str(env('FACTORIO_USERNAME')).strip(), str(env('FACTORIO_TOKEN')).strip()
        url = f'https://multiplayer.factorio.com/get-games?username={username}&token={token}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                servers = await response.json()

        if 'message' in servers:
            # Possible error messages
            # 1. User not found.        -> Invalid FACTORIO_USERNAME
            # 2. Token doesn't match.   -> Invalid FACTORIO_TOKEN
            raise Exception(servers['message'])

        master_servers = {server['host_address']: server for server in servers}
        Factorio.master_servers = master_servers

    async def query(self):
        if Factorio.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        ip = await SocketAsync.gethostbyname(host)
        host_address = f'{ip}:{port}'

        if host_address not in Factorio.master_servers:
            raise Exception('Server not found')

        server = dict(Factorio.master_servers[host_address])

        # Remove the rich text formatting
        # https://wiki.factorio.com/Rich_text
        name = re.sub(r'\[\w*=\w*\]|\[\/\w*\]', '', server['name'])
        players = server['players'] if 'players' in server else []

        result: GamedigResult = {
            'name': name,
            'map': '',
            'password': server['has_password'],
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': server['max_players'],
            'players': [{'name': player, 'raw': player} for player in players],
            'bots': None,
            'connect': server['host_address'],
            'ping': 0,
            'raw': server
        }

        return result
