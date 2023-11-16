# flake8: noqa
from .asa import ASA
from .ase import ASE
from .assettocorsa import AssettoCorsa
from .battlefield import Battlefield
from .beammp import BeamMP
from .discord import Discord
from .doom3 import Doom3
from .eco import Eco
from .factorio import Factorio
from .fivem import FiveM
from .front import Front
from .gamespy1 import GameSpy1
from .gamespy2 import GameSpy2
from .gamespy3 import GameSpy3
from .gportal import GPortal
from .hexen2 import Hexen2
from .minecraft import Minecraft
from .nwn1 import NWN1
from .nwn2 import NWN2
from .protocol import Protocol
from .quake1 import Quake1
from .quake2 import Quake2
from .quake3 import Quake3
from .raknet import Raknet
from .samp import Samp
from .satisfactory import Satisfactory
from .scum import Scum
from .source import Source
from .teamspeak3 import Teamspeak3
from .terraria import Terraria
from .unreal2 import Unreal2
from .ut3 import UT3
from .vcmp import Vcmp
from .won import WON

protocols = {str(protocol.name): protocol for protocol in Protocol.__subclasses__()}
