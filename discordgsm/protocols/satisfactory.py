import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Satisfactory(Protocol):
    name = "satisfactory"

    async def query(self):
        host, port, app_token = (
            str(self.kv["host"]),
            int(str(self.kv["port"])),
            str(self.kv["_token"]),
        )

        satisfactory = opengsq.Satisfactory(host, port, app_token, self.timeout)
        start = time.time()
        status = await satisfactory.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            "name": status.server_name,
            "map": "",
            "password": False,
            "numplayers": status.num_players,
            "numbots": 0,
            "maxplayers": status.server_max_nb_players,
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": status.__dict__,
        }

        return result
