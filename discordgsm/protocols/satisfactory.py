import time
from typing import TYPE_CHECKING

import socket
import struct
import requests
import warnings
import urllib3

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Satisfactory(Protocol):
    name = "satisfactory"

    async def query(self):
        host, port, app_token = str(self.kv["host"]), int(str(self.kv["port"])), str(self.kv["_token"])
        
        # Generate a unique cookie using the current time (in ticks)
        cookie = int(time.time() * 1000)
        
        # Construct the request packet
        request = struct.pack('<HBBQb', 0xF6D5, 0, 1, cookie, 1)
        
        # Send the Poll Server State request via UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        
        try:
            start = time.time()
            sock.sendto(request, (host, port))
            # Expecting a response of up to 1024 bytes
            response, _ = sock.recvfrom(1024)
            ping = int((time.time() - start) * 1000)
        except socket.timeout:
            return None
        finally:
            sock.close()
        
        # Unpack the response message
        protocol_magic, _, _, received_cookie, server_state, server_netcl, server_flags, num_substates = struct.unpack('<HBBQBLQB', response[:26])
        
        if protocol_magic != 0xF6D5 or received_cookie != cookie:
            return None
        
        # Extract server name length and server name
        server_name_length = struct.unpack('<H', response[26+(num_substates*3):28+(num_substates*3)])[0]
        server_name = response[28+(num_substates*3):28+(num_substates*3) + server_name_length].decode('utf-8')
        
        # Extract max number of players and number of players
        if server_state == 3:
            
            headers = {
                'Authorization': f'Bearer {app_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "function":"QueryServerState",
                "data":{
                    "ServerGameState":{}
                }
            }
            
            try:
                warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
                response = requests.post(f'https://{host}:{port}/api/v1/', verify=False, json=data, headers=headers)
                
                # Raise an exception for HTTP errors
                response.raise_for_status()
                server_game_state = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error querying server state: {e}")
                return None
            
            server_max_nb_players, server_cur_nb_players = server_game_state.get('data', {}).get('serverGameState', {}).get('playerLimit', 'Not Available'), server_game_state.get('data', {}).get('serverGameState', {}).get('numConnectedPlayers', 'Not Available')
            
        else:
            server_max_nb_players, server_cur_nb_players = 0, 0
        
        result: GamedigResult = {
            "name": server_name,
            "map": "",
            "password": False,
            "numplayers": server_cur_nb_players,
            "numbots": 0,
            "maxplayers": server_max_nb_players,
            "players": None,
            "bots": None,
            "connect": f"{host}:{port}",
            "ping": ping,
            "raw": server_game_state,
        }
        
        return result
