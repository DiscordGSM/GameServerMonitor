from typing import TYPE_CHECKING

import opengsq
from opengsq.socket_async import SocketAsync

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Scum(Protocol):
    pre_query_required = True
    name = 'scum'
    master_servers = None

    async def pre_query(self):
        master_servers = await opengsq.Scum.query_master_servers()
        Scum.master_servers = {f"{server['ip']}:{server['port']}": server for server in master_servers}

    async def query(self):
        if Scum.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        ip = await SocketAsync.gethostbyname(host)
        host_address = f'{ip}:{port}'

        if host_address not in Scum.master_servers:
            raise Exception('Server not found')

        server = dict(Scum.master_servers[host_address])
        result: GamedigResult = {
            'name': server['name'],
            'map': '',
            'password': server['password'],
            'numplayers': server['numplayers'],
            'numbots': 0,
            'maxplayers': server['maxplayers'],
            'players': None,
            'bots': None,
            'connect': f"{host}:{server['port'] - 2}",
            'ping': 0,
            'raw': server
        }

        return result
