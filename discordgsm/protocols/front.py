import asyncio
import os
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
    name = "front"

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
            "connect": f'{host}:{info["GamePort"]}',
            "ping": ping,
            "raw": info,
        }

        return result

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)

        base_url = os.getenv('OPENGSQ_MASTER_SERVER_URL', 'https://master-server.opengsq.com/').rstrip('/')
        url = f"{base_url}/thefront/search?host={ip}&port={port}"
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data: dict = await response.json()
                ping = int((time.time() - start) * 1000)

        info = dict(data["info"])

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
            "ping": ping,
            "raw": data,
        }

        return result


if __name__ == "__main__":
    async def main():
        front = Front({"host": "", "port": 27015})
        print(await front.query())

    asyncio.run(main())
