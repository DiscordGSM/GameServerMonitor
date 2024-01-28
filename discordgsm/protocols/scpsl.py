from typing import TYPE_CHECKING

import aiohttp

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class SCPSL(Protocol):
    name = 'scpsl'

    async def query(self):
        api_key, accountid = str(self.kv['_api_key']), str(self.kv['_account_id'])
        url = f'https://api.scpslgame.com/serverinfo.php?id={accountid}&key={api_key}&lo=true&players=true&list=true&version=true&flags=true&nicknames=true&online=true'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data: dict = await response.json()

        if not data['Success']:
            raise Exception(data['Error'])

        server_info: dict = data['Servers'][0]
        players_list: list[dict] = server_info['PlayersList']
        numplayers, maxplayers = str(server_info.get("Players", "0/0")).split("/")

        result: GamedigResult = {
            'name': server_info['ID'],
            'map': '',
            'password': False,
            'numplayers': int(numplayers),
            'numbots': 0,
            'maxplayers': int(maxplayers),
            'players': [{'name': player, 'raw': player} for player in players_list],
            'bots': None,
            'connect': None,
            'ping': 0,
            'raw': server_info
        }

        return result
