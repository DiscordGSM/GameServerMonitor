import time
from typing import TYPE_CHECKING

import aiohttp
import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class ASA(Protocol):
    pre_query_required = True
    name = "asa"

    _client_id = "xyza7891muomRmynIIHaJB9COBKkwj6n"
    _client_secret = "PP5UGxysEieNfSrEicaD1N2Bb3TdXuD7xHYcsdUHZ7s"
    _deployment_id = "ad9a8feffb3b4b2ca315546f038c3ae2"
    _grant_type = "client_credentials"
    _external_auth_type = ""
    _external_auth_token = ""
    _access_token = ""

    async def pre_query(self):
        ASA._access_token = await opengsq.EOS.get_access_token(
            client_id=self._client_id,
            client_secret=self._client_secret,
            deployment_id=self._deployment_id,
            grant_type=self._grant_type,
            external_auth_type=self._external_auth_type,
            external_auth_token=self._external_auth_token,
        )

    async def query(self):
        if not ASA._access_token:
            await self.pre_query()

        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        start = time.time()

        # Try EOS first
        try:
            eos = opengsq.EOS(
                host, port, self._deployment_id, ASA._access_token, self.timeout
            )
            info = await eos.get_info()
            ping = int((time.time() - start) * 1000)

            attributes = dict(info.get("attributes", {}))
            settings = dict(info.get("settings", {}))

            result: GamedigResult = {
                "name": attributes.get("CUSTOMSERVERNAME_s", ""),
                "map": attributes.get("MAPNAME_s", ""),
                "password": attributes.get("SERVERPASSWORD_b", False),
                "numplayers": info.get("totalPlayers", 0),
                "numbots": 0,
                "maxplayers": settings.get("maxPublicPlayers", 0),
                "players": None,
                "bots": None,
                "connect": f"{host}:{port}",
                "ping": ping,
                "raw": info,
            }
            return result
        except Exception:
            # EOS failed, fallback to BattleMetrics
            start = time.time()  # Restart timer for BattleMetrics query

        # Fallback: Query BattleMetrics API with multi-stage strategy
        # Stage 1: Direct fuzzy search with exact IP:port verification
        # Stage 2: Pagination search by game filter only
        # Stage 3: Retry with alternative game codes
        
        async def battlemetrics_lookup(game_codes=None):
            """
            Multi-stage BattleMetrics lookup with exact IP:port matching.
            Returns server info dict or None if not found.
            """
            if game_codes is None:
                game_codes = ["arksa", "ark"]
            
            async with aiohttp.ClientSession() as session:
                for game_code in game_codes:
                    # Stage 1: Direct fuzzy search
                    try:
                        url = (
                            f"https://api.battlemetrics.com/servers?filter[game]={game_code}"
                            f"&filter[search]={host}:{port}&page[size]=100"
                        )
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                            if response.status == 200:
                                data = await response.json()
                                servers = data.get("data", [])
                                
                                # Check for exact match in fuzzy results
                                for server in servers:
                                    attrs = server.get("attributes", {})
                                    if (attrs.get("ip") == host and 
                                        (attrs.get("port") == port or attrs.get("portQuery") == port)):
                                        return server
                    except Exception:
                        pass
                    
                    # Stage 2: Pagination search by game filter only (more reliable for exact matches)
                    try:
                        page = 1
                        per_page = 100
                        max_pages = 5
                        
                        while page <= max_pages:
                            url = (
                                f"https://api.battlemetrics.com/servers?filter[game]={game_code}"
                                f"&page[size]={per_page}&page[number]={page}"
                            )
                            async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                                if response.status != 200:
                                    break
                                
                                data = await response.json()
                                servers = data.get("data", [])
                                
                                if not servers:
                                    break
                                
                                # Look for exact match
                                for server in servers:
                                    attrs = server.get("attributes", {})
                                    if (attrs.get("ip") == host and 
                                        attrs.get("port") == port):
                                        return server
                                
                                # Check if there are more pages
                                meta = data.get("meta", {})
                                pagination = meta.get("pagination", {})
                                total_pages = pagination.get("totalPages")
                                if total_pages is None or page >= total_pages:
                                    break
                                page += 1
                    except Exception:
                        continue
            
            return None
        
        server_info = await battlemetrics_lookup()
        if not server_info:
            raise Exception(f"No server found on BattleMetrics for {host}:{port}")

        ping = int((time.time() - start) * 1000)
        attrs = server_info.get("attributes", {})
        details = attrs.get("details", {})

        result: GamedigResult = {
            "name": attrs.get("name", ""),
            "map": details.get("map", ""),
            "password": details.get("password", False),
            "numplayers": attrs.get("players", 0),
            "numbots": 0,
            "maxplayers": attrs.get("maxPlayers", 0),
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": attrs,
        }
        return result
