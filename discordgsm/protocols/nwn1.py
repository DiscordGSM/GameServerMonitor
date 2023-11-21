from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp
from opengsq.socket_async import SocketAsync

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


@dataclass
class Response:
    active_player_count: str
    maximum_player_count: str
    game_type: str
    module_name: str
    module_url: str
    online: str  # bool
    server_address: str
    server_name: str
    server_description: str
    module_description: str
    build_number: str
    elc_enforced: str  # bool
    last_heartbeat: str
    local_vault: str  # bool
    maximum_level: str
    minimum_level: str
    pvp_level: str
    pwc_url: str
    player_pause: str  # bool
    password_protected: str  # bool


class NWN1(Protocol):
    pre_query_required = True
    name = 'nwn1'
    master_servers = None

    async def pre_query(self):
        url = 'https://nwnlist.herokuapp.com/servers/NWN1'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                servers = await response.json(content_type=None)

        NWN1.master_servers = {str(server["server_address"]): Response(**server) for server in servers}

    async def query(self):
        if NWN1.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        ip = await SocketAsync.gethostbyname(host)
        key = f'{ip}:{port}'

        if key not in NWN1.master_servers:
            raise Exception('Server not found')

        server: Response = NWN1.master_servers[key]
        result: GamedigResult = {
            'name': server.server_name,
            'map': '',
            'password': str(server.password_protected) == 'true',
            'numplayers': int(server.active_player_count),
            'numbots': 0,
            'maxplayers': int(server.maximum_player_count),
            'players': None,
            'bots': None,
            'connect': key,
            'ping': 0,
            'raw': server.__dict__
        }

        return result
