import asyncio
import time
from typing import TYPE_CHECKING

import opengsq

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Teamspeak3(Protocol):
    name = 'teamspeak3'

    async def query(self):
        if 'teamspeakQueryPort' in self.kv:  # backward compatibility
            host, port, voice_port = str(self.kv['host']), int(str(self.kv['teamspeakQueryPort'])), int(str(self.kv['port']))
        else:
            host, port, voice_port = str(self.kv['host']), int(str(self.kv['port'])), int(str(self.kv['voice_port']))

        teamspeak3 = opengsq.Teamspeak3(host, port, voice_port, self.timeout)
        start = time.time()
        info, clients, channels = await asyncio.gather(teamspeak3.get_info(), teamspeak3.get_clients(), teamspeak3.get_channels())
        ping = int((time.time() - start) * 1000)
        players = [{'name': player['client_nickname'], 'raw': player} for player in clients if player.get('client_type') == '0']

        result: GamedigResult = {
            'name': info.get('virtualserver_name', ''),
            'map': '',
            'password': int(info.get('virtualserver_flag_password', '0')) == 1,
            'numplayers': len(players),
            'numbots': 0,
            'maxplayers': int(info.get('virtualserver_maxclients', '0')),
            'players': players,
            'bots': None,
            'connect': f'{host}:{voice_port}',
            'ping': ping,
            'raw': {
                'info': info,
                'channels': channels
            }
        }

        return result
