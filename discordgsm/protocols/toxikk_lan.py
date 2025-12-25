import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Toxikk_LAN(Protocol):
    name = "toxikk_lan"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))

        toxikk = opengsq.Toxikk(host, port, self.timeout)
        start = time.time()

        status = await toxikk.get_status()
        ping = int((time.time() - start) * 1000)

        # Looking at ut3.py, the response is parsed from UDK base class
        # and then enhanced with UT3-specific data

        # Extract players from the status object
        players = []
        for player in getattr(status, "players", []):
            players.append(
                {
                    "name": getattr(player, "name", ""),
                    "raw": vars(
                        player
                    ),  # Convert player object attributes to dictionary
                }
            )

        # For numbots, use the value from raw properties if available
        numbots = 0
        raw_data = vars(status).get("raw", {})
        if "numbots" in raw_data:
            numbots = int(raw_data["numbots"])

        result: GamedigResult = {
            "name": getattr(status, "name", ""),
            "map": getattr(
                status, "map_name", status.map if hasattr(status, "map") else ""
            ),
            "password": getattr(status, "password_protected", False),
            "numplayers": len(players),
            "numbots": numbots,
            "maxplayers": getattr(status, "max_players", 0),
            "players": players,
            "bots": [],  # No bots list available, just use empty list
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": {
                "game_type": getattr(status, "game_type", ""),
                "gamemode": raw_data.get("gamemode", ""),
                "mutators": getattr(status, "mutators", []),
                "stock_mutators": getattr(status, "stock_mutators", []),
                "custom_mutators": getattr(status, "custom_mutators", []),
                "bot_skill": raw_data.get("bot_skill", ""),
                "time_limit": raw_data.get("time_limit", 0),
                "frag_limit": raw_data.get("frag_limit", 0),
                "vs_bots": raw_data.get("vs_bots", ""),
                "force_respawn": raw_data.get("force_respawn", False),
                "pure_server": raw_data.get("pure_server", False),
            },
        }

        return result
