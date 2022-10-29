from .discord import Discord
from .fivem import FiveM
from .gamespy1 import GameSpy1
from .gamespy2 import GameSpy2
from .source import Source
from .terraria import Terraria
from .quake3 import Quake3


class Protocol:
    @staticmethod
    def get(protocol_name: str, kv: dict):
        address = str(kv['host'])
        query_port = int(str(kv['port']))

        if kv['type'] == 'terraria':
            return Terraria(address, query_port, str(kv['_token']))
        elif kv['type'] == 'discord':
            return Discord(address)
        elif kv['type'] == 'fivem':
            return FiveM(address, query_port)
        elif protocol_name == 'valve':
            return Source(address, query_port)
        elif protocol_name == 'gamespy1':
            return GameSpy1(address, query_port)
        elif protocol_name == 'gamespy2':
            return GameSpy2(address, query_port)
        elif protocol_name == 'quake3':
            return Quake3(address, query_port)

        return None
