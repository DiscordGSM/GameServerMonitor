import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Palworld(Protocol):
    pre_query_required = True
    name = "palworld"

    __client_id = "xyza78916PZ5DF0fAahu4tnrKKyFpqRE"
    __client_secret = "j0NapLEPm3R3EOrlQiM8cRLKq3Rt02ZVVwT0SkZstSg"
    __deployment_id = "0a18471f93d448e2a1f60e47e03d3413"
    __grant_type = "external_auth"
    __external_auth_type = "deviceid_access_token"
    __external_auth_token = ""
    __access_token = ""

    async def pre_query(self):
        self.__external_auth_token = await opengsq.EOS.get_external_auth_token(
            client_id=self.__client_id,
            client_secret=self.__client_secret,
            external_auth_type=self.__external_auth_type,
        )

        self.__access_token = await opengsq.EOS.get_access_token(
            client_id=self.__client_id,
            client_secret=self.__client_secret,
            deployment_id=self.__deployment_id,
            grant_type=self.__grant_type,
            external_auth_type=self.__external_auth_type,
            external_auth_token=self.__external_auth_token,
        )

    async def query(self):
        if not self.__access_token:
            await self.pre_query()

        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        eos = opengsq.EOS(
            host, port, self.__deployment_id, self.__access_token, self.timeout
        )
        start = time.time()
        info = await eos.get_info()
        ping = int((time.time() - start) * 1000)

        attributes = dict(info.get("attributes", {}))
        settings = dict(info.get("settings", {}))

        result: GamedigResult = {
            "name": attributes.get("NAME_s", "Unknown Server"),
            "map": "",
            "password": attributes.get("ISPASSWORD_b", False),
            "numplayers": attributes.get("PLAYERS_l", 0),
            "numbots": 0,
            "maxplayers": settings.get("maxPublicPlayers", 0),
            "players": None,
            "bots": None,
            "connect": attributes.get("ADDRESS_s", "") + ":" + str(port),
            "ping": ping,
            "raw": info,
        }

        return result
