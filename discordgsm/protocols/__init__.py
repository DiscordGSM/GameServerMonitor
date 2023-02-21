from .ase import ASE
from .assettocorsa import AssettoCorsa
from .battlefield import Battlefield
from .discord import Discord
from .doom3 import Doom3
from .fivem import FiveM
from .gamespy1 import GameSpy1
from .gamespy2 import GameSpy2
from .gamespy3 import GameSpy3
from .gportal import GPortal
from .hexen2 import Hexen2
from .minecraft import Minecraft
from .eco import Eco
from .quake1 import Quake1
from .quake2 import Quake2
from .quake3 import Quake3
from .raknet import Raknet
from .samp import Samp
from .scum import Scum
from .source import Source
from .teamspeak3 import Teamspeak3
from .terraria import Terraria
from .unreal2 import Unreal2
from .ut3 import UT3
from .vcmp import Vcmp
from .won import WON


class Protocols:
    @staticmethod
    def get(protocol_name: str, kv: dict):
        address, query_port = str(kv['host']), int(str(kv['port']))

        # match case statements only support on python 3.10
        # so if elif is used for python 3.8+ compatible
        if protocol_name == 'ase':
            return ASE(address, query_port)
        elif protocol_name == 'assettocorsa':
            return AssettoCorsa(address, query_port)
        elif protocol_name == 'battlefield':
            return Battlefield(address, query_port)
        elif protocol_name == 'discord':
            return Discord(address)
        elif protocol_name == 'doom3':
            return Doom3(address, query_port)
        elif protocol_name == 'eco':
            return Eco(address, query_port)
        elif protocol_name == 'gamespy1':
            return GameSpy1(address, query_port)
        elif protocol_name == 'gamespy2':
            return GameSpy2(address, query_port)
        elif protocol_name == 'gamespy3':
            return GameSpy3(address, query_port)
        elif protocol_name == 'gportal':
            return GPortal(address, query_port, str(kv['serverId']))
        elif protocol_name == 'hexen2':
            return Hexen2(address, query_port)
        elif protocol_name == 'minecraft':
            return Minecraft(address, query_port)
        elif protocol_name == 'fivem':
            return FiveM(address, query_port)
        elif protocol_name == 'quake1':
            return Quake1(address, query_port)
        elif protocol_name == 'quake2':
            return Quake2(address, query_port)
        elif protocol_name == 'quake3':
            return Quake3(address, query_port)
        elif protocol_name == 'raknet':
            return Raknet(address, query_port)
        elif protocol_name == 'samp':
            return Samp(address, query_port)
        elif protocol_name == 'scum':
            return Scum(address, query_port)
        elif protocol_name == 'source':
            return Source(address, query_port)
        elif protocol_name == 'unreal2':
            return Unreal2(address, query_port)
        elif protocol_name == 'teamspeak3':
            return Teamspeak3(address, int(str(kv['teamspeakQueryPort'])), query_port)
        elif protocol_name == 'terraria':
            return Terraria(address, query_port, str(kv['_token']))
        elif protocol_name == 'ut3':
            return UT3(address, query_port)
        elif protocol_name == 'vcmp':
            return Vcmp(address, query_port)
        elif protocol_name == 'won':
            return WON(address, query_port)

        return None
