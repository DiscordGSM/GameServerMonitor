from __future__ import annotations

import base64
import json
import os
import sys

import discord
from discord.utils import MISSING
from dotenv import load_dotenv

from discordgsm.database import Database
from discordgsm.gamedig import Gamedig

if sys.version_info < (3, 9):
    import backports.zoneinfo as zoneinfo
    from backports.zoneinfo import ZoneInfo
else:
    import zoneinfo
    from zoneinfo import ZoneInfo

load_dotenv()

database = Database()
gamedig = Gamedig()

s = os.environ['APP_TOKEN'].strip().split('.')[0] + '==='
client_id = base64.b64decode(s).decode('utf-8', 'ignore')

# Manage Channels, Send Messages, Manage Messages, Embed Links, Use External Emojis, Use External Stickers, Add Reactions
permissions = '137439242320'
invite_link = f'https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=applications.commands%20bot'

public = os.getenv('APP_PUBLIC', '').lower() == 'true'
whitelist_guilds = MISSING if public else [discord.Object(id=int(guild)) for guild in os.getenv(
    'WHITELIST_GUILDS', '').replace(';', ',').split(',') if guild]

timezones: set[str] = zoneinfo.available_timezones()


def tz(timezone: str):
    return ZoneInfo(timezone)


if public:
    sponsors_file = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), '..', 'sponsors.json')

    if not os.path.isfile(sponsors_file):
        with open(sponsors_file, 'w', encoding='utf8') as f:
            json.dump({'348921660361146380': {
                      'id': 'OTg1OTU1Nzg0NTE1MDE4ODQy', 'limit': 30}}, f, indent=4)


def server_limit(user_id: int):
    with open(sponsors_file, 'r', encoding='utf8') as f:
        sponsors = dict(json.load(f))

    if str(user_id) in sponsors:
        return int(sponsors[str(user_id)]['limit'])

    return int(os.getenv('APP_PUBLIC_SERVER_LIMIT', '10'))
