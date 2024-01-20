import time
from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult

class SCP_SL(Protocol):
    name = 'scp_sl'

    async def query(self):
        token, accountid, servername = str(self.kv['_token']), str(self.kv['_accountid']), str(self.kv['_servername'])

        url = f'https://api.scpslgame.com/serverinfo.php?id={accountid}&key={token}&lo=true&players=true&list=true&version=true&flags=true&online=true'

        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        server_info = data.get("Servers", [])[0] if data.get("Servers") else {}
        ping = int((time.time() - time.mktime(time.strptime(server_info.get('LastOnline', '1970-01-01'), "%Y-%m-%d"))) * 1000)

        result: GamedigResult = {
            'name': f'{servername} - SCP SL Server {server_info.get("ID", "Offline")}',
            'map': '',
            'password': False,
            'numplayers': int(server_info.get("Players", "0/0").split("/")[0]),
            'numbots': 0,
            'maxplayers': int(server_info.get("Players", "0/0").split("/")[1]),
            'players': [{'name': player, 'raw': player} for player in server_info.get('PlayersList', [])],
            'bots': None,
            'connect': None,
            'ping': ping,
            'raw': data
        }

        return result
