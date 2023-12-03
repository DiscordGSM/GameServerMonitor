import asyncio
from dataclasses import dataclass
import json
import time
from typing import TYPE_CHECKING

import aiohttp
import opengsq
from opengsq.socket_async import SocketAsync

if __name__ == '__main__':
    from protocol import Protocol
else:
    from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


@dataclass
class FrontServer:
    server_name: str
    district_id: int
    server_id: int
    type: int
    addr: str
    port: int
    info: dict
    online: int
    status: int
    owner_type: int


class Front(Protocol):
    pre_query_required = False
    name = 'front'
    master_servers = None

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        start = time.time()
        source = opengsq.Source(host, port, self.timeout)
        info, rules = await asyncio.gather(source.get_info(), source.get_rules())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': rules.get('ServerName_s'),
            'map': info['Map'],
            'password': info['Visibility'] != 0,
            'numplayers': info['Players'],
            'numbots': info['Bots'],
            'maxplayers': info['MaxPlayers'],
            'players': None,
            'bots': None,
            'connect': f'{host}:{info["GamePort"]}',
            'ping': ping,
            'raw': info
        }

        return result

    # Requires AccessKeyId
    async def pre_query(self):
        url = 'https://privatelist.playthefront.com/private_list'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.read()
                json_data = json.loads(data)
                server_list = json_data['server_list']

                # Convert server_list to a list of FrontServer objects
                Front.master_servers = {f"{server['addr']}:{server['port']}": FrontServer(
                    server_name=server['server_name'],
                    district_id=server['district_id'],
                    server_id=server['server_id'],
                    type=server['type'],
                    addr=server['addr'],
                    port=server['port'],
                    info=json.loads(server['info']),
                    online=server['online'],
                    status=server['status'],
                    owner_type=server['owner_type']
                ) for server in server_list}

        return Front.master_servers

    async def _query(self):
        if Front.master_servers is None:
            await self.pre_query()
            assert Front.master_servers is not None, "Front.master_servers is still None after pre_query"

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        start = time.time()
        source = opengsq.Source(host, port, self.timeout)
        info = await source.get_info()
        ping = int((time.time() - start) * 1000)

        ip = await SocketAsync.gethostbyname(host)
        host_address = f'{ip}:{info["GamePort"]}'

        if host_address not in Front.master_servers:
            raise Exception('Server not found')

        server = Front.master_servers[host_address]

        result: GamedigResult = {
            'name': server.server_name,
            'map': server.info.get('game_map'),
            'password': info['Visibility'] != 0,
            'numplayers': server.online,
            'numbots': 0,
            'maxplayers': server.info.get('maxplayer'),
            'players': None,
            'bots': None,
            'connect': host_address,
            'ping': ping,
            'raw': server.__dict__
        }

        return result


if __name__ == '__main__':
    async def main():
        front = Front({'host': '', 'port': 27015})
        print(await front.query())

    asyncio.run(main())
