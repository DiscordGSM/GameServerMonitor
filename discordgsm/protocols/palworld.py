import base64
import time
from typing import TYPE_CHECKING

import aiohttp
from opengsq.protocol_socket import Socket

from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


class Palworld(Protocol):
    name = "palworld"

    def __init__(self):
        super().__init__()
        self.server_name = None  # Attribute to store the server name

    async def query(self, password: str):
        """Query Palworld server with REST API using Base64 authentication (username: 'admin')"""
        
        # Username is fixed as 'admin'
        username = 'admin'
        
        # Get host and port from the kv dictionary
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        
        # Resolve the host to an IP address
        ip = await Socket.gethostbyname(host)

        # Base64 encode 'admin:password' credentials
        credentials = f'{username}:{password}'
        encoded_credentials = base64.b64encode(credentials.encode('ascii'))

        # Build the URL to query the server info
        url = f"http://{ip}:{port}/v1/api/info"
        
        # Define request headers
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Accept': 'application/json'
        }

        # Log the start time for calculating ping
        start = time.time()

        # Query the server info using aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()  # Raise an error for non-2xx responses
                    data = await response.json()  # Parse the JSON response
                    ping = int((time.time() - start) * 1000)

                    # Extract and auto-fill the server name
                    self.server_name = data.get("servername", "Unknown Server")

                    # Force the status to 'online' if server name is present
                    if self.server_name and self.server_name != "Unknown Server":
                        status = "online"
                    else:
                        status = "offline"

                    # Return the server result
                    result: GamedigResult = {
                        "status": status,  # Force online status if server name is available
                        "name": self.server_name,  # Use the auto-filled server name
                        "version": data.get("version", "Unknown Version"),
                        "description": data.get("description", "No Description"),
                        "map": data.get("map_name", ""),
                        "password": data.get("is_password", False),
                        "numplayers": data.get("current_players", 0),
                        "numbots": 0,
                        "maxplayers": data.get("max_players", 0),
                        "players": None,
                        "bots": None,
                        "connect": f"{host}:{port}",
                        "ping": ping,
                        "raw": data,
                    }
                    return result
            except Exception as e:
                # Log and return the offline status if any exception occurs
                return {"status": "offline", "error": str(e)}
