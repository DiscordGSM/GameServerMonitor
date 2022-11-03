import time
from typing import TYPE_CHECKING

import opengsq

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Raknet:
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port

    async def query(self):
        raknet = opengsq.Raknet(self.address, self.query_port, 10)
        start = time.time()
        status = await raknet.get_status()
        ping = int((time.time() - start) * 1000)

        result: GamedigResult = {
            'name': status.get('motd_line_1', ''),
            'map': status.get('motd_line_2', ''),
            'password': False,
            'maxplayers': int(status.get('max_players', '')),
            'players': [],
            'bots': [],
            'connect': f"{self.address}:{status.get('port_ipv4', self.query_port)}",
            'ping': ping,
            'raw': status
        }

        result['raw']['numplayers'] = int(status.get('num_players', ''))

        return result


if __name__ == '__main__':
    import asyncio

    async def main():
        raknet = Raknet('mobzgaming.hopto.org', 19132)
        print(await raknet.query())

    asyncio.run(main())
