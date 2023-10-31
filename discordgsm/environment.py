from __future__ import annotations

import os
from enum import Enum
from typing import Optional, TypeVar

from discord import ActivityType
from dotenv import load_dotenv

load_dotenv()

T = TypeVar('T')


class Variable:
    def __init__(self, name: str, description: str, type: T, default: Optional[T] = None, required=False, guide_link: Optional[str] = None):
        self.name = name
        self.description = description
        self.type = type
        self.default = default
        self.required = required
        self.guide_link = guide_link


class Environment:
    def __init__(self, variables: list[Variable]):
        self.variables = {variable.name: variable for variable in variables}
        self.dict = [{
            'name': variable.name,
            'description': variable.description,
            'default': '' if variable.default is None else variable.default,
            'required': variable.required,
            'guide_link': variable.guide_link
        } for variable in variables]

    def getenv(self, name: str):
        variable = self.variables[name]

        if value := os.getenv(name):
            if variable.type is bool:
                return value.lower() == 'true'

            # Not working -> if issubclass(variable.type, Enum):
            if 'Enum' in str(variable.type.__class__):
                return variable.type(int(value))

            return variable.type(value)

        return None if variable.default is None else variable.type(variable.default)


class AdvertiseType(Enum):
    server_count = 0
    individually = 1
    player_stats = 2

    def __int__(self) -> int:
        return self.value


environment = Environment([
    Variable('APP_TOKEN', 'Discord Bot Token.', str, required=True, guide_link='https://discordgsm.com/guide/how-to-get-a-discord-bot-token'),
    Variable('WHITELIST_GUILDS', 'Discord Guild ID, if more than one, separated by a semi colon ;', str, required=True),
    Variable('APP_DEBUG', 'Enable application debug mode.', bool, default=False),
    Variable('APP_ACTIVITY_TYPE', 'Presence activity type override. playing = 0, listening = 2, watching = 3, competing = 5', ActivityType, default=3),
    Variable('APP_ACTIVITY_NAME', 'Presence activity name override.', str),
    Variable('APP_ADVERTISE_TYPE', 'Presence advertise type. server_count = 0, individually = 1, player_stats = 2', AdvertiseType, default=0),
    Variable('TASK_QUERY_SERVER', 'Query servers task scheduled time in seconds.', float, default=60),
    Variable('TASK_QUERY_SERVER_TIMEOUT', 'Query servers task timeout in seconds.', float, default=15),
    Variable('DB_CONNECTION', 'Database type. Accepted value: sqlite, pgsql, mongodb', str, default='sqlite'),
    Variable('DATABASE_URL', 'Database connection url.', str),
    Variable('COMMAND_QUERY_PUBLIC', 'Whether the /queryserver command should be available to all users.', bool, default=False),
    Variable('COMMAND_QUERY_COOLDOWN', 'The /queryserver command cooldown in seconds. (Administrator will not be affected)', float, default=5),
    Variable('HEROKU_APP_NAME', 'Heroku application name. (Heroku only)', str),
    Variable('WEB_API_ENABLE', 'Enable Web API feature. (Web server only)', bool, default=False),
    Variable('FACTORIO_USERNAME', 'The factorio username associated with the auth token.', str),
    Variable('FACTORIO_TOKEN', 'The factorio auth token.', str),
])


def env(name: str):
    """Get an environment variable"""
    return environment.getenv(name)
