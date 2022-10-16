import asyncio
import json
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
import discord
from discord import (ActivityType, AutoShardedClient, ButtonStyle, Client,
                     Embed, Interaction, Message, SelectOption, SyncWebhook,
                     app_commands)
from discord.ext import tasks
from discord.ui import Button, Modal, Select, TextInput, View
from dotenv import load_dotenv

from discordgsm.logger import Logger
from discordgsm.server import Server
from discordgsm.service import (ZoneInfo, database, gamedig, invite_link,
                                public, timezones, whitelist_guilds)
from discordgsm.styles.style import Style

load_dotenv()

# Create table here because it will cause thread issue on service.py
database.create_table_if_not_exists()

# DiscordGSM styles
styles = {style.__name__: style for style in Style.__subclasses__()}

# Discord messages cache
messages: Dict[int, Message] = {}


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

    Logger.info(f'Connected to {database.type} database')
    Logger.info(f'Logged on as {client.user}')
    Logger.info(f'Add to Server: {invite_link}')

    await sync_commands(whitelist_guilds)
    query_servers.start()
    edit_messages.start()
    presence_update.start()

    if os.getenv('WEB_API_ENABLE', '').lower() == 'true':
        cache_guilds.start()

    if os.getenv('HEROKU_APP_NAME') is not None:
        heroku_query.start()


@client.event
async def on_guild_join(guild: discord.Guild):
    """Called when a Guild is either created by the Client or when the Client joins a guild."""
    Logger.info(f'{client.user} joined {guild.name}({guild.id}) 🎉.')

    if public:
        webhook = SyncWebhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'))
        webhook.send(f'<@{client.user.id}> joined {guild.name}({guild.id}) 🎉.')
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
    title = (server.result['password'] and ':lock: ' or '') + server.result['name']

    if alert == Alert.TEST:
        description = '🧪 This is a test alert!'
        color = discord.Color.from_rgb(48, 49, 54)
    elif alert == Alert.ONLINE:
        description = '✅ Your server is back online!'
        color = discord.Color.from_rgb(87, 242, 135)
    elif alert == Alert.OFFLINE:
        description = '🚨 Your server seems to be down!'
        color = discord.Color.from_rgb(237, 66, 69)

    embed = Embed(description=description, color=color)
    embed.set_author(name=title)
    embed.add_field(name='Game', value=server.style_data.get('fullname', server.game_id), inline=True)

    game_port = gamedig.game_port(server.result)

    if server.game_id == 'discord':
        embed.add_field(name='Guild ID', value=f'`{server.address}`', inline=True)
    elif game_port is None or game_port == int(server.query_port):
        embed.add_field(name='Address:Port', value=f'`{server.address}:{server.query_port}`', inline=True)
    else:
        embed.add_field(name='Address:Port (Query)', value=f'`{server.address}:{game_port} ({server.query_port})`', inline=True)

    last_update = datetime.now(tz=ZoneInfo(server.style_data.get('timezone', 'Etc/UTC'))).strftime('%Y-%m-%d %I:%M:%S%p')
    icon_url = 'https://avatars.githubusercontent.com/u/61296017'
    embed.set_footer(text=f'Query Time: {last_update}', icon_url=icon_url)

    return embed


def modal(game_id: str, is_add_server: bool):
    """Query server modal"""
    game = gamedig.find(game_id)
    default_port = gamedig.default_port(game_id)
    query_param = {'type': game_id, 'host': TextInput(label='Address'), 'port': TextInput(label='Query Port', max_length='5', default=default_port)}

    modal = Modal(title=game['fullname']).add_item(query_param['host']).add_item(query_param['port'])
    query_extra = {}

    if game_id == 'teamspeak2':
        query_extra['teamspeakQueryPort'] = TextInput(label='TeamSpeak Query Port', max_length='5', default=51234)
        modal.add_item(query_extra['teamspeakQueryPort'])
    elif game_id == 'teamspeak3':
        query_extra['teamspeakQueryPort'] = TextInput(label='TeamSpeak Query Port', max_length='5', default=10011)
        modal.add_item(query_extra['teamspeakQueryPort'])
    elif game_id == 'terraria':
        query_extra['_token'] = TextInput(label='REST user token')
        modal.add_item(query_extra['_token'])

    if game_id == 'discord':
        query_param['host'].label = 'Guild ID'
        modal.remove_item(query_param['port'])
        query_param['port']._value = '0'

    async def modal_on_submit(interaction: Interaction):
        host = query_param['host']._value = str(query_param['host']._value).strip()
        port = str(query_param['port']).strip()

        await interaction.response.defer()

        if is_add_server:
            try:
                database.find_server(interaction.channel.id, host, port)
                await interaction.followup.send('The server already exists in the channel', ephemeral=True)
                return
            except database.ServerNotFoundError:
                pass

        try:
            result = await gamedig.run({**query_param, **query_extra})
        except Exception:
            await interaction.followup.send(f'Fail to query `{game_id}` server `{host}:{port}`. Please try again.', ephemeral=True)
            return

        server = Server.new(interaction.guild_id, interaction.channel_id, game_id, host, port, query_extra, result)
        style = styles['Medium'](server)
        server.style_id = style.id
        server.style_data = await style.default_style_data()

        if is_add_server:
            if public:
                content = f'Server was added by <@{interaction.user.id}> on #{interaction.channel.name}({interaction.channel.id}) {interaction.guild.name}({interaction.guild.id})'
                webhook = SyncWebhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'))
                webhook.send(content, embed=style.embed())

            try:
                server = database.add_server(server)
                Logger.info(f'Successfully added {game_id} server {host}:{port} to #{interaction.channel.name}({interaction.channel.id}).')
            except Exception as e:
                Logger.error(f'Fail to add {game_id} server {host}:{port} {e}')
                await interaction.followup.send(f'Fail to add `{game_id}` server `{host}:{port}`. Please try again later.')
                return

            await refresh_channel_messages(interaction, resend=True)
        else:
            await interaction.followup.send('Query successfully!', embed=style.embed())

    modal.on_submit = modal_on_submit

    return modal


@tree.command(name='queryserver', description='Query server', guilds=whitelist_guilds)
@app_commands.describe(game_id='Game ID. Learn more: https://discordgsm.com/guide/supported-games')
@app_commands.check(custom_command_query_check)
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_except_administrator)
async def command_query(interaction: Interaction, game_id: str):
    """Query server"""
    Logger.command(interaction, game_id)

    if game := await find_game(interaction, game_id):
        await interaction.response.send_modal(modal(game['id'], False))


@tree.command(name='addserver', description='Add server in current channel', guilds=whitelist_guilds)
@app_commands.describe(game_id='Game ID. Learn more: https://discordgsm.com/guide/supported-games')
@app_commands.check(is_administrator)
async def command_addserver(interaction: Interaction, game_id: str):
    """Add server in current channel"""
    Logger.command(interaction, game_id)

    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message('Command only supports text channel.', ephemeral=True)
        return

    if game := await find_game(interaction, game_id):
        if public:
            limit = int(os.getenv('APP_PUBLIC_SERVER_LIMIT', '10'))

            if len(database.all_servers(guild_id=interaction.guild.id)) > limit:
                await interaction.response.send_message(f'The server quota has been exceeded. Limit: {limit}', ephemeral=True)
                return

        await interaction.response.send_modal(modal(game['id'], True))


@tree.command(name='delserver', description='Delete server in current channel', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_delserver(interaction: Interaction, address: str, query_port: int):
    """Delete server in current channel"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer()
        database.delete_server(server)
        await refresh_channel_messages(interaction, resend=True)


@tree.command(name='refresh', description='Refresh servers\' messages manually in current channel', guilds=whitelist_guilds)
@app_commands.check(is_administrator)
async def command_refresh(interaction: Interaction):
    """Refresh servers\' messages in current channel"""
    Logger.command(interaction)

    await interaction.response.defer()
    await refresh_channel_messages(interaction, resend=True)


@tree.command(name='factoryreset', description='Delete all servers in current guild', guilds=whitelist_guilds)
@app_commands.check(is_administrator)
async def command_factoryreset(interaction: Interaction):
    """Delete all servers in current guild"""
    Logger.command(interaction)

    button = Button(style=ButtonStyle.red, label='Delete all servers')

    async def button_callback(interaction: Interaction):
        await interaction.response.defer()
        servers = database.all_servers(guild_id=interaction.guild.id)
        database.factory_reset(interaction.guild.id)
        await asyncio.gather(*[delete_message(server) for server in servers])
        await interaction.followup.send('Factory reset successfully.', ephemeral=True)

    button.callback = button_callback

    view = View()
    view.add_item(button)

    await interaction.response.send_message('Are you sure you want to delete all servers in current guild? This cannot be undone.', view=view, ephemeral=True)


@tree.command(name='moveup', description='Move the server message upward', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_moveup(interaction: Interaction, address: str, query_port: int):
    """Move the server message upward"""
    await action_move(interaction, address, query_port, True)


@tree.command(name='movedown', description='Move the server message downward', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_movedown(interaction: Interaction, address: str, query_port: int):
    """Move the server message downward"""
    await action_move(interaction, address, query_port, False)


async def action_move(interaction: Interaction, address: str, query_port: int, direction: bool):
    """True if move up, otherwise move down"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer()
        database.modify_server_position(server, direction)
        await refresh_channel_messages(interaction, resend=False)
        await interaction.delete_original_response()


@tree.command(name='changestyle', description='Change server message style', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_changestyle(interaction: Interaction, address: str, query_port: int):
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

            await interaction.response.defer()
            server.style_id = select.values[0]
            database.update_server_style_id(server)
            await refresh_channel_messages(interaction, resend=False)

        select.callback = select_callback
        view = View()
        view.add_item(select)

        embed = Embed(title='Select the message style', description=f'Server: `{server.address}:{server.query_port}`', color=discord.Color.from_rgb(235, 69, 158))
        embed.set_author(name=server.result['name'])

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name='editstyledata', description='Edit server message style data', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_editstyledata(interaction: Interaction, address: str, query_port: int):
    """Edit server message style data"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        style = styles.get(server.style_id, styles['Medium'])(server)
        modal = Modal(title=f'Edit {server.address}:{server.query_port}')
        edit_fields = style.default_edit_fields

        for item in edit_fields.values():
            modal.add_item(item)

        async def modal_on_submit(interaction: Interaction):
            await interaction.response.defer()
            server.style_data.update({k: str(v) for k, v in edit_fields.items()})
            database.update_server_style_data(server)
            await refresh_channel_messages(interaction, resend=False)

        modal.on_submit = modal_on_submit

        await interaction.response.send_modal(modal)


@tree.command(name='settimezone', description='Set server message time zone', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.describe(timezone='TZ database name. Learn more: https://discordgsm.com/guide/timezones')
@app_commands.check(is_administrator)
async def command_settimezone(interaction: Interaction, address: str, query_port: int, timezone: str):
    """Set server message time zone"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        if timezone not in timezones:
            await interaction.response.send_message(f'`{timezone}` is not a valid time zone. Learn more: https://discordgsm.com/guide/timezones', ephemeral=True)
            return

        await interaction.response.defer()
        server.style_data.update({'timezone': timezone})
        database.update_server_style_data(server)
        await refresh_channel_messages(interaction, resend=False)
        await interaction.delete_original_response()


@tree.command(name='setalert', description='Set server status alert settings', guilds=whitelist_guilds)
@app_commands.describe(address='IP Address or Domain Name')
@app_commands.describe(query_port='Query Port')
@app_commands.check(is_administrator)
async def command_setalert(interaction: Interaction, address: str, query_port: int):
    """Set server status alert settings"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        # Set up button 1
        button1 = Button(style=ButtonStyle.primary, label='Alert Settings')

        async def button1_callback(interaction: Interaction):
            text_input_webhook_url = TextInput(label='Webhook URL', placeholder='Discord Webhook URL', default=server.style_data.get('_alert_webhook_url', ''), required=False)
            text_input_webhook_content = TextInput(label='Webhook Content', placeholder='Alert Content', default=server.style_data.get('_alert_content', ''), required=False, max_length=4000)
            modal = Modal(title='Alert Settings').add_item(text_input_webhook_url).add_item(text_input_webhook_content)

            async def modal_on_submit(interaction: Interaction):
                await interaction.response.defer()
                webhook_url = str(text_input_webhook_url).strip()
                content = str(text_input_webhook_content).strip()
                server.style_data.update({'_alert_webhook_url': webhook_url, '_alert_content': content})
                database.update_server_style_data(server)

            modal.on_submit = modal_on_submit
            await interaction.response.send_modal(modal)

        button1.callback = button1_callback

        # Set up button 2
        button2 = Button(style=ButtonStyle.secondary, label='Send Test Alert')

        async def button2_callback(interaction: Interaction):
            if webhook_url := server.style_data.get('_alert_webhook_url'):
                try:
                    webhook = SyncWebhook.from_url(webhook_url)
                    content = server.style_data.get('_alert_content', '').strip()
                    webhook.send(content=None if not content else content, embed=alert_embed(server, Alert.TEST))
                    await interaction.response.send_message('Test webhook sent.', ephemeral=True)
                    Logger.info(f'({server.game_id})[{server.address}:{server.query_port}] Send Alert Test successfully.')
                except ValueError:
                    # The URL is invalid.
                    await interaction.response.send_message('The Webhook URL is invalid.', ephemeral=True)
                except discord.NotFound:
                    # This webhook was not found.
                    await interaction.response.send_message('This webhook was not found.', ephemeral=True)
                except discord.HTTPException:
                    # Sending the message failed.
                    await interaction.response.send_message('Sending the message failed.', ephemeral=True)
                except Exception as e:
                    Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] send_alert_webhook Exception {e}')
                    await interaction.response.send_message('Fail to send webhook. Please try again later.', ephemeral=True)
            else:
                await interaction.response.send_message('The Webhook URL is empty.', ephemeral=True)

        button2.callback = button2_callback

        view = View()
        view.add_item(button1)
        view.add_item(button2)

        embed = Embed(title='Set server status alert settings', description=f'Server: `{server.address}:{server.query_port}`', color=discord.Color.from_rgb(235, 69, 158))
        embed.set_author(name=server.result['name'])

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
        await interaction.response.send_message('You don\'t have sufficient privileges to use this command', ephemeral=True)
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
        await interaction.response.send_message(f'`{game_id}` is not a valid game id. Learn more: https://discordgsm.com/guide/supported-games', ephemeral=True)
        return None


async def find_server(interaction: Interaction, address: str, query_port: int):
    """Find server by channel id, and return server"""
    try:
        server = database.find_server(interaction.channel.id, address, query_port)
        return server
    except database.ServerNotFoundError:
        await interaction.response.send_message(f'The server `{address}:{query_port}` does not exist in the channel', ephemeral=True)
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


async def refresh_channel_messages(interaction: Interaction, resend: bool):
    """When resend=True, no need to await interaction.delete_original_response()"""
    servers = database.all_servers(channel_id=interaction.channel.id)

    if not resend:
        await asyncio.gather(*[edit_message(chunks) for chunks in database.all_channels_servers(servers).values()])
        return True

    channel = client.get_channel(interaction.channel.id)

    try:
        await channel.purge(check=lambda m: m.author == client.user)
    except discord.Forbidden as e:
        # You do not have proper permissions to do the actions required.
        Logger.error(f'Channel {interaction.channel.id} channel.purge discord.Forbidden {e}')
        await interaction.followup.send('Missing Permission: `Manage Messages`')
        return False
    except discord.HTTPException as e:
        # Purging the messages failed.
        Logger.error(f'Channel {interaction.channel.id} channel.purge discord.HTTPException {e}')
        await interaction.followup.send('Purging the messages failed. Please try again later.')
        return False

    for chunks in to_chunks(servers, 10):
        try:
            message = await channel.send(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in chunks])
        except discord.Forbidden as e:
            # You do not have the proper permissions to send the message.
            Logger.error(f'Channel {interaction.channel.id} send_message discord.Forbidden {e}')
            await interaction.followup.send('Missing Permission: `Send Messages`')
            return False
        except discord.HTTPException as e:
            # Sending the message failed.
            Logger.error(f'Channel {interaction.channel.id} send_message discord.HTTPException {e}')
            await interaction.followup.send('Sending the message failed. Please try again later.')
            return False

        for server in chunks:
            server.message_id = message.id

        cache_message(message)

    database.update_servers_message_id(servers)

    return True


async def delete_message(server: Server, update_message_id: bool = False):
    """Delete message"""
    message = await fetch_message(server)

    if message is None:
        return

    try:
        await message.delete()
    except discord.Forbidden as e:
        # You do not have proper permissions to delete the message.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] delete_message discord.Forbidden {e}')
        return
    except discord.NotFound:
        # The message was deleted already
        pass
    except discord.HTTPException as e:
        # Deleting the message failed.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] delete_message discord.HTTPException {e}')
        return

    server.message_id = None
    messages.pop(message.id, None)

    if update_message_id:
        database.update_servers_message_id([server])


# Credits: https://stackoverflow.com/questions/312443/how-do-i-split-a-list-into-equally-sized-chunks
def to_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
# endregion


# region Application tasks
@tasks.loop(seconds=float(os.getenv('TASK_EDIT_MESSAGE', '60')))
async def edit_messages():
    """Edit messages (Scheduled)"""
    messages_servers = database.all_messages_servers()
    message_ids = [*messages_servers]
    task_action = 'Fetch' if edit_messages.current_loop == 0 else 'Edit'
    Logger.debug(f'{task_action} messages: Tasks = {len(message_ids)} messages')

    if edit_messages.current_loop == 0:
        tasks = [fetch_message(messages_servers[message_id][0]) for message_id in message_ids]
    else:
        tasks = [edit_message(messages_servers[message_id]) for message_id in message_ids]

    results = []

    # Discord Rate limit: 50 requests per second
    for chunks in to_chunks(tasks, 25):
        results += await asyncio.gather(*chunks)
        await asyncio.sleep(1)

    failed = sum(result is False or result is None for result in results)
    success = len(results) - failed
    Logger.info(f'{task_action} messages: Total = {len(results)}, Success = {success}, Failed = {failed} ({success and int(failed / len(results) * 100) or 0}% fail)')


async def edit_message(servers: List[Server]):
    """Edit message"""
    if len(servers) <= 0:
        return True

    if message := await fetch_message(servers[0]):
        try:
            message = await asyncio.wait_for(message.edit(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in servers]), timeout=2.0)
            Logger.debug(f'Edit messages: {message.id} success')
            return True
        except discord.Forbidden as e:
            # Tried to suppress a message without permissions or edited a message's content or embed that isn't yours.
            Logger.debug(f'Edit messages: {message.id} edit_messages discord.Forbidden {e}')
        except discord.HTTPException as e:
            # Editing the message failed.
            Logger.debug(f'Edit messages: {message.id} edit_messages discord.HTTPException {e}')
        except asyncio.TimeoutError:
            # Possible: discord.http: We are being rate limited.
            Logger.debug(f'Edit messages: {message.id} edit_messages asyncio.TimeoutError')

    return False


@tasks.loop(seconds=float(os.getenv('TASK_QUERY_SERVER', '60')))
async def query_servers():
    """Query servers (Scheduled)"""
    distinct_servers = database.distinct_servers()
    Logger.debug(f'Query servers: Tasks = {len(distinct_servers)} unique servers')

    tasks = [query_server(server) for server in distinct_servers]
    servers: List[Server] = []

    for chunks in to_chunks(tasks, 25):
        servers += await asyncio.gather(*chunks)
        await asyncio.sleep(0.5)

    database.update_servers(servers)

    failed = sum(server.status is False for server in servers)
    success = len(servers) - failed
    Logger.info(f'Query servers: Total = {len(servers)}, Success = {success}, Failed = {failed} ({len(servers) > 0 and int(failed / len(servers) * 100) or 0}% fail)')


async def query_server(server: Server):
    """Query server"""
    status = server.status

    try:
        server.result = await gamedig.query(server)
        server.status = True
        Logger.debug(f'Query servers: ({server.game_id})[{server.address}:{server.query_port}] success: {server.status}')
    except Exception as e:
        server.status = False
        Logger.debug(f'Query servers: ({server.game_id})[{server.address}:{server.query_port}] success: {server.status}, {e}')

    # Send alert when status changes
    if status != server.status:
        if webhook_url := server.style_data.get('_alert_webhook_url'):
            try:
                webhook = SyncWebhook.from_url(webhook_url)
                content = server.style_data.get('_alert_content', '').strip()
                webhook.send(content=None if not content else content, embed=alert_embed(server, Alert.ONLINE if server.status else Alert.OFFLINE))
                Logger.info(f'({server.game_id})[{server.address}:{server.query_port}] Send Alert {"Online" if server.status else "Offline"} successfully.')
            except Exception as e:
                Logger.debug(f'({server.game_id})[{server.address}:{server.query_port}] send_alert_webhook Exception {e}')

    return server


@tasks.loop(minutes=5)
async def presence_update():
    """Changes the client's presence."""
    number_of_servers = int(database.statistics()['unique_servers'])
    activity = discord.Activity(name=f'{number_of_servers} servers', type=ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=activity)


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
        Logger.error(f'Sends a GET request to {url}, {e}')
# endregion

if __name__ == '__main__':
    client.run(os.environ['APP_TOKEN'])
