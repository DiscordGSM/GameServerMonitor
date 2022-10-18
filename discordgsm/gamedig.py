import asyncio
import csv
import json
import os
import platform
import re
import time
from typing import List, TypedDict

import aiohttp

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
        self.default_games = Gamedig.__load_games(os.path.join(path, '..', 'node_modules', 'gamedig', 'games.txt'))

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
                if len(row) > 0:
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

    async def query(self, server: Server):
        return await self.run({**{
            'type': server.game_id,
            'host': server.address,
            'port': server.query_port,
        }, **server.query_extra})

    async def run(self, kv: dict):
        if kv['type'] not in self.default_games:
            kv['type'] = f"protocol-{self.games[kv['type']]['protocol']}"

        return await Gamedig.__run(kv)

    @staticmethod
    async def __run(kv: dict):
        if kv['type'] == 'terraria':
            return await query_terraria(kv['host'], kv['port'], kv['_token'])
        elif kv['type'] == 'discord':
            return await query_discord(kv['host'])

        args = ['cmd.exe', '/c'] if platform.system() == 'Windows' else []
        args.extend(['node', os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../node_modules/gamedig/bin/gamedig.js'))])

        for option, value in kv.items():
            args.extend([f'--{str(option).lstrip("_")}', Gamedig.__escape_argument(str(value)) if platform.system() == 'Windows' else str(value)])

        process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()
        result: GamedigResult = json.loads(stdout)

        if 'error' in result:
            if 'Invalid game:' in result['error']:
                raise InvalidGameException()
            else:
                raise Exception(result['error'])

        if kv['type'] == 'mordhau':
            for tag in result['raw'].get('tags', []):
                if tag[:2] == 'B:':
                    result['raw']['numplayers'] = int(tag[2:])
                    break

        result['raw'] = result.get('raw', {})

        return result

    # Credits: https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows
    @staticmethod
    def __escape_argument(arg: str):
        if not arg or re.search(r'(["\s])', arg):
            arg = '"' + arg.replace('"', r'\"') + '"'

        return Gamedig.__escape_for_cmd_exe(arg)

    # Credits: https://stackoverflow.com/questions/29213106/how-to-securely-escape-command-line-arguments-for-the-cmd-exe-shell-on-windows
    @staticmethod
    def __escape_for_cmd_exe(arg: str):
        meta_re = re.compile(r'([()%!^"<>&|])')
        return meta_re.sub('^\1', arg)


async def query_terraria(host: str, port: int, token: str):
    url = f'http://{host}:{port}/v2/server/status?players=true&rules=false&token={token}'
    start = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            end = time.time()

    result: GamedigResult = {
        'name': data['name'],
        'map': data['world'],
        'password': data['serverpassword'],
        'maxplayers': data['maxplayers'],
        'players': [{'name': player['nickname'], 'raw': player} for player in data['players']],
        'bots': [],
        'connect': f"{host}:{data['port']}",
        'ping': int((end - start) * 1000),
        'raw': {}
    }

    return result


async def query_discord(guild_id: str):
    url = f'https://discord.com/api/guilds/{guild_id}/widget.json?v={int(time.time())}'
    start = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            end = time.time()

    result: GamedigResult = {
        'name': data['name'],
        'map': '',
        'password': False,
        'maxplayers': -1,
        'players': [{'name': player['username'], 'raw': player} for player in data['members']],
        'bots': [],
        'connect': data['instant_invite'],
        'ping': int((end - start) * 1000),
        'raw': {
            'numplayers': data['presence_count'],
        }
    }

    return result


if __name__ == '__main__':
    async def main():
        r = await Gamedig().run({
            'type': 'tf2',
            'host': '104.238.229.98',
            'port': '27015'
        })

        print(r)

    asyncio.run(main())
