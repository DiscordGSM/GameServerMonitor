import time
from typing import TYPE_CHECKING

import opengsq
from opengsq.protocol_socket import Socket
from opengsq.exceptions.server_not_found_exception import ServerNotFoundException

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Palworld(Protocol):
    pre_query_required = True
    name = "palworld"

    _client_id = "xyza78916PZ5DF0fAahu4tnrKKyFpqRE"
    _client_secret = "j0NapLEPm3R3EOrlQiM8cRLKq3Rt02ZVVwT0SkZstSg"
    _deployment_id = "0a18471f93d448e2a1f60e47e03d3413"
    _grant_type = "external_auth"
    _external_auth_type = "deviceid_access_token"
    _external_auth_token = ""
    _access_token = ""

    async def pre_query(self):
        Palworld._external_auth_token = await opengsq.EOS.get_external_auth_token(
            client_id=self._client_id,
            client_secret=self._client_secret,
            external_auth_type=self._external_auth_type,
        )

        Palworld._access_token = await opengsq.EOS.get_access_token(
            client_id=self._client_id,
            client_secret=self._client_secret,
            deployment_id=self._deployment_id,
            grant_type=self._grant_type,
            external_auth_type=self._external_auth_type,
            external_auth_token=self._external_auth_token,
        )

    async def query(self):
        if not self._access_token:
            await self.pre_query()

        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        eos = opengsq.EOS(
            host, port, self._deployment_id, Palworld._access_token, self.timeout
        )
        start = time.time()

        try:
            # Filter the servers by ADDRESS_s and (ADDRESSBOUND_s or GAMESERVER_PORT_l)
            # Most of the Palworld servers work
            info = await eos.get_info()
        except ServerNotFoundException:
            # Get IP Address
            address = await Socket.gethostbyname(host)

            # Filter the servers by GAMESERVER_ADDRESS_s and GAMESERVER_PORT_l
            matchmaking = await eos.get_matchmaking(
                self._deployment_id,
                self._access_token,
                {
                    "criteria": [
                        {
                            "key": "attributes.GAMESERVER_ADDRESS_s",
                            "op": "EQUAL",
                            "value": address,
                        },
                        {
                            "key": "attributes.GAMESERVER_PORT_l",
                            "op": "EQUAL",
                            "value": port,
                        },
                    ]
                },
            )

            if matchmaking.count <= 0:
                raise ServerNotFoundException()

            info = matchmaking.sessions[0]

        ping = int((time.time() - start) * 1000)

        attributes = dict(info.get("attributes", {}))
        settings = dict(info.get("settings", {}))

        result: GamedigResult = {
            "name": attributes.get("NAME_s", ""),
            "map": attributes.get("MAPNAME_s", ""),
            "password": attributes.get("ISPASSWORD_b", False),
            "numplayers": attributes.get("PLAYERS_l", 0),
            "numbots": 0,
            "maxplayers": settings.get("maxPublicPlayers", 0),
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": info,
        }

        return result
