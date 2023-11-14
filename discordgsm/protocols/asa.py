from discordgsm.protocols.protocol import Protocol
import requests
import base64

class Asa(Protocol):
    name = 'asa'

    def __init__(self, kv):
        super().__init__(kv)
        self.client_id = 'xyza7891muomRmynIIHaJB9COBKkwj6n'
        self.client_secret = 'PP5UGxysEieNfSrEicaD1N2Bb3TdXuD7xHYcsdUHZ7s'
        self.deployment_id = 'ad9a8feffb3b4b2ca315546f038c3ae2'
        self.epic_api = 'https://api.epicgames.dev'

    async def query(self):
        host, port = str(self.kv['host']), int(str(self.kv['port']))
        try:
            access_token = self.get_access_token()
            server_info = self.query_server_info(access_token, host, port)

            sessions = server_info.get('sessions', [])
            if not sessions:
                raise Exception("No sessions found")

            desired_session = sessions[0]

            attributes = desired_session.get('attributes', {})
            settings = desired_session.get('settings', {})

            result = {
                'name': attributes.get('CUSTOMSERVERNAME_s', 'Unknown Server'),
                'map': attributes.get('MAPNAME_s', 'Unknown Map'),
                'password': attributes.get('SERVERPASSWORD_b', False),
                'numplayers': desired_session.get('totalPlayers', 0),
                'maxplayers': settings.get('maxPublicPlayers', 0),
                'players': [],
                'bots': [],
                'connect': attributes.get('ADDRESS_s', '') + ':' + str(port),
                'ping': 0,
                'raw': desired_session
            }
        except Exception as e:
            result = {
                'raw': {'error': str(e)},
                'name': 'Unknown Server',
                'map': 'Unknown Map',
                'password': False,
                'numplayers': 0,
                'maxplayers': 0,
                'players': [],
                'bots': [],
                'connect': f"{host}:{port}",
                'ping': 0
            }

        return result

    def get_access_token(self):
        url = f"{self.epic_api}/auth/v1/oauth/token"
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = f"grant_type=client_credentials&deployment_id={self.deployment_id}"
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        return response.json()['access_token']

    def query_server_info(self, access_token, host, port):
        url = f"{self.epic_api}/matchmaking/v1/{self.deployment_id}/filter"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        body = {
            "criteria": [
                {"key": "attributes.ADDRESS_s", "op": "EQUAL", "value": host},
                {"key": "attributes.ADDRESSBOUND_s", "op": "EQUAL", "value": f"0.0.0.0:{port}"}
            ]
        }
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
