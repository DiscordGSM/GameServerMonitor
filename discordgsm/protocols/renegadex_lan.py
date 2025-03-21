import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class RenegadeX(Protocol):
    name = "renegadex_lan"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv.get("port")))

        renegadex = opengsq.RenegadeX(host, port, self.timeout)
        start = time.time()

        status = await renegadex.get_status()
        ping = int((time.time() - start) * 1000)

        # RenegadeX doesn't provide individual player information
        # Just the total count
        players = []
        
        # Create empty player objects based on the total count
        # since we don't have individual player data
        for _ in range(status.players):
            players.append({
                "name": "",  # No player names available
                "raw": {}
            })

        # Get variables from status
        variables = status.variables

        result: GamedigResult = {
            "name": status.name,
            "map": status.current_map,
            "password": variables.passworded,
            "numplayers": status.players,
            "numbots": 0,  # No bot information available
            "maxplayers": variables.player_limit,
            "players": players,
            "bots": [],  # No bot information available
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": {
                "game_version": status.game_version,
                "vehicle_limit": variables.vehicle_limit,
                "mine_limit": variables.mine_limit,
                "time_limit": variables.time_limit,
                "steam_required": variables.steam_required,
                "team_mode": variables.team_mode,
                "spawn_crates": variables.spawn_crates,
                "game_type": variables.game_type,
                "ranked": variables.ranked
            }
        }

        return result