import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult

class Palworld(Protocol):
    name = "palworld"

    async def query(self):
        host, port, api_port, admin_password = (
            str(self.kv["host"]),
            int(str(self.kv["port"])),
            int(str(self.kv["api_port"])),
            str(self.kv["admin_password"]),
        )
        palworld = opengsq.Palworld(host, api_port, "admin", admin_password, self.timeout)
        start = time.time()
        data = await palworld.get_status()
        ping = int((time.time() - start) * 1000)
        if data.server_name:
            status = "online"
        else:
            status = "offline"
        result: GamedigResult = {
            "status": status,
            "name": data.server_name,
            "map": None,
            "password": False,
            "numplayers": data.num_players,
            "numbots": 0,
            "maxplayers": data.max_players,
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": data.__dict__,
        }

        return result
