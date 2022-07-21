import base64
import os

from database import Database
from gamedig import Gamedig

database = Database()
gamedig = Gamedig()

client_id = base64.b64decode(os.environ['APP_TOKEN'].split('.')[0]).decode()
permissions = '137439217728' # Send Messages, Use External Emojis, Use External Stickers, Add Reactions
invite_link = f'https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=applications.commands%20bot'
