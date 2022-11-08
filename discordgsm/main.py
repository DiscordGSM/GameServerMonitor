import asyncio
import json
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
import discord
from discord import (ActivityType, AutoShardedClient, ButtonStyle, Client,
                     Embed, Interaction, Locale, Message, SelectOption,
                     Webhook, app_commands)
from discord.ext import tasks
from discord.ui import Button, Modal, Select, TextInput, View
from dotenv import load_dotenv

from discordgsm.gamedig import GamedigGame
from discordgsm.logger import Logger
from discordgsm.server import Server
from discordgsm.service import (ZoneInfo, database, gamedig, invite_link,
                                public, timezones, whitelist_guilds)
from discordgsm.styles.style import Style
from discordgsm.translator import Translator, t
from discordgsm.version import __version__

load_dotenv()

# Create table here because it will cause thread issue on service.py
database.create_table_if_not_exists()

styles = {style.__name__: style for style in Style.__subclasses__()}
"""DiscordGSM styles"""

messages: Dict[int, Message] = {}
"""DiscordGSM messages cache"""


def cache_message(message: Message):
    """Cache the discord.Message"""
    messages[message.id] = message
    return messages[message.id]


# Client setup
intents = discord.Intents.default()
shard_ids = [int(shard_id) for shard_id in os.getenv('APP_SHARD_IDS').replace(';', ',').split(',') if shard_id] if len(os.getenv('APP_SHARD_IDS', '')) > 0 else None
shard_count = int(os.getenv('APP_SHARD_COUNT', '1'))
client = Client(intents=intents) if not public else AutoShardedClient(intents=intents, shard_ids=shard_ids, shard_count=shard_count)


# region Application event
@client.event
async def on_ready():
    """Called when the client is done preparing the data received from Discord."""
    await client.wait_until_ready()

    Logger.info(f'Starting Game Server Monitor {__version__}')
    Logger.info(f'Connected to {database.type} database')
    Logger.info(f'Logged on as {client.user}')
    Logger.info(f'Add to Server: {invite_link}')
    Logger.info('Thank you for using Game Server Monitor, you may consider sponsoring us ♥.')
    Logger.info('Github Sponsors: https://github.com/sponsors/DiscordGSM')

    await sync_commands(whitelist_guilds)
    await tasks_fetch_messages()

    if not tasks_query.is_running():
        tasks_query.start()

    if not cache_guilds.is_running() and os.getenv('WEB_API_ENABLE', '').lower() == 'true':
        cache_guilds.start()

    if not heroku_query.is_running() and os.getenv('HEROKU_APP_NAME') is not None:
        heroku_query.start()


@client.event
async def on_guild_join(guild: discord.Guild):
    """Called when a Guild is either created by the Client or when the Client joins a guild."""
    Logger.info(f'{client.user} joined {guild.name}({guild.id}) 🎉.')

    if public:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'), session=session)
            await webhook.send(f'<@{client.user.id}> joined {guild.name}({guild.id}) 🎉.')
            return

    # Sync the commands to guild when discordgsm joins a guild.
    if guild.id in [guild.id for guild in whitelist_guilds]:
        await sync_commands([discord.Object(id=guild.id)])


@client.event
async def on_guild_remove(guild: discord.Guild):
    """Remove all associated servers in database when discordgsm leaves"""
    database.factory_reset(guild.id)
    Logger.info(f'{client.user} left {guild.name}({guild.id}), associated servers were deleted.')


@client.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    """Remove all associated servers in database when channel deletes"""
    database.delete_servers(channel_id=channel.id)
    Logger.info(f'Channel #{channel.name}({channel.id}) deleted, associated servers were deleted.')


async def sync_commands(guilds: List[discord.Object]):
    """Syncs the application commands to Discord."""
    if not public:
        for guild in guilds:
            await tree_sync(guild)

        # Remove global commands
        tree.clear_commands(guild=None)

    await tree_sync()


async def tree_sync(guild: discord.Object = None):
    """Syncs the application commands to Discord."""
    try:
        await tree.set_translator(Translator())
        await tree.sync(guild=guild)

        if public:
            Logger.info('Sync the commands to Discord. Global commands take up to 1-hour to propagate.')
        elif guild is not None:
            Logger.info(f'Sync the commands to guild {guild.id}. Guild commands propagate instantly.')
    except discord.ClientException as e:
        Logger.error(f'The client does not have an application ID. {e} {guild.id if guild else ""}')
    except discord.Forbidden as e:
        Logger.error(f'The client does not have the applications.commands scope in the guild. {e} {guild.id if guild else ""}')
    except discord.HTTPException as e:
        Logger.error(f'Syncing the commands failed. {e} {guild.id if guild else ""}')
# endregion


# region Application checks
def is_owner(interaction: Interaction) -> bool:
    """Check is owner"""
    return interaction.user.id == interaction.guild.owner.id


def is_administrator(interaction: Interaction) -> bool:
    """Check is administrator"""
    return interaction.user.guild_permissions.administrator


def custom_command_query_check(interaction: Interaction) -> bool:
    """Query command check"""
    if os.getenv('COMMAND_QUERY_PUBLIC', '').lower() == 'true':
        return True

    return is_administrator(interaction)


def cooldown_for_everyone_except_administrator(interaction: Interaction) -> Optional[app_commands.Cooldown]:
    """Cooldown for everyone except administrator"""
    if is_administrator(interaction):
        return None

    return app_commands.Cooldown(1, float(os.getenv('COMMAND_QUERY_COOLDOWN', '5')))
# endregion


# region Application commands
tree = app_commands.CommandTree(client)


class Alert(Enum):
    TEST = 1
    ONLINE = 2
    OFFLINE = 3


def alert_embed(server: Server, alert: Alert):
    """Returns alert embed"""
    locale = str(server.style_data.get('locale', 'en-US'))
    title = (server.result['password'] and ':lock: ' or '') + server.result['name']

    if alert == Alert.TEST:
        description = t('embed.alert.description.test', locale)
        color = discord.Color.from_rgb(48, 49, 54)
    elif alert == Alert.ONLINE:
        description = t('embed.alert.description.online', locale)
        color = discord.Color.from_rgb(87, 242, 135)
    elif alert == Alert.OFFLINE:
        description = t('embed.alert.description.offline', locale)
        color = discord.Color.from_rgb(237, 66, 69)

    embed = Embed(description=description, color=color)
    embed.set_author(name=title)

    style = styles['Medium'](server)
    style.add_game_field(embed)
    style.add_address_field(embed)

    query_time = datetime.now(tz=ZoneInfo(server.style_data.get('timezone', 'Etc/UTC'))).strftime('%Y-%m-%d %I:%M:%S%p')
    query_time = t('embed.alert.footer.query_time', locale).format(query_time=query_time)
    icon_url = 'https://avatars.githubusercontent.com/u/61296017'
    embed.set_footer(text=f'DiscordGSM {__version__} | {query_time}', icon_url=icon_url)

    return embed


async def send_alert(server: Server, alert: Alert):
    """Send alert to webhook"""
    if webhook_url := server.style_data.get('_alert_webhook_url'):
        content = server.style_data.get('_alert_content', '').strip()
        content = None if not content else content
        username = 'Game Server Monitor Alert'
        avatar_url = 'https://avatars.githubusercontent.com/u/61296017'

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            await webhook.send(content, username=username, avatar_url=avatar_url, embed=alert_embed(server, alert))
    else:
        # The Webhook URL is empty.
        raise NameError()


def query_server_modal(game: GamedigGame, locale: Locale):
    """Query server modal"""
    query_param: Dict[str, TextInput] = {
        'host': TextInput(label=t('modal.text_input.address.label', locale), placeholder=t('command.option.address', locale)),
        'port': TextInput(
            label=t('modal.text_input.query_port.label', locale),
            placeholder=t('command.option.query_port', locale),
            max_length='5',
            default=gamedig.default_port(game['id'])
        )
    }

    title = game['fullname'].ljust(45)[:45]

    if len(game['fullname']) > 45:
        title = title[:-3] + '...'

    modal = Modal(title=title).add_item(query_param['host']).add_item(query_param['port'])
    query_extra: Dict[str, TextInput] = {}

    if game['id'] == 'teamspeak2':
        query_extra['teamspeakQueryPort'] = TextInput(label='TeamSpeak Query Port', max_length='5', default=51234)
        modal.add_item(query_extra['teamspeakQueryPort'])
    elif game['id'] == 'teamspeak3':
        query_extra['teamspeakQueryPort'] = TextInput(label='TeamSpeak Query Port', max_length='5', default=10011)
        modal.add_item(query_extra['teamspeakQueryPort'])
    elif game['id'] == 'terraria':
        query_extra['_token'] = TextInput(label='REST user token')
        modal.add_item(query_extra['_token'])

    if game['id'] == 'discord':
        query_param['host'].label = t('modal.text_input.guild_id.label', locale)
        modal.remove_item(query_param['port'])
        query_param['port']._value = '0'

    return modal, query_param, query_extra


def query_server_modal_handler(interaction: Interaction, game: GamedigGame, is_add_server: bool):
    """Query server modal"""
    modal, query_param, query_extra = query_server_modal(game, interaction.locale)

    async def modal_on_submit(interaction: Interaction):
        params = {**query_param, **query_extra}

        for item in params.values():
            item.default = item._value = str(item._value).strip()

        address, query_port = str(query_param['host']), str(query_param['port'])

        # Validate the port number
        for key in params.keys():
            if 'port' in key.lower() and not gamedig.is_port_valid(str(params[key])):
                content = t('function.query_server_modal.invalid_port', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)
                return

        await interaction.response.defer(ephemeral=is_add_server, thinking=True)

        # Check is the server already exists in database
        if is_add_server:
            try:
                database.find_server(interaction.channel.id, address, query_port)
                content = t('function.query_server_modal.already_exists', interaction.locale)
                await interaction.followup.send(content, ephemeral=True)
                return
            except database.ServerNotFoundError:
                pass

        # Query the server
        try:
            result = await gamedig.run({**{'type': game['id']}, **params})
        except Exception:
            content = t('function.query_server_modal.fail_to_query', interaction.locale).format(game_id=game['id'], address=address, query_port=query_port)
            await interaction.followup.send(content, ephemeral=True)
            return

        # Create new server object
        server = Server.new(interaction.guild_id, interaction.channel_id, game['id'], address, query_port, query_extra, result)
        style = styles['Medium'](server)
        server.style_id = style.id
        server.style_data = await style.default_style_data(None)

        if is_add_server:
            if public:
                content = f'Server was added by <@{interaction.user.id}> on #{interaction.channel.name}({interaction.channel.id}) {interaction.guild.name}({interaction.guild.id})'

                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'), session=session)
                    await webhook.send(content, embed=style.embed())

            server = database.add_server(server)
            Logger.info(f'Successfully added {game["id"]} server {address}:{query_port} to #{interaction.channel.name}({interaction.channel.id}).')

            if await resend_channel_messages(interaction):
                await interaction.delete_original_response()
        else:
            content = t('function.query_server_modal.success', interaction.locale)
            await interaction.followup.send(content, embed=style.embed())

    modal.on_submit = modal_on_submit

    return modal


@tree.command(name='queryserver', description='command.queryserver.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(game_id='command.option.game_id')
@app_commands.check(custom_command_query_check)
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_except_administrator)
async def command_query(interaction: Interaction, game_id: str):
    """Query server"""
    Logger.command(interaction, game_id)

    if game := await find_game(interaction, game_id):
        await interaction.response.send_modal(query_server_modal_handler(interaction, game, False))


@tree.command(name='addserver', description='command.addserver.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(game_id='command.option.game_id')
@app_commands.check(is_administrator)
async def command_addserver(interaction: Interaction, game_id: str):
    """Add server in current channel"""
    Logger.command(interaction, game_id)

    if not isinstance(interaction.channel, discord.TextChannel):
        content = t('command.addserver.text_channel_only', interaction.locale)
        await interaction.response.send_message(content, ephemeral=True)
        return

    if game := await find_game(interaction, game_id):
        if public:
            limit = int(os.getenv('APP_PUBLIC_SERVER_LIMIT', '10'))

            if len(database.all_servers(guild_id=interaction.guild.id)) > limit:
                content = t('command.addserver.limit_exceeded', interaction.locale).format(limit=limit)
                await interaction.response.send_message(content, ephemeral=True)
                return

        await interaction.response.send_modal(query_server_modal_handler(interaction, game, True))


@tree.command(name='delserver', description='command.delserver.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_delserver(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Delete server in current channel"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)
        database.delete_server(server)

        if await resend_channel_messages(interaction):
            await interaction.delete_original_response()


@tree.command(name='refresh', description='command.refresh.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.check(is_administrator)
async def command_refresh(interaction: Interaction):
    """Refresh servers\' messages in current channel"""
    Logger.command(interaction)

    await interaction.response.defer(ephemeral=True)

    if await resend_channel_messages(interaction):
        await interaction.delete_original_response()


@tree.command(name='factoryreset', description='command.factoryreset.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.check(is_administrator)
async def command_factoryreset(interaction: Interaction):
    """Delete all servers in current guild"""
    Logger.command(interaction)

    label = t('command.factoryreset.button.label', interaction.locale)
    button = Button(style=ButtonStyle.red, label=label)

    async def button_callback(interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        servers = database.all_servers(guild_id=interaction.guild.id)
        database.factory_reset(interaction.guild.id)

        async def purge_channel(channel_id: int):
            channel = client.get_channel(channel_id)

            try:
                await channel.purge(check=lambda m: m.author == client.user, before=interaction.created_at)
            except discord.Forbidden as e:
                # You do not have proper permissions to do the actions required.
                Logger.error(f'Channel {channel.id} channel.purge discord.Forbidden {e}')
            except discord.HTTPException as e:
                # Purging the messages failed.
                Logger.error(f'Channel {channel.id} channel.purge discord.HTTPException {e}')

        channel_ids = set(server.channel_id for server in servers if server.channel_id)
        await asyncio.gather(*[purge_channel(channel_id) for channel_id in channel_ids])
        content = t('command.factoryreset.success', interaction.locale)
        await interaction.followup.send(content, ephemeral=True)

    button.callback = button_callback

    view = View()
    view.add_item(button)

    content = t('command.factoryreset.content', interaction.locale)
    await interaction.response.send_message(content, view=view, ephemeral=True)


@tree.command(name='moveup', description='command.moveup.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_moveup(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Move the server message upward"""
    await action_move(interaction, address, query_port, True)


@tree.command(name='movedown', description='command.movedown.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_movedown(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Move the server message downward"""
    await action_move(interaction, address, query_port, False)


async def action_move(interaction: Interaction, address: str, query_port: int, direction: bool):
    """True if move up, otherwise move down"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)
        database.modify_server_position(server, direction)
        await refresh_channel_messages(interaction)
        await interaction.delete_original_response()


@tree.command(name='changestyle', description='command.changestyle.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_changestyle(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Change server message style"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        current_style = styles.get(server.style_id, styles['Medium'])(server)
        options = []

        for style_id in styles:
            style = styles[style_id](server)
            options.append(SelectOption(label=style.display_name, value=style_id, description=style.description, emoji=style.emoji, default=style_id == current_style.id))

        select = Select(options=options)

        async def select_callback(interaction: Interaction):
            if select.values[0] not in styles:
                return

            await interaction.response.defer(ephemeral=True)
            server.style_id = select.values[0]
            database.update_server_style_id(server)
            await refresh_channel_messages(interaction)

        select.callback = select_callback
        view = View()
        view.add_item(select)

        content = t('command.changestyle.content', interaction.locale).format(address=server.address, query_port=server.query_port)
        await interaction.response.send_message(content, view=view, ephemeral=True)


@tree.command(name='editstyledata', description='command.editstyledata.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_editstyledata(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Edit server message style data"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        style = styles.get(server.style_id, styles['Medium'])(server)
        title = t('command.editstyledata.modal.title', interaction.locale).format(address=server.address, query_port=server.query_port)
        modal = Modal(title=title)
        edit_fields = style.default_edit_fields

        for item in edit_fields.values():
            modal.add_item(item)

        async def modal_on_submit(interaction: Interaction):
            await interaction.response.defer(ephemeral=True)
            server.style_data.update({k: str(v) for k, v in edit_fields.items()})
            database.update_server_style_data(server)
            await refresh_channel_messages(interaction)

        modal.on_submit = modal_on_submit

        await interaction.response.send_modal(modal)


@tree.command(name='switch', description='command.switch.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(channel='command.option.channel')
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_switch(interaction: Interaction, channel: discord.TextChannel, address: Optional[str], query_port: Optional[app_commands.Range[int, 0, 65535]]):
    """Switch the server message(s) to another channel"""
    if channel.id == interaction.channel.id:
        content = t('command.switch.same_channel', interaction.locale)
        await interaction.response.send_message(content, ephemeral=True)
        return

    if servers := await find_servers(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)

        for server in servers:
            server.channel_id = channel.id

        database.update_servers_channel_id(servers)
        await resend_channel_messages(None, interaction.channel.id)
        await resend_channel_messages(None, channel.id)

        if len(servers) <= 1:
            await interaction.delete_original_response()
        else:
            content = t('command.switch.success', interaction.locale).format(count=len(servers), channel_id1=interaction.channel.id, channel_id2=channel.id)
            await interaction.followup.send(content, ephemeral=True)


@tree.command(name='settimezone', description='command.settimezone.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(timezone='command.option.timezone')
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_settimezone(interaction: Interaction, timezone: str, address: Optional[str], query_port: Optional[app_commands.Range[int, 0, 65535]]):
    """Set server message time zone"""
    Logger.command(interaction, timezone, address, query_port)

    if timezone not in timezones:
        content = t('command.settimezone.invalid', interaction.locale).format(timezone=timezone)
        await interaction.response.send_message(content, ephemeral=True)
        return

    if servers := await find_servers(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)

        for server in servers:
            server.style_data.update({'timezone': timezone})

        database.update_servers_style_data(servers)
        await refresh_channel_messages(interaction)
        await interaction.delete_original_response()


@tree.command(name='setclock', description='command.setclock.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(clock_format='command.option.clock_format')
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.choices(clock_format=[app_commands.Choice(name="command.choice.12_hour_clock", value=12), app_commands.Choice(name="command.choice.24_hour_clock", value=24)])
@app_commands.check(is_administrator)
async def command_setclock(interaction: Interaction, clock_format: app_commands.Choice[int], address: Optional[str], query_port: Optional[app_commands.Range[int, 0, 65535]]):
    """Set server message clock format"""
    Logger.command(interaction, clock_format.value, address, query_port)

    if servers := await find_servers(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)

        for server in servers:
            server.style_data.update({'clock_format': clock_format.value})

        database.update_servers_style_data(servers)
        await refresh_channel_messages(interaction)
        await interaction.delete_original_response()


@tree.command(name='setlocale', description='command.setlocale.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(locale='command.option.locale')
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_setlocale(interaction: Interaction, locale: str, address: Optional[str], query_port: Optional[app_commands.Range[int, 0, 65535]]):
    """Set server message locale"""
    Logger.command(interaction, locale, address, query_port)

    if locale not in set(str(value) for value in Locale):
        content = t('command.setlocale.invalid', interaction.locale).format(locale=locale)
        await interaction.response.send_message(content, ephemeral=True)
        return

    if servers := await find_servers(interaction, address, query_port):
        await interaction.response.defer(ephemeral=True)

        for server in servers:
            server.style_data.update({'locale': locale})

        database.update_servers_style_data(servers)
        await refresh_channel_messages(interaction)
        await interaction.delete_original_response()


@tree.command(name='setalert', description='command.setalert.description', guilds=whitelist_guilds)
@app_commands.guild_only()
@app_commands.describe(address='command.option.address')
@app_commands.describe(query_port='command.option.query_port')
@app_commands.check(is_administrator)
async def command_setalert(interaction: Interaction, address: str, query_port: app_commands.Range[int, 0, 65535]):
    """Set server status alert settings"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        # Set up button 1
        label = t('command.setalert.settings.button.label', interaction.locale)
        button1 = Button(style=ButtonStyle.primary, label=label)

        async def button1_callback(interaction: Interaction):
            label = t('modal.text_input.webhook_url.label', interaction.locale)
            text_input_webhook_url = TextInput(label=label, default=server.style_data.get('_alert_webhook_url', ''), required=False)
            label = t('modal.text_input.webhook_content.label', interaction.locale)
            text_input_webhook_content = TextInput(label=label, default=server.style_data.get('_alert_content', ''), required=False, max_length=4000)
            title = t('command.setalert.settings.modal.title', interaction.locale)
            modal = Modal(title=title).add_item(text_input_webhook_url).add_item(text_input_webhook_content)

            async def modal_on_submit(interaction: Interaction):
                await interaction.response.defer(ephemeral=True)
                webhook_url = str(text_input_webhook_url).strip()
                content = str(text_input_webhook_content).strip()
                server.style_data.update({'_alert_webhook_url': webhook_url, '_alert_content': content})
                database.update_server_style_data(server)

            modal.on_submit = modal_on_submit
            await interaction.response.send_modal(modal)

        button1.callback = button1_callback

        # Set up button 2
        label = t('command.setalert.test.button.label', interaction.locale)
        button2 = Button(style=ButtonStyle.secondary, label=label)

        async def button2_callback(interaction: Interaction):
            try:
                await send_alert(server, Alert.TEST)
                content = t('command.setalert.test.success', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)
                Logger.info(f'({server.game_id})[{server.address}:{server.query_port}] Send Alert Test successfully.')
            except NameError:
                # The URL is empty.
                content = t('command.setalert.test.empty', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)
            except ValueError:
                # The URL is invalid.
                content = t('command.setalert.test.invalid', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)
            except discord.NotFound:
                # This webhook was not found.
                content = t('command.setalert.test.not_found', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)
            except Exception as e:
                # Sending the message failed. (Include discord.HTTPException)
                Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] send_alert Exception {e}')
                content = t('command.error.internal_error', interaction.locale)
                await interaction.response.send_message(content, ephemeral=True)

        button2.callback = button2_callback

        view = View()
        view.add_item(button1)
        view.add_item(button2)

        content = t('command.setalert.content', interaction.locale).format(address=server.address, query_port=query_port)
        await interaction.response.send_message(content, view=view, ephemeral=True)


@command_query.error
@command_addserver.error
@command_delserver.error
@command_refresh.error
@command_moveup.error
@command_movedown.error
@command_changestyle.error
@command_editstyledata.error
@command_settimezone.error
async def command_error_handler(interaction: Interaction, error: app_commands.AppCommandError):
    """The default error handler provided by the client."""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        content = t('command.error.no_permission', interaction.locale)
        await interaction.response.send_message(content, ephemeral=True)
    else:
        Logger.error(str(error))
# endregion


# region Application functions
async def find_game(interaction: Interaction, game_id: str):
    """Find game by game_id, return """
    try:
        game = gamedig.find(game_id)
        return game
    except LookupError:
        content = t('function.find_game.not_found', interaction.locale).format(game_id=game_id)
        await interaction.response.send_message(content, ephemeral=True)
        return None


async def find_server(interaction: Interaction, address: str, query_port: int):
    """Find server by channel id, and return server"""
    try:
        server = database.find_server(interaction.channel.id, address, query_port)
        return server
    except database.ServerNotFoundError:
        content = t('function.find_server.not_found', interaction.locale).format(address=address, query_port=query_port)
        await interaction.response.send_message(content, ephemeral=True)
        return None


async def find_servers(interaction: Interaction, address: Optional[str], query_port: Optional[int]):
    if address is None and query_port is None:
        if servers := database.all_servers(channel_id=interaction.channel.id):
            return servers
        else:
            content = t('function.find_servers.empty', interaction.locale)
            await interaction.response.send_message(content, ephemeral=True)
    elif address is not None and query_port is not None:
        if server := await find_server(interaction, address, query_port):
            return [server]
    else:
        content = t('function.find_servers.parameter_error', interaction.locale)
        await interaction.response.send_message(content, ephemeral=True)

    return None


async def fetch_message(server: Server):
    """Fetch message with local cache"""
    if server.message_id is None:
        return None

    if server.message_id in messages:
        return messages[server.message_id]

    channel = client.get_channel(server.channel_id)

    if channel is None:
        return None

    try:
        message = await channel.fetch_message(server.message_id)
        return cache_message(message)
    except discord.NotFound as e:
        # The specified message was not found.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.NotFound {e}')
        server.message_id = None
        database.update_servers_message_id([server])
    except discord.Forbidden as e:
        # You do not have the permissions required to get a message.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.Forbidden {e}')
        server.message_id = None
        database.update_servers_message_id([server])
    except discord.HTTPException as e:
        # Retrieving the message failed.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.HTTPException {e}')

    return None


async def resend_channel_messages(interaction: Optional[Interaction], channel_id: Optional[int] = None):
    """Resend channel messages"""
    channel = client.get_channel(channel_id if channel_id else interaction.channel.id)
    servers = database.all_servers(channel_id=channel.id)

    try:
        await channel.purge(check=lambda m: m.author == client.user, before=interaction.created_at)
    except discord.Forbidden as e:
        # You do not have proper permissions to do the actions required.
        Logger.error(f'Channel {channel.id} channel.purge discord.Forbidden {e}')
        content = t('missing_permission.manage_messages', interaction.locale)
        if interaction: await interaction.followup.send(content, ephemeral=True)
        return False
    except discord.HTTPException as e:
        # Purging the messages failed.
        Logger.error(f'Channel {channel.id} channel.purge discord.HTTPException {e}')
        content = t('command.error.internal_error', interaction.locale)
        if interaction: await interaction.followup.send(content, ephemeral=True)
        return False

    async for chunks in to_chunks(servers, 10):
        try:
            message = await channel.send(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in chunks])
        except discord.Forbidden as e:
            # You do not have the proper permissions to send the message.
            Logger.error(f'Channel {channel.id} send_message discord.Forbidden {e}')
            content = t('missing_permission.send_messages', interaction.locale)
            if interaction: await interaction.followup.send(content, ephemeral=True)
            return False
        except discord.HTTPException as e:
            # Sending the message failed.
            Logger.error(f'Channel {channel.id} send_message discord.HTTPException {e}')
            content = t('command.error.internal_error', interaction.locale)
            if interaction: await interaction.followup.send(content, ephemeral=True)
            return False

        for server in chunks:
            server.message_id = message.id

        cache_message(message)

    database.update_servers_message_id(servers)

    return True


async def refresh_channel_messages(interaction: Interaction):
    """Edit channel messages"""
    servers = database.all_servers(channel_id=interaction.channel.id)
    await asyncio.gather(*[edit_message(chunks) for chunks in database.all_messages_servers(servers).values()])


# Credits: https://stackoverflow.com/questions/312443/how-do-i-split-a-list-into-equally-sized-chunks
async def to_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        await asyncio.sleep(0.001)
        yield lst[i:i + n]
# endregion


# region Application tasks
@tasks.loop(seconds=max(15.0, float(os.getenv('TASK_QUERY_SERVER', '60'))))
async def tasks_query():
    """Query servers (Scheduled)"""
    distinct_servers = database.distinct_servers()
    Logger.debug(f'Query servers: Tasks = {len(distinct_servers)} unique servers')

    tasks = [query_server(server) for server in distinct_servers]
    servers: List[Server] = []

    async for chunks in to_chunks(tasks, int(os.getenv('TASK_QUERY_CHUNK_SIZE', '50'))):
        servers += await asyncio.gather(*chunks)

    database.update_servers(servers)

    failed = sum(server.status is False for server in servers)
    success = len(servers) - failed
    Logger.info(f'Query servers: Total = {len(servers)}, Success = {success}, Failed = {failed} ({len(servers) > 0 and int(failed / len(servers) * 100) or 0}% fail)')

    # Run the tasks after the server queries
    await asyncio.gather(tasks_send_alert(), tasks_edit_messages(), tasks_presence_update(tasks_query.current_loop))


async def query_server(server: Server):
    """Query server"""
    try:
        sent_offline_alert = bool(server.result['raw'].get('__sent_offline_alert', False))
        server.result = await gamedig.query(server)
        server.result['raw']['__sent_offline_alert'] = sent_offline_alert
        server.status = True
        Logger.debug(f'Query servers: ({server.game_id})[{server.address}:{server.query_port}] Success. Ping: {server.result.get("ping", -1)}ms')
    except Exception as e:
        server.status = False
        server.result['raw']['__fail_query_count'] = int(server.result.get('raw', {}).get('__fail_query_count', '0')) + 1
        Logger.debug(f'Query servers: ({server.game_id})[{server.address}:{server.query_port}] Error: {e}')

    return server


async def tasks_send_alert():
    """Send alerts tasks"""
    servers = database.all_servers()

    async def send_alert_webhook(server: Server):
        if server.status is False:
            server.result['raw']['__sent_offline_alert'] = True

        try:
            await send_alert(server, Alert.ONLINE if server.status else Alert.OFFLINE)
            Logger.info(f'({server.game_id})[{server.address}:{server.query_port}] Send Alert {"Online" if server.status else "Offline"} successfully.')
        except NameError:
            # The Webhook URL is empty.
            pass
        except Exception as e:
            Logger.debug(f'({server.game_id})[{server.address}:{server.query_port}] send_alert Exception {e}')

        return server

    fail_query_count = max(2, int(120 / float(os.getenv('TASK_QUERY_SERVER', '60'))))

    def should_send_alert(server: Server):
        if server.status:
            return bool(server.result['raw'].pop('__sent_offline_alert', False))
        else:
            return int(server.result['raw'].get('__fail_query_count', '0')) == fail_query_count

    tasks = [send_alert_webhook(server) for server in servers if should_send_alert(server)]

    async for chunks in to_chunks(tasks, 25):
        servers += await asyncio.gather(*chunks)

    database.update_servers(servers)


async def tasks_fetch_messages():
    messages_servers = database.all_messages_servers()
    Logger.debug(f'Fetch messages: Tasks: {len(messages_servers)} messages')

    tasks = [fetch_message(servers[0]) for servers in messages_servers.values()]
    results = []

    # Discord Rate limit: 50 requests per second
    async for chunks in to_chunks(tasks, 25):
        start = datetime.now().timestamp()
        results += await asyncio.gather(*chunks)
        time_used = datetime.now().timestamp() - start
        await asyncio.sleep(max(0, 1 - time_used))

    failed = sum(result is None for result in results)
    success = len(results) - failed
    Logger.info(f'Fetch messages: Total = {len(results)}, Success = {success}, Failed = {failed} ({success and int(failed / len(results) * 100) or 0}% fail)')


async def tasks_edit_messages():
    """Edit messages tasks"""
    messages_servers = database.all_messages_servers()
    Logger.debug(f'Edit messages: Tasks: {len(messages_servers)} messages')

    tasks = [edit_message(servers) for servers in messages_servers.values()]
    results: List[bool] = []

    # Discord Rate limit: 50 requests per second
    async for chunks in to_chunks(tasks, 25):
        start = datetime.now().timestamp()
        results += await asyncio.gather(*chunks)
        time_used = datetime.now().timestamp() - start
        await asyncio.sleep(max(0, 1 - time_used))

    failed = sum(result is False for result in results)
    success = len(results) - failed
    Logger.info(f'Edit messages: Total = {len(results)}, Success = {success}, Failed = {failed} ({success and int(failed / len(results) * 100) or 0}% fail)')


async def edit_message(servers: List[Server]):
    """Edit message"""
    if len(servers) <= 0:
        return True

    if message := await fetch_message(servers[0]):
        try:
            embeds = [styles.get(server.style_id, styles['Medium'])(server).embed() for server in servers]
            message = await asyncio.wait_for(message.edit(embeds=embeds), timeout=float(os.getenv('TASK_EDIT_MESSAGE_TIMEOUT', '3')))
            Logger.debug(f'Edit messages: {message.id} success')
            return True
        except discord.Forbidden as e:
            # Tried to suppress a message without permissions or edited a message's content or embed that isn't yours.
            Logger.debug(f'Edit messages: {message.id} edit_messages discord.Forbidden {e}')
            messages.pop(message.id, None)
        except discord.HTTPException as e:
            # Editing the message failed.
            Logger.debug(f'Edit messages: {message.id} edit_messages discord.HTTPException {e}')
        except asyncio.TimeoutError:
            # Possible: discord.http: We are being rate limited.
            Logger.debug(f'Edit messages: {message.id} edit_messages asyncio.TimeoutError')
            messages.pop(message.id, None)

    return False


async def tasks_presence_update(current_loop: int):
    """Presence update tasks"""
    name = None
    status = discord.Status.online

    if activity_name := os.getenv('APP_ACTIVITY_NAME'):
        # Activity name override
        name = activity_name
    elif os.getenv('APP_PRESENCE_ADVERTISE', '').lower() == 'true':
        # Advertise online servers one by one
        if servers := database.all_servers():
            online_servers = [server for server in servers if server.status]

            if len(online_servers) > 0:
                server = online_servers[current_loop % len(online_servers)]
                name = Style.get_players_display_string(server) + f' {server.result["name"]}'
    else:
        # Display number of server monitoring
        unique_servers = int(database.statistics()['unique_servers'])

        if unique_servers == 1:
            # Display server status on presence when one server only
            if servers := database.all_servers():
                server = servers[0]
                status = discord.Status.online if server.status else discord.Status.do_not_disturb
                name = Style.get_players_display_string(server)
        else:
            name = f'{unique_servers} servers'

    activity = discord.Activity(name=name, type=ActivityType(int(os.getenv('APP_ACTIVITY_TYPE', '3'))))
    await client.change_presence(status=status, activity=activity)


@tasks.loop(minutes=30)
async def cache_guilds():
    """Cache guilds data to json for web api"""
    guilds = [{
        'id': guild.id,
        'shard_id': guild.shard_id,
        'name': guild.name,
        'description': guild.description,
        'member_count': guild.member_count,
        'icon_url': guild.icon.url if guild.icon is not None else None,
    } for guild in client.guilds]

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'public', 'static', 'guilds.json'), 'w', encoding='utf-8') as f:
        json.dump(guilds, f, ensure_ascii=False)


@tasks.loop(minutes=5)
async def heroku_query():
    """Heroku - Prevent a web dyno from sleeping"""
    url = f"https://{os.environ['HEROKU_APP_NAME']}.herokuapp.com"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, raise_for_status=True) as _:
                Logger.debug(f'Sends a GET request to {url}')
    except Exception as e:
        Logger.error(f'Fail to send a GET request to {url}, {e}, your discord bot will sleeps after 30 minutes of inactivity.')
# endregion

if __name__ == '__main__':
    client.run(os.environ['APP_TOKEN'])
