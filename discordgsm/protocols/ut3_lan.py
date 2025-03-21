import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class UT3_LAN(Protocol):
    name = "ut3_lan"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))

        ut3 = opengsq.UT3(host, port, self.timeout)
        start = time.time()

        result_dict = await ut3.get_status()
        ping = int((time.time() - start) * 1000)

        # Based on the UDK implementation, players and bots are likely in result_dict
        players = []
        for player in result_dict.get('players', []):
            players.append({
                "name": player.get('name', ''),
                "raw": player
            })

        bots = []
        # Check if there are bots in the response or use numbots from properties
        bots_list = result_dict.get('bots', [])
        numbots = len(bots_list)
        # If there's no 'bots' field but there's a numbots in raw properties 
        if not bots_list and 'raw' in result_dict and 'numbots' in result_dict['raw']:
            numbots = int(result_dict['raw']['numbots'])

        for bot in bots_list:
            bots.append({
                "name": bot.get('name', ''),
                "raw": bot
            })

        result: GamedigResult = {
            "name": result_dict.get('server_name', ''),
            "map": result_dict.get('map', ''),
            "password": result_dict.get('password_protected', False),
            "numplayers": len(players),
            "numbots": numbots,
            "maxplayers": result_dict.get('max_players', 0),
            "players": players,
            "bots": bots,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": result_dict.get('raw', {})
        }

        return result