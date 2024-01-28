import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class ASA(Protocol):
    pre_query_required = True
    name = 'asa'
    __access_token = ''

    __client_id = 'xyza7891muomRmynIIHaJB9COBKkwj6n'
    __client_secret = 'PP5UGxysEieNfSrEicaD1N2Bb3TdXuD7xHYcsdUHZ7s'
    __deployment_id = 'ad9a8feffb3b4b2ca315546f038c3ae2'
    __grant_type = "client_credentials"
    __external_auth_type = ""
    __external_auth_token = ""

    async def pre_query(self):
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

        host, port = str(self.kv['host']), int(str(self.kv['port']))
        eos = opengsq.EOS(host, port, self.__deployment_id, self.__access_token, self.timeout)
        start = time.time()
        info = await eos.get_info()
        ping = int((time.time() - start) * 1000)

        # Credits: @dkoz https://github.com/DiscordGSM/GameServerMonitor/pull/54/files
        attributes = dict(info.get('attributes', {}))
        settings = dict(info.get('settings', {}))

        result: GamedigResult = {
            'name': attributes.get('CUSTOMSERVERNAME_s', 'Unknown Server'),
            'map': attributes.get('MAPNAME_s', 'Unknown Map'),
            'password': attributes.get('SERVERPASSWORD_b', False),
            'numplayers': info.get('totalPlayers', 0),
            'numbots': 0,
            'maxplayers': settings.get('maxPublicPlayers', 0),
            'players': None,
            'bots': None,
            'connect': attributes.get('ADDRESS_s', '') + ':' + str(port),
            'ping': ping,
            'raw': info
        }

        return result
