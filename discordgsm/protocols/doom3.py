import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Doom3(Protocol):
    name = "doom3"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        doom3 = opengsq.Doom3(host, port, self.timeout)
        start = time.time()
        status = await doom3.get_status()
        info = status.info
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            "name": info.get("si_name", ""),
            "map": info.get("si_map", ""),
            "password": info.get("si_usepass", info.get("si_needPass", "0")) == 1,
            "numplayers": int(status.players),
            "numbots": 0,
            "maxplayers": int(
                info.get("si_maxplayers", info.get("si_maxPlayers", "0"))
            ),
            "players": [
                {"name": player["name"], "raw": player} for player in status.players
            ],
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": info,
        }

        return result
