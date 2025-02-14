import sqlite3
import json
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import os
from pathlib import Path
import argparse
import sys

VALID_STYLES = ['ExtraSmall', 'Small', 'Medium', 'Large', 'ExtraLarge']

@dataclass
class StyleConfig:
    style_id: str = "Medium"
    description: str = ""
    fullname: str = ""
    image_url: str = ""
    thumbnail_url: str = ""
    country: str = ""
    locale: str = "en-US"
    timezone: str = "UTC"
    clock_format: str = "12"

@dataclass
class ServerConfig:
    guild_id: int
    channel_id: int
    game_id: str
    address: str
    query_port: int
    style_config: StyleConfig = None
    query_extra: Dict = None
    status: bool = False
    result: Dict = None
    message_id: Optional[int] = None
    position: Optional[int] = None

    @staticmethod
    def process_auth_params(game_id: str, auth_params: Dict) -> Dict:
        query_extra = {}
        if game_id == "terraria" and "token" in auth_params:
            query_extra["_token"] = auth_params["token"]
        elif game_id == "scpsl" and all(k in auth_params for k in ["account_id", "api_key"]):
            query_extra["_api_key"] = auth_params["api_key"]
            return {"address": auth_params["account_id"], "query_port": 0, "query_extra": query_extra}
        elif game_id == "gportal" and "server_id" in auth_params:
            query_extra["serverId"] = auth_params["server_id"]
        elif game_id == "teamspeak3" and "voice_port" in auth_params:
            query_extra["voice_port"] = auth_params["voice_port"]
        elif game_id == "tmnf" and all(k in auth_params for k in ["username", "password"]):
            query_extra.update({
                "username": auth_params["username"],
                "password": auth_params["password"]
            })
        return {"query_extra": query_extra} if query_extra else {}

class DGSMAutomation:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(Path(__file__).parent, "data", "servers.db")
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position INT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message_id BIGINT,
                    game_id TEXT NOT NULL,
                    address TEXT NOT NULL,
                    query_port INT(5) NOT NULL,
                    query_extra TEXT NOT NULL,
                    status INT(1) NOT NULL,
                    result TEXT NOT NULL,
                    style_id TEXT NOT NULL,
                    style_data TEXT NOT NULL
                )
            ''')
            conn.commit()

    def server_exists(self, address: str, query_port: int) -> Tuple[bool, Optional[Dict]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT channel_id, game_id FROM servers WHERE address = ? AND query_port = ?',
                (address, query_port)
            )
            result = cursor.fetchone()
            if result:
                return True, {
                    'channel_id': result[0],
                    'game_id': result[1]
                }
            return False, None

    def add_server(self, config: ServerConfig) -> Tuple[bool, str]:
        try:
            exists, existing_data = self.server_exists(config.address, config.query_port)
            if exists:
                return False, f"Server {config.address}:{config.query_port} already exists in channel {existing_data['channel_id']} for game {existing_data['game_id']}"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if config.position is None:
                    cursor.execute(
                        'SELECT COALESCE(MAX(position + 1), 0) FROM servers WHERE channel_id = ?', 
                        (config.channel_id,)
                    )
                    config.position = cursor.fetchone()[0]

                config.query_extra = config.query_extra or {}
                
                # Prepare style data
                style_config = config.style_config or StyleConfig()
                style_data = {
                    "description": style_config.description,
                    "fullname": style_config.fullname,
                    "image_url": style_config.image_url,
                    "thumbnail_url": style_config.thumbnail_url,
                    "locale": style_config.locale,
                    "timezone": style_config.timezone,
                    "clock_format": style_config.clock_format
                }
                if style_config.country:
                    style_data["country"] = style_config.country

                # Default result structure
                config.result = config.result or {
                    "name": "", 
                    "map": "", 
                    "password": False,
                    "raw": {},
                    "connect": "",
                    "numplayers": 0,
                    "numbots": 0,
                    "maxplayers": 0,
                    "players": [],
                    "bots": []
                }

                cursor.execute('''
                    INSERT INTO servers (
                        position, guild_id, channel_id, game_id, address, query_port,
                        query_extra, status, result, style_id, style_data, message_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    config.position,
                    config.guild_id,
                    config.channel_id,
                    config.game_id,
                    config.address,
                    config.query_port,
                    json.dumps(config.query_extra),
                    int(config.status),
                    json.dumps(config.result),
                    style_config.style_id,
                    json.dumps(style_data),
                    config.message_id
                ))
                conn.commit()
                return True, f"Successfully added server {config.address}:{config.query_port}"

        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Add server to DiscordGSM')
    parser.add_argument('--guild_id', type=int, required=True)
    parser.add_argument('--channel_id', type=int, required=True)
    parser.add_argument('--game_id', type=str, required=True)
    parser.add_argument('--address', type=str, required=True)
    parser.add_argument('--query_port', type=int, required=True)
    parser.add_argument('--db_path', type=str, help='Path to servers.db')
    parser.add_argument('--ignore-existing', action='store_true', help='Continue if server exists')
    
    # Style configuration
    parser.add_argument('--style', choices=VALID_STYLES, default='Medium', help='Message style')
    parser.add_argument('--description', type=str, help='Server description')
    parser.add_argument('--fullname', type=str, help='Game full name')
    parser.add_argument('--image_url', type=str, help='Embed image URL')
    parser.add_argument('--thumbnail_url', type=str, help='Embed thumbnail URL')
    parser.add_argument('--country', type=str, help='Server country (Medium style)')
    parser.add_argument('--locale', type=str, default='en-US', help='Locale for translations')
    parser.add_argument('--timezone', type=str, default='UTC', help='Timezone for timestamps')
    parser.add_argument('--clock_format', choices=['12', '24'], default='12', help='Clock format')
    
    # Authentication parameters
    parser.add_argument('--token', help='REST token for Terraria')
    parser.add_argument('--account_id', help='Account ID for SCPSL')
    parser.add_argument('--api_key', help='API key for SCPSL')
    parser.add_argument('--server_id', help='Server ID for GPortal')
    parser.add_argument('--voice_port', type=int, help='Voice port for TeamSpeak3')
    parser.add_argument('--username', help='Query username for TMNF')
    parser.add_argument('--password', help='Query password for TMNF')
    
    args = parser.parse_args()
    
    try:
        automation = DGSMAutomation(db_path=args.db_path)
        
        # Process authentication parameters
        auth_params = {k: v for k, v in vars(args).items() if k in [
            'token', 'account_id', 'api_key', 'server_id', 
            'voice_port', 'username', 'password'
        ] and v is not None}
        
        config_updates = ServerConfig.process_auth_params(args.game_id, auth_params)
        
        # Create style configuration
        style_config = StyleConfig(
            style_id=args.style,
            description=args.description or "",
            fullname=args.fullname or "",
            image_url=args.image_url or "",
            thumbnail_url=args.thumbnail_url or "",
            country=args.country or "",
            locale=args.locale,
            timezone=args.timezone,
            clock_format=args.clock_format
        )

        server_config = ServerConfig(
            guild_id=args.guild_id,
            channel_id=args.channel_id,
            game_id=args.game_id,
            address=config_updates.get('address', args.address),
            query_port=config_updates.get('query_port', args.query_port),
            query_extra=config_updates.get('query_extra', {}),
            style_config=style_config
        )
        
        success, message = automation.add_server(server_config)
        print(message)
        
        if not success and not args.ignore_existing:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()