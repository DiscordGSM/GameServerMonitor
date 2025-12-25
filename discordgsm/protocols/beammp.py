import re
from typing import TYPE_CHECKING

import aiohttp
from opengsq.protocol_socket import Socket

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class BeamMP(Protocol):
    pre_query_required = True
    name = "beammp"
    master_servers = None

    async def pre_query(self):
        url = "https://backend.beammp.com/servers-info"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                servers: dict = await response.json()

        BeamMP.master_servers = {f"{s['ip']}:{s['port']}": s for s in servers}

    async def query(self):
        if BeamMP.master_servers is None:
            await self.pre_query()

        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)
        key = f"{ip}:{port}"

        if key not in BeamMP.master_servers:
            raise Exception("Server not found")

        data = BeamMP.master_servers[key]
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
            "ping": 0,
            "raw": data,
        }

        return result
