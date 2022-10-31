from .assettocorsa import AssettoCorsa
from .discord import Discord
from .fivem import FiveM
from .gamespy1 import GameSpy1
from .gamespy2 import GameSpy2
from .gamespy3 import GameSpy3
from .hexen2 import Hexen2
from .quake1 import Quake1
from .quake2 import Quake2
from .quake3 import Quake3
from .source import Source
from .terraria import Terraria
from .unreal2 import Unreal2
from .ut3 import UT3
from .won import WON


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
        elif kv['type'] == 'hexen2':
            return Hexen2(address, query_port)
        elif kv['type'] == 'assettocorsa':
            return AssettoCorsa(address, query_port)
        elif protocol_name == 'valve':
            return Source(address, query_port)
        elif protocol_name == 'gamespy1':
            return GameSpy1(address, query_port)
        elif protocol_name == 'gamespy2':
            return GameSpy2(address, query_port)
        elif protocol_name == 'gamespy3':
            return GameSpy3(address, query_port)
        elif protocol_name == 'quake1':
            return Quake1(address, query_port)
        elif protocol_name == 'quake2':
            return Quake2(address, query_port)
        elif protocol_name == 'quake3':
            return Quake3(address, query_port)
        elif protocol_name == 'unreal2':
            return Unreal2(address, query_port)
        elif protocol_name == 'ut3':
            return UT3(address, query_port)
        elif protocol_name == 'goldsrc':
            return WON(address, query_port)

        return None
