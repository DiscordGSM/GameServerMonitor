import base64
import os

from dotenv import load_dotenv

import discord
from database import Database
from discord.utils import MISSING
from gamedig import Gamedig

load_dotenv()

database = Database()
gamedig = Gamedig()

client_id = base64.b64decode(os.environ['APP_TOKEN'].strip().split('.')[0] + '===').decode()
permissions = '137439225936' # Manage Channels, Send Messages, Manage Messages, Use External Emojis, Use External Stickers, Add Reactions
invite_link = f'https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=applications.commands%20bot'

public = os.getenv('APP_PUBLIC', '').lower() == 'true'
guilds = public and MISSING or [discord.Object(id=int(guild)) for guild in os.getenv('WHITELIST_GUILDS', '').replace(';', ',').split(',') if guild]
