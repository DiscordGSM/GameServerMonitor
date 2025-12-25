import asyncio
import json
import time
from typing import TYPE_CHECKING

import aiohttp
import opengsq
from opengsq.protocol_socket import Socket

if __name__ == "__main__":
    from protocol import Protocol
else:
    from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Front(Protocol):
    pre_query_required = True
    name = "front"
    master_servers = None

    async def pre_query(self):
        url = "https://privatelist.playthefront.com/private_list"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                res = await response.json(content_type=None)

        if res["msg"] != "ok":
            raise LookupError(res["msg"])

        servers = list(res["server_list"])
        Front.master_servers = {
            f"{server['addr']}:{server['port']}": server for server in servers
        }

    # old method
    async def _query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        start = time.time()
        source = opengsq.Source(host, port, self.timeout)
        info, rules = await asyncio.gather(source.get_info(), source.get_rules())
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            "name": rules.get("ServerName_s"),
            "map": info["Map"],
            "password": info["Visibility"] != 0,
            "numplayers": info["Players"],
            "numbots": info["Bots"],
            "maxplayers": info["MaxPlayers"],
            "players": None,
            "bots": None,
            "connect": f"{host}:{info['GamePort']}",
            "ping": ping,
            "raw": info,
        }

        return result

    async def query(self):
        if Front.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)
        key = f"{ip}:{port}"

        data: dict = Front.master_servers[key]
        info: dict = json.loads(data["info"])

        result: GamedigResult = {
            "name": data.get("server_name", ""),
            "map": info.get("game_map", ""),
            "password": info.get("HasPWD", False),
            "numplayers": data.get("online", 0),
            "numbots": 0,
            "maxplayers": info.get("maxplayer", 0),
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": 0,
            "raw": data,
        }

        return result


if __name__ == "__main__":

    async def main():
        front = Front({"host": "", "port": 5001})
        print(await front.query())

    asyncio.run(main())
