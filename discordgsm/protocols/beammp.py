import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp
from opengsq.socket_async import SocketAsync

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


@dataclass
class Response:
    players: str
    playerslist: str
    maxplayers: str
    ip: str
    location: str
    port: str
    dport: str
    map: str
    private: bool
    sname: str
    version: str
    cversion: str
    official: bool
    owner: str
    sdesc: str
    pps: str
    modlist: str
    modstotal: str
    modstotalsize: str


class BeamMP(Protocol):
    pre_query_required = True
    name = 'beammp'
    master_servers = None

    async def pre_query(self):
        # Known-bug: the api sometimes doesn't return full server list
        # (GET) https://backend.beammp.com/servers-info
        # (POST) https://backend.beammp.com/servers
        url = 'https://backend.beammp.com/servers-info'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                servers = await response.json()

        master_servers = {f'{server["ip"]}:{server["port"]}': Response(**server) for server in servers}

        # Temp fix the api bug, full update the BeamMP.master_servers when response servers > 1000
        if BeamMP.master_servers is None or len(servers) > 1000:
            BeamMP.master_servers = master_servers
        else:
            BeamMP.master_servers.update(master_servers)

    async def query(self):
        if BeamMP.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        ip = SocketAsync.gethostbyname(host)
        key = f'{ip}:{port}'

        if key not in BeamMP.master_servers:
            raise Exception('Server not found')

        server: Response = BeamMP.master_servers[key]
        result: GamedigResult = {
            'name': re.sub(r'\^[0-9|a-f|l-p|r]', '', server.sname),
            'map': re.sub(r'\/?levels\/(.+)\/info\.json', r'\1', server.map).replace('_', ' ').title(),
            'password': server.private,
            'numplayers': int(server.players),
            'numbots': 0,
            'maxplayers': int(server.maxplayers),
            'players': [{'name': name, 'raw': {}} for name in server.playerslist.split(';')],
            'bots': [],
            'connect': key,
            'ping': 0,
            'raw': server.__dict__
        }

        return result
