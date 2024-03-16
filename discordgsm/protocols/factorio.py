import os
import re
import time
from typing import TYPE_CHECKING

import aiohttp
from opengsq.protocol_socket import Socket

from discordgsm.environment import env
from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Factorio(Protocol):
    pre_query_required = False
    name = "factorio"
    master_servers = None

    def __init__(self, kv: dict):
        super().__init__(kv)

        # Get FACTORIO_USERNAME and FACTORIO_TOKEN on https://www.factorio.com/profile
        # Notice: It requires to own Factorio on steam account
        self.username, self.token = (
            str(env("FACTORIO_USERNAME")).strip(),
            str(env("FACTORIO_TOKEN")).strip(),
        )

        if self.username and self.token:
            self.pre_query_required = True

    async def pre_query(self):
        if not self.pre_query_required:
            return

        url = f"https://multiplayer.factorio.com/get-games?username={self.username}&token={self.token}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                servers = await response.json()

        if "message" in servers:
            # Possible error messages
            # 1. User not found.        -> Invalid FACTORIO_USERNAME
            # 2. Token doesn't match.   -> Invalid FACTORIO_TOKEN
            raise Exception(servers["message"])

        master_servers = {server["host_address"]: server for server in servers}
        Factorio.master_servers = master_servers

    async def query(self):
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        ip = await Socket.gethostbyname(host)

        if self.pre_query_required:
            if Factorio.master_servers is None:
                await self.pre_query()

            host_address = f"{ip}:{port}"

            if host_address not in Factorio.master_servers:
                raise Exception("Server not found")

            data = dict(Factorio.master_servers[host_address])
            ping = 0
        else:
            base_url = os.getenv('OPENGSQ_MASTER_SERVER_URL', 'https://master-server.opengsq.com/').rstrip('/')
            url = f"{base_url}/factorio/search?host={ip}&port={port}"
            start = time.time()

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data: dict = await response.json()
                    ping = int((time.time() - start) * 1000)

        # Remove the rich text formatting
        # https://wiki.factorio.com/Rich_text
        name = re.sub(r"\[\w*=\w*\]|\[\/\w*\]", "", data["name"])
        players = list(data.get("players", []))

        result: GamedigResult = {
            "name": name,
            "map": "",
            "password": data["has_password"],
            "numplayers": len(players),
            "numbots": 0,
            "maxplayers": data["max_players"],
            "players": [{"name": player, "raw": player} for player in players],
            "bots": None,
            "connect": data["host_address"],
            "ping": ping,
            "raw": data,
        }

        return result
