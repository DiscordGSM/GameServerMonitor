import io
import os
from datetime import datetime
from pathlib import Path

from discord import Interaction
from dotenv import load_dotenv

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

load_dotenv()


class Logger:
    """Custom Logger"""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'logs')

    @staticmethod
    def command(interaction: Interaction, *args, **kwargs):
        message = f'{interaction.guild.name}({interaction.guild.id}) '
        message += f'#{interaction.channel.name}({interaction.channel.id}) '
        message += f'{interaction.user.name}({interaction.user.id}): /{interaction.command.name}'
        Logger.info(message, *args, **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        Logger.__print_and_write_with_tz('INFO', '94', *args, **kwargs)

    @staticmethod
    def warning(*args, **kwargs):
        Logger.__print_and_write_with_tz('WARNING', '93', *args, **kwargs)

    @staticmethod
    def error(*args, **kwargs):
        Logger.__print_and_write_with_tz('ERROR', '91', *args, **kwargs)

    @staticmethod
    def debug(*args, **kwargs):
        if os.getenv('APP_DEBUG', '').lower() == 'true':
            Logger.__print_and_write_with_tz('DEBUG', '36', *args, **kwargs)

    @staticmethod
    def __get_timestamp_with_zone_info():
        return datetime.now(ZoneInfo(os.getenv('TZ'))) if os.getenv('TZ') and os.getenv('TZ').strip() else datetime.now()

    @staticmethod
    def __print_and_write_with_tz(info: str, color: str, *args, **kwargs):
        timestamp = Logger.__get_timestamp_with_zone_info()

        if os.getenv('HEROKU_APP_NAME') is not None:
            print(info.ljust(8), *args, **kwargs)
        else:
            print(f'\x1b[1m\x1b[90m{timestamp.strftime("%Y-%m-%d %H:%M:%S")}\x1b[0m', f'\x1b[1m\x1b[{color}m{info.ljust(8)}\x1b[0m', *args, **kwargs)

        Path(Logger.path).mkdir(parents=True, exist_ok=True)

        with open(os.path.join(Logger.path, f'{timestamp.date()}.txt'), 'a', encoding='utf-8') as f:
            f.write(Logger.__print_to_string(timestamp.strftime("%Y-%m-%d %H:%M:%S"), info.ljust(8), *args, **kwargs))

    # Credits: https://stackoverflow.com/questions/39823303/python3-print-to-string
    @staticmethod
    def __print_to_string(*args, **kwargs):
        with io.StringIO() as output:
            print(*args, file=output, **kwargs)
            return output.getvalue()
