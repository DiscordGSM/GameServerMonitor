import os
import time
from typing import TYPE_CHECKING

import aiohttp

from opengsq.protocol_socket import Socket

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Scum(Protocol):
    name = "scum"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)

        base_url = os.getenv('OPENGSQ_MASTER_SERVER_URL', 'https://master-server.opengsq.com/').rstrip('/')
        url = f"{base_url}/scum/search?host={ip}&port={port}"
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data: dict = await response.json()
                ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            "name": data.get("name", ""),
            "map": "",
            "password": data.get("password", False),
            "numplayers": data.get("num_players", 0),
            "numbots": 0,
            "maxplayers": data.get("max_players", 0),
            "players": None,
            "bots": None,
            "connect": f"{host}:{port - 2}",
            "ping": ping,
            "raw": data,
        }

        return result
