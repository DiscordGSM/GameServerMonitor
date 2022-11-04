import json
import os
import sqlite3
import sys
from argparse import ArgumentParser
from typing import Dict, List, Tuple

import psycopg2
from dotenv import load_dotenv

if __name__ == '__main__':
    from server import Server
else:
    from discordgsm.server import Server

load_dotenv()


def stringify(data: dict):
    """Dictionary to json string"""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


class Database:
    """Database with connection and cursor prepared"""

    def __init__(self):
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def connect(self):
        DB_CONNECTION = os.getenv('DB_CONNECTION', '')
        DATABASE_URL = os.getenv('DATABASE_URL', '')

        if DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://') or DB_CONNECTION == 'pgsql':
            self.type = 'pgsql'
            self.conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('POSTGRES_SSL_MODE', 'require'))
        else:
            self.type = 'sqlite'
            self.conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'servers.db'))

    def create_table_if_not_exists(self):
        cursor = self.conn.cursor()

        if self.type == 'pgsql':
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id BIGSERIAL PRIMARY KEY,
                position INT NOT NULL,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                message_id BIGINT,
                game_id TEXT NOT NULL,
                address TEXT NOT NULL,
                query_port INT NOT NULL,
                query_extra TEXT NOT NULL,
                status BOOLEAN NOT NULL,
                result TEXT NOT NULL,
                style_id TEXT NOT NULL,
                style_data TEXT NOT NULL
            )''')
        elif self.type == 'sqlite':
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
            )''')

        self.conn.commit()
        cursor.close()

    def close(self):
        self.conn.close()

    def transform(self, sql: str):
        if self.type == 'pgsql':
            return sql.replace('?', '%s').replace('IFNULL', 'COALESCE')

        return sql  # sqlite

    def statistics(self):
        sql = '''
        SELECT DISTINCT
            (SELECT COUNT(DISTINCT message_id) FROM servers) as messages,
            (SELECT COUNT(DISTINCT channel_id) FROM servers) as channels,
            (SELECT COUNT(DISTINCT guild_id) FROM servers) as guilds,
            (SELECT COUNT(*) FROM (SELECT DISTINCT game_id, address, query_port, query_extra FROM servers) x) as unique_servers
        FROM servers'''

        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql))
        row = cursor.fetchone()
        cursor.close()
        row = [0, 0, 0, 0] if row is None else row

        return {
            'messages': row[0],
            'channels': row[1],
            'guilds': row[2],
            'unique_servers': row[3],
        }

    def all_servers(self, channel_id: int = None, guild_id: int = None, message_id: int = None, filter_secret: bool = False):
        """Get all servers"""
        cursor = self.conn.cursor()

        if channel_id:
            cursor.execute(self.transform('SELECT * FROM servers WHERE channel_id = ? ORDER BY position'), (channel_id,))
        elif guild_id:
            cursor.execute(self.transform('SELECT * FROM servers WHERE guild_id = ? ORDER BY position'), (guild_id,))
        elif message_id:
            cursor.execute(self.transform('SELECT * FROM servers WHERE message_id = ? ORDER BY position'), (message_id,))
        else:
            cursor.execute('SELECT * FROM servers ORDER BY position')

        servers = [Server.from_list(row, filter_secret) for row in cursor.fetchall()]
        cursor.close()

        return servers

    def all_channels_servers(self, servers: List[Server] = None):
        """Convert or get servers to dict grouped by channel id"""
        all_servers = servers if servers is not None else self.all_servers()
        channels_servers: Dict[int, List[Server]] = {}

        for server in all_servers:
            if server.channel_id in channels_servers:
                channels_servers[server.channel_id].append(server)
            else:
                channels_servers[server.channel_id] = [server]

        return channels_servers

    def all_messages_servers(self, servers: List[Server] = None):
        """Convert or get servers to dict grouped by message id"""
        all_servers = servers if servers is not None else self.all_servers()
        messages_servers: Dict[int, List[Server]] = {}

        for server in all_servers:
            if server.message_id:
                if server.message_id in messages_servers:
                    messages_servers[server.message_id].append(server)
                else:
                    messages_servers[server.message_id] = [server]

        return messages_servers

    def distinct_servers(self):
        """Get distinct servers (Query server purpose) (Only fetch game_id, address, query_port, query_extra, status, result)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT game_id, address, query_port, query_extra, status, result FROM servers')
        servers = [Server.from_distinct_query(row) for row in cursor.fetchall()]
        cursor.close()

        return servers

    def add_server(self, s: Server):
        sql = '''
        INSERT INTO servers (position, guild_id, channel_id, game_id, address, query_port, query_extra, status, result, style_id, style_data)
        VALUES ((SELECT IFNULL(MAX(position + 1), 0) FROM servers WHERE channel_id = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

        try:
            cursor = self.conn.cursor()
            cursor.execute(self.transform(sql), (s.channel_id, s.guild_id, s.channel_id, s.game_id, s.address, s.query_port, stringify(s.query_extra), s.status, stringify(s.result), s.style_id, stringify(s.style_data)))
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

        return self.find_server(s.channel_id, s.address, s.query_port)

    def update_servers_message_id(self, servers: List[Server]):
        sql = 'UPDATE servers SET message_id = ? WHERE id = ?'
        parameters = [(server.message_id, server.id) for server in servers]
        cursor = self.conn.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.conn.commit()
        cursor.close()

    def update_servers(self, servers: List[Server]):
        """Update servers status and result"""
        parameters = [(server.status, stringify(server.result), server.game_id, server.address, server.query_port, stringify(server.query_extra)) for server in servers]
        sql = 'UPDATE servers SET status = ?, result = ? WHERE game_id = ? AND address = ? AND query_port = ? AND query_extra = ?'

        cursor = self.conn.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.conn.commit()
        cursor.close()

    def delete_server(self, server: Server):
        sql = 'DELETE FROM servers WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (server.id,))
        self.conn.commit()
        cursor.close()

    def factory_reset(self, guild_id: int):
        sql = 'DELETE FROM servers WHERE guild_id = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (guild_id,))
        self.conn.commit()
        cursor.close()

    def delete_servers(self, channel_id: int):
        sql = 'DELETE FROM servers WHERE channel_id = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (channel_id,))
        self.conn.commit()
        cursor.close()

    def find_server(self, channel_id: int, address: str = None, query_port: str = None, message_id: int = None):
        cursor = self.conn.cursor()

        if message_id is not None:
            sql = 'SELECT * FROM servers WHERE channel_id = ? AND message_id = ?'
            cursor.execute(self.transform(sql), (channel_id, message_id,))
        else:
            sql = 'SELECT * FROM servers WHERE channel_id = ? AND address = ? AND query_port = ?'
            cursor.execute(self.transform(sql), (channel_id, address, query_port))

        row = cursor.fetchone()
        cursor.close()

        if not row:
            raise self.ServerNotFoundError()

        return Server.from_list(row)

    def modify_server_position(self, server: Server, direction: bool):
        servers = self.all_servers(channel_id=server.channel_id)
        indices = [i for i, s in enumerate(servers) if s.id == server.id]

        if len(indices) <= 0 or (direction and indices[0] == 0) or (not direction and indices[0] == len(servers) - 1):
            return []

        return self.swap_servers_positon(server, servers[indices[0] + 1 * (-1 if direction else 1)])

    def swap_servers_positon(self, server1: Server, server2: Server):
        sql = 'UPDATE servers SET position = case when position = ? then ? else ? end, message_id = case when message_id = ? then ? else ? end WHERE id IN (?, ?)'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (server1.position, server2.position, server1.position, server1.message_id, server2.message_id, server1.message_id, server1.id, server2.id))
        self.conn.commit()
        cursor.close()

        server1.position, server2.position = server2.position, server1.position
        server1.message_id, server2.message_id = server2.message_id, server1.message_id

        return [server1, server2]

    def server_exists(self, channel_id: int, address: str, query_port: str):
        sql = 'SELECT id FROM servers WHERE channel_id = ? AND address = ? AND query_port = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (channel_id, address, query_port))
        exists = True if cursor.fetchone() else False
        cursor.close()

        return exists

    def update_server_style_id(self, server: Server):
        sql = 'UPDATE servers SET style_id = ? WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (server.style_id, server.id))
        self.conn.commit()
        cursor.close()

    def update_server_style_data(self, server: Server):
        sql = 'UPDATE servers SET style_data = ? WHERE id = ?'
        cursor = self.conn.cursor()
        cursor.execute(self.transform(sql), (stringify(server.style_data), server.id))
        self.conn.commit()
        cursor.close()

    def update_servers_style_data(self, servers: List[Server]):
        sql = 'UPDATE servers SET style_data = ? WHERE id = ?'
        parameters = [(stringify(server.style_data), server.id) for server in servers]
        cursor = self.conn.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.conn.commit()
        cursor.close()

    def update_servers_channel_id(self, servers: List[Server]):
        sql = 'UPDATE servers SET channel_id = ?, position = (SELECT IFNULL(MAX(position + 1), 0) FROM servers WHERE channel_id = ?) WHERE id = ?'
        parameters = [(server.channel_id, server.channel_id, server.id) for server in servers]
        cursor = self.conn.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.conn.commit()
        cursor.close()

    def export(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM servers')
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'servers.sql')

        def values_builder(row: Tuple):
            values = []

            for value in row:
                if value is None:
                    values.append('NULL')
                elif isinstance(value, str):
                    value = str(value).replace("'", "''")
                    values.append(f"'{value}'")
                else:
                    values.append(str(value))

            return ', '.join(values)

        with open(file, 'w', encoding='utf-8') as f:
            f.writelines([f'INSERT INTO servers VALUES ({values_builder(row)});\n' for row in cursor])

            if self.type == 'pgsql':
                # Sync the id sequence, fix postgresql duplicate key violates unique constraint
                f.write("SELECT SETVAL((SELECT PG_GET_SERIAL_SEQUENCE('\"servers\"', 'id')), (SELECT (MAX('id') + 1) FROM 'servers'), FALSE);\n")

        print(f'Exported to {os.path.abspath(file)}')

    class ServerNotFoundError(Exception):
        pass


if __name__ == '__main__':
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser_name')
    subparsers.add_parser('all')
    subparsers.add_parser('export')

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(-1)

    database = Database()

    if args.subparser_name == 'all':
        for server in database.all_servers():
            print(server)
    elif args.subparser_name == 'export':
        database.export()
