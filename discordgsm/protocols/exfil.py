import asyncio
import time
import logging
from typing import TYPE_CHECKING

import aiohttp
import opengsq
from opengsq.responses.source import SourceInfo, GoldSourceInfo, Visibility

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult

logger = logging.getLogger(__name__)


class Exfil(Protocol):
    name = "exfil"

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        start = time.time()

        # Stage 1: Try HTTP API first
        try:
            async with aiohttp.ClientSession() as session:
                api_url = f"http://{host}:{port}/status"
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, dict):
                            # Successfully got API response
                            logger.debug(f"Exfil HTTP API success for {host}:{port}")
                            result = await self._build_result_from_api(data, host, port, start, time.time())
                            return result
                    else:
                        logger.debug(f"Exfil HTTP API failed with status {response.status} for {host}:{port}")
        except asyncio.TimeoutError:
            logger.debug(f"Exfil HTTP API timeout for {host}:{port}")
        except Exception as e:
            logger.debug(f"Exfil HTTP API exception for {host}:{port}: {type(e).__name__}: {e}")

        # Stage 2: Fallback to Source protocol (A2S query)
        try:
            logger.debug(f"Exfil falling back to Source protocol for {host}:{port}")
            source = opengsq.Source(host, port, self.timeout)

            async def get_players():
                try:
                    return await source.get_players()
                except Exception:
                    return []

            # Query info and players from Source protocol
            info, players = await asyncio.gather(source.get_info(), get_players())

            if isinstance(info, SourceInfo):
                info: SourceInfo = info
                connect = f"{host}:{info.port}"
            elif isinstance(info, GoldSourceInfo):
                info: GoldSourceInfo = info
                connect = info.address
            else:
                raise Exception("Unknown SourceInfo type")

            ping = int((time.time() - start) * 1000)
            players.sort(key=lambda x: x.duration, reverse=True)
            players, bots = players[info.bots :], players[: info.bots]

            result: GamedigResult = {
                "name": info.name,
                "map": info.map,
                "password": info.visibility == Visibility.Private,
                "numplayers": info.players,
                "numbots": info.bots,
                "maxplayers": info.max_players,
                "players": [
                    {
                        "name": player.name,
                        "raw": {"score": player.score, "time": player.duration},
                    }
                    for player in players
                ],
                "bots": [
                    {"name": bot.name, "raw": {"score": bot.score, "time": bot.duration}}
                    for bot in bots
                ],
                "connect": connect,
                "ping": ping,
                "raw": info.__dict__,
            }
            logger.debug(f"Exfil Source protocol success for {host}:{port}")
            return result

        except Exception as e:
            logger.error(f"Exfil protocol failed for {host}:{port}: {type(e).__name__}: {e}")
            raise Exception(f"Both HTTP API and Source protocol failed for {host}:{port}: {str(e)}")

    async def _build_result_from_api(self, api_data: dict, host: str, port: int, start_time: float, end_time: float) -> "GamedigResult":
        """
        Build standardized GamedigResult from HTTP API response.
        Maps API fields to match expected format.
        Handles both Exfil API format and Steam A2S format.
        """
        ping = int((end_time - start_time) * 1000)

        # Extract and map fields from API response
        # Try multiple possible field names for server name
        name = (api_data.get("serverName") or 
                api_data.get("name") or 
                api_data.get("SteamServerName_s") or 
                "Unknown")
        map_name = api_data.get("map", "Unknown")
        password = api_data.get("password", False)

        # Parse player count - handle both formats:
        # Format 1: Players_s = "X/Y" (Steam A2S format)
        # Format 2: players = X, maxPlayers = Y (Exfil API format)
        numplayers = 0
        maxplayers = 0
        if "Players_s" in api_data:
            players_str = str(api_data["Players_s"])
            if "/" in players_str:
                try:
                    numplayers, maxplayers = map(int, players_str.split("/"))
                except (ValueError, IndexError):
                    numplayers = 0
                    maxplayers = 0
        else:
            # Use direct integer fields (Exfil API format)
            numplayers = int(api_data.get("players", api_data.get("current", 0)))
            maxplayers = int(api_data.get("maxPlayers", api_data.get("max", 0)))

        # Extract player list if available
        player_list = []
        if isinstance(api_data.get("playerList"), list):
            player_list = [
                {"name": player if isinstance(player, str) else player.get("name", "Unknown"), "raw": {}}
                for player in api_data["playerList"]
            ]

        result: GamedigResult = {
            "name": name,
            "map": map_name,
            "password": bool(password),
            "numplayers": numplayers,
            "numbots": 0,
            "maxplayers": maxplayers,
            "players": player_list if player_list else None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": api_data,
        }

        return result
