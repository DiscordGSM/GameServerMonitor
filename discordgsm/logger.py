import logging
import os
from logging.handlers import TimedRotatingFileHandler

from discord import Interaction, utils
from discord.utils import _ColourFormatter, stream_supports_colour
from dotenv import load_dotenv

load_dotenv()

filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'logs', 'discordgsm.log')
file_handler = TimedRotatingFileHandler(filename, when='D', encoding='utf-8')
file_handler.namer = lambda name: name.replace('.log', '') + '.log'
utils.setup_logging(handler=file_handler, root=True)

handler = logging.StreamHandler()

if isinstance(handler, logging.StreamHandler) and stream_supports_colour(handler.stream):
    formatter = _ColourFormatter()
else:
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

handler.setFormatter(formatter)

library, _, _ = __name__.partition('.')
logger = logging.getLogger(library)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


class Logger:
    """Custom Logger"""

    @staticmethod
    def command(interaction: Interaction, *args, **kwargs):
        message = f'{interaction.guild.name}({interaction.guild.id}) '
        message += f'#{interaction.channel.name}({interaction.channel.id}) '
        message += f'{interaction.user.name}({interaction.user.id}): /{interaction.command.name}'
        Logger.info(message, *args, **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        logger.info(*args, **kwargs)

    @staticmethod
    def warning(*args, **kwargs):
        logger.warning(*args, **kwargs)

    @staticmethod
    def error(*args, **kwargs):
        logger.error(*args, **kwargs)

    @staticmethod
    def debug(*args, **kwargs):
        if os.getenv('APP_DEBUG', '').lower() == 'true':
            logger.debug(*args, **kwargs)
