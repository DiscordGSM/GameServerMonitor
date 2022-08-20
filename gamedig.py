import csv
import json
import platform
import re
import subprocess
from typing import TypedDict

from server import Server


class Gamedig:
    def __init__(self, file: str = 'data/games.txt'):
        self.games: dict[str, GamedigGame] = {}
        
        def row_to_dict(row: str):
            d = {}
            
            if len(row) > 0:
                for x in row.split(','):
                    y = x.split('=')
                    d[y[0]] = y[1]
                
            return d
        
        with open(file, 'r', encoding='utf8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader, None)
            
            for row in reader:
                if len(row) > 0: 
                    options = len(row) > 3 and row_to_dict(row[3]) or {}
                    extra = len(row) > 4 and row_to_dict(row[4]) or {}
                    self.games[row[0]] = GamedigGame(id=row[0], fullname=row[1], protocol=row[2], options=options, extra=extra)

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
    def query(server: Server):
        return Gamedig.run({
            'type': server.game_id,
            'host': server.address,
            'port': server.query_port,
        } | server.query_extra)

    @staticmethod
    def run(kv: dict):
        args = ['cmd.exe', '/c', 'gamedig'] if platform.system() == 'Windows' else ['gamedig']
        
        for option, value in kv.items():
            args.extend([f'--{option}', Gamedig.__escape_argument(str(value)) if platform.system() == 'Windows' else str(value)])
        
        process = subprocess.run(args, stdout=subprocess.PIPE)
        output = process.stdout.decode('utf8')
        result: GamedigResult = json.loads(output)
        
        if 'error' in result:
            raise Exception(result['error'])

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


class GamedigGame(TypedDict):
    id: str
    fullname: str
    protocol: str
    options: dict
    extra: dict


class GamedigPlayer(TypedDict):
    name: str
    raw: dict


class GamedigResult(TypedDict):
    name: str
    map: str
    password: bool
    maxplayers: int
    players: list[GamedigPlayer]
    bots: list[GamedigPlayer]
    connect: str
    ping: str
    raw: dict


if __name__ == '__main__':
    r = Gamedig.run({
        'type': 'tf2',
        'host': '104.238.229.98',
        'port': '27015'
    })
    
    print(r['players'])
