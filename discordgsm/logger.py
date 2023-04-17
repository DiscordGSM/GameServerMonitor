import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from discord import Interaction, utils
from discord.utils import _ColourFormatter, stream_supports_colour
from dotenv import load_dotenv

load_dotenv()

# Create logs directory
log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'logs')
Path(log_path).mkdir(parents=True, exist_ok=True)

# Set up TimedRotatingFileHandler
file_handler = TimedRotatingFileHandler(os.path.join(log_path, 'discordgsm.log'), when='D', encoding='utf-8')
file_handler.namer = lambda name: name.replace('.log', '') + '.log'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{')
utils.setup_logging(handler=file_handler, formatter=formatter, root=True)

# Set up logger
handler = logging.StreamHandler()

# If the console supports colour, then use colour formatter
if isinstance(handler, logging.StreamHandler) and stream_supports_colour(handler.stream):
    formatter = _ColourFormatter()

handler.setFormatter(formatter)

library, _, _ = __name__.partition('.')
logger = logging.getLogger(library)
logger.setLevel(logging.DEBUG if os.getenv('APP_DEBUG', '').lower() == 'true' else logging.INFO)
logger.addHandler(handler)


class Logger:
    """Custom Logger"""

    @staticmethod
    def command(interaction: Interaction, **kwargs):
        msg = f'{interaction.guild.name}({interaction.guild.id}) '
        msg += f'#{interaction.channel.name}({interaction.channel.id}) '
        msg += f'{interaction.user.name}({interaction.user.id}): /{interaction.command.name} '
        msg += ' '.join([f'{k}: {v}' for k, v in kwargs.items()])
        logger.info(msg)

    @staticmethod
    def info(msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        logger.warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logger.error(msg, *args, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        logger.critical(msg, *args, **kwargs)

    @staticmethod
    def exception(msg, *args, **kwargs):
        logger.exception(msg, *args, **kwargs)

    @staticmethod
    def debug(msg, *args, **kwargs):
        if os.getenv('APP_DEBUG', '').lower() == 'true':
            logger.debug(msg, *args, **kwargs)
