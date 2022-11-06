import asyncio
import csv
import os
from typing import List, TypedDict

from discordgsm.protocols import Protocols

if __name__ == '__main__':
    from server import Server
else:
    from discordgsm.server import Server


class GamedigGame(TypedDict):
    """Gamedig Game"""
    id: str
    fullname: str
    protocol: str
    options: dict
    extra: dict


class GamedigPlayer(TypedDict):
    """Gamedig Player"""
    name: str
    raw: dict


class GamedigResult(TypedDict):
    """Gamedig Result"""
    name: str
    map: str
    password: bool
    maxplayers: int
    players: List[GamedigPlayer]
    bots: List[GamedigPlayer]
    connect: str
    ping: int
    raw: dict


class InvalidGameException(Exception):
    """Invalid Game Exception"""


class Gamedig:
    def __init__(self):
        path = os.path.dirname(os.path.realpath(__file__))
        self.games = Gamedig.__load_games(os.path.join(path, 'games.txt'))

    @staticmethod
    def __load_games(path: str):
        games: dict[str, GamedigGame] = {}

        def row_to_dict(row: str):
            data = {}

            if len(row) > 0:
                for item in row.split(','):
                    results = item.split('=')
                    data[results[0]] = results[1]

            return data

        with open(path, 'r', encoding='utf8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader, None)

            for row in reader:
                if len(row) > 0 and not row[0].startswith('#'):
                    id = row[0].split(',')[0]
                    options = len(row) > 3 and row_to_dict(row[3]) or {}
                    extra = len(row) > 4 and row_to_dict(row[4]) or {}
                    games[id] = GamedigGame(id=id, fullname=row[1], protocol=row[2], options=options, extra=extra)

        return games

    def find(self, game_id: str):
        if game_id in self.games:
            return self.games[game_id]

        raise LookupError()

    def default_port(self, game_id: str):
        game = self.games[game_id]

        if 'port_query' in game['options']:
            return int(game['options']['port_query'])
        elif 'port_query_offset' in game['options']:
            if 'port' in game['options']:
                return int(game['options']['port']) + int(game['options']['port_query_offset'])
            elif game['protocol'] == 'valve':
                return 27015 + int(game['options']['port_query_offset'])
        elif 'port' in game['options']:
            return int(game['options']['port'])

    @staticmethod
    def game_port(result: GamedigResult):
        """Attempt to get the game port from GamedigResult, return None if failure."""
        game_port: int = None

        if result['connect'] and ':' in result['connect']:
            elements = result['connect'].split(':')

            if len(elements) == 2 and elements[1].isdigit():
                game_port = int(elements[1])

        return game_port

    @staticmethod
    def is_port_valid(port: str):
        try:
            port_number = int(port)
        except ValueError:
            return False

        return 0 <= port_number <= 65535

    async def query(self, server: Server):
        return await self.run({**{
            'type': server.game_id,
            'host': server.address,
            'port': server.query_port,
        }, **server.query_extra})

    async def run(self, kv: dict):
        if protocol := Protocols.get(self.games[kv['type']]['protocol'], kv):
            return await asyncio.wait_for(protocol.query(), timeout=float(os.getenv('TASK_QUERY_SERVER_TIMEOUT', '15')))

        raise Exception('No protocol supported')


if __name__ == '__main__':
    async def main():
        r = await Gamedig().run({
            'type': '',
            'host': '',
            'port': ''
        })

        print(r)

    asyncio.run(main())
