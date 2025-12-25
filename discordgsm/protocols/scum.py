from typing import TYPE_CHECKING

import aiohttp

from opengsq.protocol_socket import Socket

from discordgsm.protocols.protocol import Protocol
from discordgsm.version import __version__

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Scum(Protocol):
    name = "scum"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)

        url = f"https://api.hellbz.de/scum/api.php?address={ip}&port={port}"

        async with aiohttp.ClientSession(
            headers={
                "User-Agent": f"GameServerMonitor/{__version__} (DiscordGSM; https://discordgsm.com; https://github.com/DiscordGSM/GameServerMonitor; SCUM server status check)"
            }
        ) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                res: dict = await response.json()

        if len(res.get("data", [])) <= 0:
            raise Exception("Server not found")

        data: dict = res["data"][0]

        result: GamedigResult = {
            "name": data.get("name", ""),
            "map": "",
            "password": data.get("password", 0) == 1,
            "numplayers": data.get("players", 0),
            "numbots": 0,
            "maxplayers": data.get("players_max", 0),
            "players": None,
            "bots": None,
            "connect": None,
            "ping": 0,
            "raw": data,
        }

        return result
