import sqlite3
import json
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import os
from pathlib import Path
import argparse
import sys

@dataclass
class ServerConfig:
    guild_id: int
    channel_id: int
    game_id: str
    address: str
    query_port: int
    query_extra: Dict = None
    style_id: str = "Medium"
    style_data: Dict = None
    position: Optional[int] = None
    status: bool = False
    result: Dict = None
    message_id: Optional[int] = None

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
                config.style_data = config.style_data or {"locale": "en-US", "timezone": "UTC"}
                config.result = config.result or {"name": "", "map": "", "password": False, "raw": {}, "connect": "", "numplayers": 0, "numbots": 0, "maxplayers": 0, "players": [], "bots": []}

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
                    config.style_id,
                    json.dumps(config.style_data),
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
    
    args = parser.parse_args()
    
    try:
        automation = DGSMAutomation(db_path=args.db_path)
        
        server_config = ServerConfig(
            guild_id=args.guild_id,
            channel_id=args.channel_id,
            game_id=args.game_id,
            address=args.address,
            query_port=args.query_port
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