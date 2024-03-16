import os
import re
import time
from typing import TYPE_CHECKING

import aiohttp
from opengsq.protocol_socket import Socket

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class BeamMP(Protocol):
    name = "beammp"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)

        base_url = os.getenv('OPENGSQ_MASTER_SERVER_URL', 'https://master-server.opengsq.com/').rstrip('/')
        url = f"{base_url}/beammp/search?host={ip}&port={port}"
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data: dict = await response.json()
                ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            "name": re.sub(r"\^[0-9|a-f|l-p|r]", "", str(data["sname"])),
            "map": re.sub(r"\/?levels\/(.+)\/info\.json", r"\1", str(data["map"]))
            .replace("_", " ")
            .title(),
            "password": bool(data.get("password", False)),
            "numplayers": int(data["players"]),
            "numbots": 0,
            "maxplayers": int(data["maxplayers"]),
            "players": [
                {"name": name, "raw": {}}
                for name in str(data["playerslist"]).split(";")
            ],
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": data,
        }

        return result
