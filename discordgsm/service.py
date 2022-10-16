from __future__ import annotations

import base64
import os

import discord
from discord.utils import MISSING
from dotenv import load_dotenv

from discordgsm.database import Database
from discordgsm.gamedig import Gamedig

try:
    import zoneinfo
    from zoneinfo import ZoneInfo as ZoneInfo
except ImportError:
    import backports.zoneinfo as zoneinfo
    from backports.zoneinfo import ZoneInfo as ZoneInfo

load_dotenv()

database = Database()
gamedig = Gamedig()

client_id = base64.b64decode(os.environ['APP_TOKEN'].strip().split('.')[0] + '===').decode()
permissions = '137439225936'  # Manage Channels, Send Messages, Manage Messages, Use External Emojis, Use External Stickers, Add Reactions
invite_link = f'https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=applications.commands%20bot'

public = os.getenv('APP_PUBLIC', '').lower() == 'true'
whitelist_guilds = MISSING if public else [discord.Object(id=int(guild)) for guild in os.getenv('WHITELIST_GUILDS', '').replace(';', ',').split(',') if guild]

timezones: set[str] = zoneinfo.available_timezones()
