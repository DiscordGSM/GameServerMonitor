from __future__ import annotations
from datetime import datetime

from enum import Enum

import json
import os
from pathlib import Path
import sqlite3
import sys
from argparse import ArgumentParser
import time

from pymongo import DeleteOne, MongoClient, UpdateMany, UpdateOne
import psycopg2
import psycopg2.pool
from psycopg2.extensions import connection
from dotenv import load_dotenv


if __name__ == '__main__':
    from server import Server
    from server import QueryServer
    from async_utils import run_in_executor
else:
    from discordgsm.server import Server
    from discordgsm.server import QueryServer
    from discordgsm.async_utils import run_in_executor

load_dotenv()


def stringify(data: dict):
    """Dictionary to json string"""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


class Driver(Enum):
    SQLite = 'sqlite'
    PostgreSQL = 'pgsql'
    MongoDB = 'mongodb'


drivers = [driver.value for driver in Driver]


class InvalidDriverError(Exception):
    pass


class Database:
    """Database with connection and cursor prepared"""

    def __init__(self):
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.dispose()

    def connect(self):
        DB_CONNECTION: str = os.getenv('DB_CONNECTION', 'sqlite')
        DATABASE_URL: str = os.getenv('DATABASE_URL', '')

        if DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://') or DB_CONNECTION == Driver.PostgreSQL.value:
            self.driver = Driver.PostgreSQL
            self.pool = self.__connect_psycopg2(DATABASE_URL)
        elif DB_CONNECTION == Driver.MongoDB.value:
            self.driver = Driver.MongoDB
            self.conn = MongoClient(DATABASE_URL)
            self.servers = self.conn.get_default_database()['servers']
            self.metrics = self.conn.get_default_database()['metrics']
        else:
            self.driver = Driver.SQLite
            self.database = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), '..', 'data', 'servers.db')

    def __connect_psycopg2(self, database_url: str, max_retries=3):
        retries = 0
        sslmode = os.getenv('POSTGRES_SSL_MODE', 'require')

        while True:
            time.sleep(1)

            try:
                pool = psycopg2.pool.ThreadedConnectionPool(
                    1, 10, database_url, sslmode=sslmode)
                return pool
            except psycopg2.OperationalError as e:
                if retries >= max_retries:
                    raise e

                retries += 1
                print(
                    f"Connection failed. Retry attempt {retries}/{max_retries}. Retrying in 1 second...")

    def create_table_if_not_exists(self):
        if self.driver == Driver.MongoDB:
            return

        conn, cursor = self.cursor()

        if self.driver == Driver.PostgreSQL:
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
        elif self.driver == Driver.SQLite:
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

        self.close(conn, cursor, commit=True)

    def dispose(self):
        if self.driver == Driver.PostgreSQL:
            self.pool.closeall()
        elif self.driver == Driver.MongoDB:
            self.conn.close()

    def cursor(self):
        if self.driver == Driver.PostgreSQL:
            try:
                conn: connection = self.pool.getconn()

                # Fix the issue so many ROLLBACKs
                # The connection pool issues connection.rollback() when a connection is returned.
                # https://docs.sqlalchemy.org/en/14/faq/connections.html#why-does-sqlalchemy-issue-so-many-rollbacks
                conn.autocommit = True

                cursor = conn.cursor()
            except psycopg2.InterfaceError:  # connection already closed
                # Reconnect
                self.connect()
                conn = self.pool.getconn()
                cursor = conn.cursor()

            return conn, cursor
        else:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            return conn, cursor

    def close(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor, *, commit=False):
        cursor.close()

        if self.driver == Driver.PostgreSQL:
            self.pool.putconn(conn)
        else:
            if commit:
                conn.commit()

            conn.close()

    def transform(self, sql: str):
        if self.driver == Driver.PostgreSQL:
            return sql.replace('?', '%s').replace('IFNULL', 'COALESCE')

        return sql  # sqlite

    @run_in_executor
    def statistics(self):
        if self.driver == Driver.MongoDB:
            messages = len(self.servers.distinct("message_id"))
            channels = len(self.servers.distinct("channel_id"))
            guilds = len(self.servers.distinct("guild_id"))

            pipeline = [
                {"$group": {
                    "_id": {
                        "game_id": "$game_id",
                        "address": "$address",
                        "query_port": "$query_port",
                        "query_extra": "$query_extra"
                    }
                }}
            ]
            unique_servers = len(list(self.servers.aggregate(pipeline)))

            return {
                'messages': messages,
                'channels': channels,
                'guilds': guilds,
                'unique_servers': unique_servers,
            }

        sql = '''
        SELECT DISTINCT
            (SELECT COUNT(DISTINCT message_id) FROM servers) as messages,
            (SELECT COUNT(DISTINCT channel_id) FROM servers) as channels,
            (SELECT COUNT(DISTINCT guild_id) FROM servers) as guilds,
            (SELECT COUNT(*) FROM (SELECT DISTINCT game_id, address, query_port, query_extra FROM servers) x) as unique_servers
        FROM servers'''

        conn, cursor = self.cursor()
        cursor.execute(self.transform(sql))
        row: tuple[int] = cursor.fetchone()
        self.close(conn, cursor)
        row = [0, 0, 0, 0] if row is None else row

        return {
            'messages': row[0],
            'channels': row[1],
            'guilds': row[2],
            'unique_servers': row[3],
        }

    @run_in_executor
    def count_servers_per_game(self):
        if self.driver == Driver.MongoDB:
            pipeline = [
                {"$group": {"_id": "$game_id", "count": {"$sum": 1}}}
            ]
            results = self.servers.aggregate(pipeline)
            servers_count = {str(row['_id']): int(row['count'])
                             for row in results}
            results.close()
            return servers_count

        conn, cursor = self.cursor()
        cursor.execute(self.transform(
            'SELECT game_id, COUNT(*) FROM servers GROUP BY game_id'))
        servers_count = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        self.close(conn, cursor)

        return servers_count

    @run_in_executor
    def count_servers_per_channel(self):
        if self.driver == Driver.MongoDB:
            pipeline = [
                {"$group": {"_id": "$channel_id", "count": {"$sum": 1}}}
            ]
            results = self.servers.aggregate(pipeline)
            servers_count = {str(row['_id']): int(row['count'])
                             for row in results}
            results.close()
            return servers_count

        conn, cursor = self.cursor()
        cursor.execute(self.transform(
            'SELECT channel_id, COUNT(*) FROM servers GROUP BY channel_id'))
        servers_count = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        self.close(conn, cursor)

        return servers_count

    @run_in_executor
    def all_servers(self, *, channel_id: int = None, guild_id: int = None, message_id: int = None, game_id: str = None, filter_secret=False):
        return self.__all_servers(channel_id=channel_id, guild_id=guild_id, message_id=message_id, game_id=game_id, filter_secret=filter_secret)

    def __all_servers(self, *, channel_id: int = None, guild_id: int = None, message_id: int = None, game_id: str = None, filter_secret=False):
        """Get all servers"""
        if self.driver == Driver.MongoDB:
            if channel_id:
                results = self.servers.find(
                    {"channel_id": channel_id}).sort("position")
            elif guild_id:
                results = self.servers.find(
                    {"guild_id": guild_id}).sort("position")
            elif message_id:
                results = self.servers.find(
                    {"message_id": message_id}).sort("position")
            elif game_id:
                results = self.servers.find(
                    {"game_id": game_id}).sort("position")
            else:
                results = self.servers.find({}).sort("position")

            servers = [Server.from_docs(doc, filter_secret) for doc in results]
            results.close()

            return servers

        conn, cursor = self.cursor()

        if channel_id:
            cursor.execute(self.transform(
                'SELECT * FROM servers WHERE channel_id = ? ORDER BY position'), (channel_id,))
        elif guild_id:
            cursor.execute(self.transform(
                'SELECT * FROM servers WHERE guild_id = ? ORDER BY position'), (guild_id,))
        elif message_id:
            cursor.execute(self.transform(
                'SELECT * FROM servers WHERE message_id = ? ORDER BY position'), (message_id,))
        elif game_id:
            cursor.execute(self.transform(
                'SELECT * FROM servers WHERE game_id = ? ORDER BY id'), (game_id,))
        else:
            cursor.execute('SELECT * FROM servers ORDER BY position')

        servers = [Server.from_list(row, filter_secret)
                   for row in cursor.fetchall()]
        self.close(conn, cursor)

        return servers

    @run_in_executor
    def distinct_servers(self):
        """Get distinct servers (Query server purpose) (Only fetch game_id, address, query_port, query_extra, status, result)"""
        if self.driver == Driver.MongoDB:
            pipeline = [
                {"$group": {
                    "_id": {
                        "game_id": "$game_id",
                        "address": "$address",
                        "query_port": "$query_port",
                        "query_extra": "$query_extra",
                        "status": "$status",
                        "result": "$result"
                    }
                }}
            ]
            results = self.servers.aggregate(pipeline)
            servers = [QueryServer(**row['_id']) for row in results]
            results.close()
            return servers

        conn, cursor = self.cursor()
        cursor.execute(
            'SELECT DISTINCT game_id, address, query_port, query_extra, status, result FROM servers')
        servers = [QueryServer.create(row) for row in cursor.fetchall()]
        self.close(conn, cursor)

        return servers

    def server_limit(self, s: Server):
        if self.driver == Driver.MongoDB:
            pipeline = [
                {"$group": {
                    "_id": {
                        "game_id": "$game_id",
                        "address": "$address",
                        "query_port": "$query_port",
                        "query_extra": "$query_extra",
                        "status": "$status",
                        "result": "$result"
                    }
                }}
            ]

        return int(os.getenv('APP_PUBLIC_SERVER_LIMIT', '10'))

    @run_in_executor
    def add_server(self, s: Server):
        if self.driver == Driver.MongoDB:
            try:
                max_position = self.servers.find_one({'channel_id': s.channel_id}, sort=[
                    ('position', -1)])["position"]
            except TypeError:
                max_position = 0

            self.servers.insert_one({
                "position": max_position + 1,
                "guild_id": s.guild_id,
                "channel_id": s.channel_id,
                "game_id": s.game_id,
                "address": s.address,
                "query_port": s.query_port,
                "query_extra": s.query_extra,
                "status": s.status,
                "result": s.result,
                "style_id": s.style_id,
                "style_data": s.style_data
            })

            return self.__find_server(s.channel_id, s.address, s.query_port)

        sql = '''
        INSERT INTO servers (position, guild_id, channel_id, game_id, address, query_port, query_extra, status, result, style_id, style_data)
        VALUES ((SELECT IFNULL(MAX(position + 1), 0) FROM servers WHERE channel_id = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

        conn, cursor = self.cursor()
        cursor.execute(self.transform(sql), (s.channel_id, s.guild_id, s.channel_id, s.game_id, s.address, s.query_port, stringify(
            s.query_extra), s.status, stringify(s.result), s.style_id, stringify(s.style_data)))
        self.close(conn, cursor, commit=True)

        return self.__find_server(s.channel_id, s.address, s.query_port)

    @run_in_executor
    def update_servers_message_id(self, servers: list[Server]):
        if self.driver == Driver.MongoDB:
            operations = [
                UpdateOne(
                    {"_id": server.id},
                    {"$set": {"message_id": server.message_id}}
                ) for server in servers
            ]

            if operations:
                self.servers.bulk_write(operations)

            return

        sql = 'UPDATE servers SET message_id = ? WHERE id = ?'
        parameters = [(server.message_id, server.id) for server in servers]
        conn, cursor = self.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.close(conn, cursor, commit=True)

    @run_in_executor
    def update_servers(self, servers: list[Server], *, channel_id: int = None):
        if channel_id is not None:
            return self.__update_servers_channel_id(servers, channel_id)

        """Update servers status and result"""
        if self.driver == Driver.MongoDB:
            operations = [
                UpdateMany(
                    {"game_id": server.game_id, "address": server.address,
                        "query_port": server.query_port, "query_extra": server.query_extra},
                    {"$set": {"status": server.status, "result": server.result}}
                ) for server in servers
            ]

            if operations:
                self.servers.bulk_write(operations)

            return

        parameters = [(server.status, stringify(server.result), server.game_id, server.address,
                       server.query_port, stringify(server.query_extra)) for server in servers]
        sql = 'UPDATE servers SET status = ?, result = ? WHERE game_id = ? AND address = ? AND query_port = ? AND query_extra = ?'
        conn, cursor = self.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.close(conn, cursor, commit=True)

    @run_in_executor
    def update_metrics(self, servers: list[Server]):
        if self.driver == Driver.MongoDB:
            if os.getenv('METRICS_ENABLE', '').lower() == 'true':
                limit = int(os.getenv('METRICS_RECORD_LIMIT', '1000'))

                operations = [
                    UpdateOne({
                        "game_id": server.game_id,
                        "address": server.address,
                        "query_port": server.query_port,
                        "query_extra": server.query_extra
                    }, {
                        "$push": {
                            "records": {
                                "$each": [{
                                    "s": server.status,
                                    "p": server.result["numplayers"],
                                    "b": server.result["numbots"],
                                    "m": server.result["maxplayers"],
                                    "c": datetime.utcnow(),
                                }],
                                "$slice": limit * -1
                            }
                        }
                    }, upsert=True) for server in servers
                ]

                if operations:
                    self.metrics.bulk_write(operations)

    @run_in_executor
    def delete_servers(self, *, guild_id: int = None, channel_id: int = None, servers: list[Server] = None):
        if guild_id is None and channel_id is None and servers is None:
            return

        if self.driver == Driver.MongoDB:
            if guild_id is not None:
                self.servers.delete_many({"guild_id": guild_id})
            elif channel_id is not None:
                self.servers.delete_many({"channel_id": channel_id})
            elif servers is not None:
                operations = [DeleteOne({"_id": server.id})
                              for server in servers]

                if operations:
                    self.servers.bulk_write(operations)
        else:
            conn, cursor = self.cursor()

            if guild_id is not None:
                sql = 'DELETE FROM servers WHERE guild_id = ?'
                cursor.execute(self.transform(sql), (guild_id,))
            elif channel_id is not None:
                sql = 'DELETE FROM servers WHERE channel_id = ?'
                cursor.execute(self.transform(sql), (channel_id,))
            elif servers is not None:
                sql = 'DELETE FROM servers WHERE id = ?'
                parameters = [(server.id,) for server in servers]
                cursor.executemany(self.transform(sql), parameters)

            self.close(conn, cursor, commit=True)

    @run_in_executor
    def find_server(self, channel_id: int, address: str = None, query_port: int = None):
        return self.__find_server(channel_id=channel_id, address=address, query_port=query_port)

    def __find_server(self, channel_id: int, address: str = None, query_port: int = None):
        if self.driver == Driver.MongoDB:
            result = self.servers.find_one(
                {"channel_id": channel_id, "address": address, "query_port": query_port})

            if not result:
                raise self.ServerNotFoundError()

            return Server.from_docs(result)

        conn, cursor = self.cursor()

        sql = 'SELECT * FROM servers WHERE channel_id = ? AND address = ? AND query_port = ?'
        cursor.execute(self.transform(
            sql), (channel_id, address, query_port))

        row = cursor.fetchone()
        self.close(conn, cursor)

        if not row:
            raise self.ServerNotFoundError()

        return Server.from_list(row)

    @run_in_executor
    def modify_server_position(self, server1: Server, direction: bool):
        servers = self.__all_servers(channel_id=server1.channel_id)
        indices = [i for i, s in enumerate(servers) if s.id == server1.id]

        # Ignore when the position is the most top and bottom
        if len(indices) <= 0 or (direction and indices[0] == 0) or (not direction and indices[0] == len(servers) - 1):
            return []

        server2 = servers[indices[0] + 1 * (-1 if direction else 1)]

        # Ignore when message id is NULL
        if server1.message_id is None or server2.message_id is None:
            return []

        return self.__swap_servers_positon(server1, server2)

    def __swap_servers_positon(self, server1: Server, server2: Server):
        if self.driver == Driver.MongoDB:
            # Update server1's position and message_id to server2's values
            self.servers.update_one({"_id": server1.id}, {
                "$set": {"position": server2.position, "message_id": server2.message_id}})

            # Update server2's position and message_id to the original server1's values
            self.servers.update_one({"_id": server2.id}, {
                "$set": {"position": server1.position, "message_id": server1.message_id}})
        else:
            sql = 'UPDATE servers SET position = case when position = ? then ? else ? end, message_id = case when message_id = ? then ? else ? end WHERE id IN (?, ?)'
            conn, cursor = self.cursor()
            cursor.execute(self.transform(sql), (server1.position, server2.position, server1.position,
                                                 server1.message_id, server2.message_id, server1.message_id, server1.id, server2.id))
            self.close(conn, cursor, commit=True)

        # Swap the position and message_id values in the server objects
        server1.position, server2.position = server2.position, server1.position
        server1.message_id, server2.message_id = server2.message_id, server1.message_id

        return [server1, server2]

    @run_in_executor
    def update_server_style_id(self, server: Server):
        if self.driver == Driver.MongoDB:
            self.servers.update_one(
                {"_id": server.id}, {"$set": {"style_id": server.style_id}})
            return

        sql = 'UPDATE servers SET style_id = ? WHERE id = ?'
        conn, cursor = self.cursor()
        cursor.execute(self.transform(sql), (server.style_id, server.id))
        self.close(conn, cursor, commit=True)

    @run_in_executor
    def update_servers_style_data(self, servers: list[Server]):
        if self.driver == Driver.MongoDB:
            if operations := [
                UpdateOne(
                    {"_id": server.id},
                    {"$set": {"style_data": server.style_data}}
                ) for server in servers
            ]:
                self.servers.bulk_write(operations)

            return

        sql = 'UPDATE servers SET style_data = ? WHERE id = ?'
        parameters = [(stringify(server.style_data), server.id)
                      for server in servers]
        conn, cursor = self.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.close(conn, cursor, commit=True)

    def __update_servers_channel_id(self, servers: list[Server], channel_id: int):
        if self.driver == Driver.MongoDB:
            try:
                max_position = self.servers.find_one({'channel_id': channel_id}, sort=[
                    ('position', -1)])["position"]
            except TypeError:
                max_position = 0

            operations = []

            for server in servers:
                max_position += 1

                operations.append(
                    UpdateOne(
                        {"_id": server.id},
                        {"$set": {"channel_id": channel_id, "position": max_position}}
                    )
                )

            if operations:
                self.servers.bulk_write(operations)

            return

        sql = 'UPDATE servers SET channel_id = ?, position = (SELECT IFNULL(MAX(position + 1), 0) FROM servers WHERE channel_id = ?) WHERE id = ?'
        parameters = [(channel_id, channel_id, server.id)
                      for server in servers]
        conn, cursor = self.cursor()
        cursor.executemany(self.transform(sql), parameters)
        self.close(conn, cursor, commit=True)

    def export(self, *, to_driver: str):
        if to_driver not in drivers:
            raise InvalidDriverError(
                f"'{to_driver}' is not a valid driver. Valid drivers are: {', '.join(drivers)}")

        export_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), '..', 'data', 'exports')
        Path(export_path).mkdir(parents=True, exist_ok=True)

        if to_driver == Driver.MongoDB.value:
            servers = self.__all_servers()
            documents = [server.__dict__ for server in servers]
            documents = [{k: v for k, v in doc.items() if k != 'id'}
                         for doc in documents]
            file = os.path.join(export_path, 'servers.json')

            with open(file, 'w', encoding='utf-8') as f:
                json.dump(documents, f, indent=2)
        else:
            file = os.path.join(export_path, 'servers.sql')

            if self.driver == Driver.SQLite:
                # Export data to SQL file
                with open(file, 'w', encoding='utf-8') as f:
                    conn, _ = self.cursor()

                    for line in conn.iterdump():
                        f.write('%s\n' % line)
            elif self.driver == Driver.PostgreSQL:
                DATABASE_URL: str = os.getenv('DATABASE_URL', '')

                # Define the command to export the table
                cmd = f"pg_dump {DATABASE_URL} -f {file}"

                # Execute the command
                os.system(cmd)
            elif self.driver == Driver.MongoDB:
                print("MongoDB does not support exporting to SQL file directly.")
                return

        print(f'Exported to {os.path.abspath(file)}')

    def import_(self, *, filename: str):
        # Define the path to the exports directory
        export_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), '..', 'data', 'exports')

        # Create the exports directory if it doesn't exist
        Path(export_path).mkdir(parents=True, exist_ok=True)

        # Check if the filename ends with '.json'
        if filename.endswith('.json'):
            # If the driver is not MongoDB, raise an error
            if self.driver != Driver.MongoDB:
                raise ValueError(
                    "Invalid driver for JSON file. Expected 'mongodb'.")

        # Check if the filename ends with '.sql'
        elif filename.endswith('.sql'):
            # If the driver is not PostgreSQL or SQLite, raise an error
            if self.driver not in [Driver.PostgreSQL, Driver.SQLite]:
                raise ValueError(
                    "Invalid driver for SQL file. Expected 'pgsql' or 'sqlite'.")

        # Check if the file exists
        file_path = os.path.join(export_path, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"The file {filename} does not exist in the export path.")

        # Load the data and insert it into the database
        with open(file_path, 'r', encoding='utf-8') as file:
            # If the driver is MongoDB
            if self.driver == Driver.MongoDB:
                # Load the JSON data
                servers = json.load(file)

                # Insert the data into the MongoDB collection
                result = self.servers.insert_many(servers)
                print(f"Imported {len(result.inserted_ids)} servers.")
            # If the driver is PostgreSQL or SQLite
            elif self.driver in [Driver.PostgreSQL, Driver.SQLite]:
                # Read the SQL commands
                sql_script = file.read()

                self.create_table_if_not_exists()

                # Execute the SQL commands
                conn, cursor = self.cursor()

                if self.driver == Driver.PostgreSQL:
                    cursor.execute(sql_script)
                if self.driver == Driver.SQLite:
                    cursor.executescript(sql_script)

                # Commit the changes and close the cursor
                self.close(conn, cursor, commit=True)

                print(f"Imported {len(sql_script.splitlines())} servers.")

    class ServerNotFoundError(Exception):
        pass


if __name__ == '__main__':
    database = Database()

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    subparsers.add_parser('all')
    export = subparsers.add_parser('export')
    export.add_argument('--to_driver', choices=drivers,
                        default=database.driver.value)

    # Add a parser for the 'import' action
    import_ = subparsers.add_parser('import')
    import_.add_argument('--filename', required=True)

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(-1)

    if args.action == 'all':
        for server in database.__all_servers():
            print(server)
    elif args.action == 'export':
        database.export(to_driver=args.to_driver)
    elif args.action == 'import':
        database.import_(filename=args.filename)
