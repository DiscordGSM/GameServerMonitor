import time
from typing import TYPE_CHECKING

import opengsq

print("Available in opengsq:", dir(opengsq))
print("UT3 available:", hasattr(opengsq, 'UT3'))

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class UT3_LAN(Protocol):
    name = "ut3_lan"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))

        #ut3 = opengsq.UT3(host, port, self.timeout)
        from opengsq.protocols.ut3 import UT3
        ut3 = UT3(host, port, self.timeout)
        start = time.time()

        status = await ut3.get_status()
        ping = int((time.time() - start) * 1000)

        players = []
        for player in status.players:
            players.append({
                "name": player.name,
                "raw": player.__dict__
            })

        bots = []
        for bot in status.bots:
            bots.append({
                "name": bot.name,
                "raw": bot.__dict__
            })

        result: GamedigResult = {
            "name": status.server_name,
            "map": status.map_name,
            "password": status.password_protected,
            "numplayers": len(status.players),
            "numbots": len(status.bots),
            "maxplayers": status.max_players,
            "players": players,
            "bots": bots,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": {
                "game_type": status.game_type,
                "gamemode": status.raw.get("gamemode"),
                "mutators": status.mutators,
                "stock_mutators": status.stock_mutators,
                "custom_mutators": status.custom_mutators,
                "bot_skill": status.raw.get("bot_skill"),
                "time_limit": status.raw.get("time_limit"),
                "frag_limit": status.raw.get("frag_limit"),
                "vs_bots": status.raw.get("vs_bots"),
                "force_respawn": status.raw.get("force_respawn"),
                "pure_server": status.raw.get("pure_server")
            }
        }

        return result