import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import discord
import requests
from discord import (ActivityType, AutoShardedClient, ButtonStyle, Client,
                     Interaction, Message, SelectOption, SyncWebhook,
                     app_commands)
from discord.ext import tasks
from discord.ui import Button, Modal, Select, TextInput, View
from dotenv import load_dotenv

from logger import Logger
from server import Server
from service import database, gamedig, guilds, invite_link, public
from styles.style import Style

load_dotenv()

# Create table here because it will cause thread issue on service.py
database.create_table_if_not_exists()

# DiscordGSM styles
styles = {style.__name__: style for style in Style.__subclasses__()}

# Discord messages cache
messages: dict[int, Message] = {}

# Client setup
intents = discord.Intents.default()
shard_ids = [int(shard_id) for shard_id in os.getenv('APP_SHARD_IDS').replace(';', ',').split(',') if shard_id] if len(os.getenv('APP_SHARD_IDS', '')) > 0 else None
shard_count = int(os.getenv('APP_SHARD_COUNT', 1))
client = Client(intents=intents) if not public else AutoShardedClient(intents=intents, shard_ids=shard_ids, shard_count=shard_count)

#region Application event
@client.event
async def on_ready():
    await client.wait_until_ready()
    
    Logger.info(f'Connected to {database.type} database')
    Logger.info(f'Logged on as {client.user}')
    Logger.info(f'Add to Server: {invite_link}')
    
    await sync_commands(guilds)
    query_servers.start()
    edit_messages.start()
    presence_update.start()
    
    if os.getenv('WEB_API_ENABLE', '').lower() == 'true':
        cache_guilds.start()
        
    if os.getenv('HEROKU_APP_NAME') is not None:
        heroku_query.start()

@client.event
async def on_guild_join(guild: discord.Guild):
    Logger.info(f'{client.user} joined {guild.name}({guild.id}) 🎉.')
    
    if public:
        webhook = SyncWebhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'))
        webhook.send(content=f'<@{client.user.id}> joined {guild.name}({guild.id}) 🎉.')
        return
    
    """Sync the commands to guild when discordgsm joins a guild."""
    if guild.id in [guild.id for guild in guilds]:
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
    
async def sync_commands(guilds: list[discord.Object]):
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
#endregion

#region Application checks
def is_owner(interaction: Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner.id

def is_administrator(interaction: Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

def custom_command_query_check(interaction: Interaction) -> bool:
    if os.getenv('COMMAND_QUERY_PUBLIC', '').lower() == 'true':
        return True
    
    return is_administrator(interaction)

def cooldown_for_everyone_except_administrator(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
    if is_administrator(interaction):
        return None
    
    return app_commands.Cooldown(1, float(os.getenv('COMMAND_QUERY_COOLDOWN', 5)))
#endregion

#region Application commands
tree = app_commands.CommandTree(client)

def modal(game_id: str, is_add_server: bool):
    """Query server modal"""
    game = gamedig.find(game_id)
    default_port = gamedig.default_port(game_id)
    query_param = {'type': game_id, 'host': TextInput(label='Address'), 'port': TextInput(label='Query Port', max_length='5', default=default_port)}
    
    modal = Modal(title=game['fullname'])
    modal.add_item(query_param['host'])
    modal.add_item(query_param['port'])
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
    
    async def modal_on_submit(interaction: Interaction):
        if is_add_server:
            try:
                database.find_server(interaction.channel.id, str(query_param['host']), str(query_param['port']))
                await interaction.response.send_message('The server already exists in the channel', ephemeral=True)
                return
            except Exception as e:
                pass
        
        try:
            result = gamedig.run(query_param | query_extra)
        except Exception as e:
            await interaction.response.send_message(content=f"Fail to query the server `{query_param['host']}:{query_param['port']}`. Please try again.", ephemeral=True)
            return

        server = Server.new(interaction.guild_id, interaction.channel_id, game_id, str(query_param['host']), str(query_param['port']), query_extra, result)
        style = styles['Medium'](server)
        server.style_id = style.id
        server.style_data = style.default_style_data()
        
        if is_add_server:
            if public:
                content = f'Server was added by <@{interaction.user.id}> on #{interaction.channel.name}({interaction.channel.id}) {interaction.guild.name}({interaction.guild.id})'
                webhook = SyncWebhook.from_url(os.getenv('APP_PUBLIC_WEBHOOK_URL'))
                webhook.send(content=content, embed=style.embed())
            
            try:
                server = database.add_server(server)
            except Exception as e:
                await interaction.response.send_message(f"Fail to add the server `{query_param['host']}:{query_param['port']}`. Please try again.")
                Logger.error(f"Fail to add the server {query_param['host']}:{query_param['port']} {e}")
                return
            
            await interaction.response.defer()
            await refresh_channel_messages(interaction.channel.id, resend=True)
        else:
            await interaction.response.send_message(content='Query successfully!', embed=style.embed())
        
    modal.on_submit = modal_on_submit
    
    return modal

@tree.command(name='queryserver', description='Query server', guilds=guilds)
@app_commands.check(custom_command_query_check)
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_except_administrator)
async def command_query(interaction: Interaction, game_id: str):
    """Query server"""
    Logger.command(interaction, game_id)
    
    if game := await find_game(interaction, game_id):
        await interaction.response.send_modal(modal(game['id'], False))

@tree.command(name='addserver', description='Add server in current channel', guilds=guilds)
@app_commands.check(is_administrator)
async def command_addserver(interaction: Interaction, game_id: str):
    """Add server in current channel"""
    Logger.command(interaction, game_id)
    
    if not type(interaction.channel) == discord.TextChannel:
        await interaction.response.send_message(f'Command only supports text channel.', ephemeral=True)
        return

    if game := await find_game(interaction, game_id):
        if public:
            limit = int(os.getenv('APP_PUBLIC_SERVER_LIMIT', 10))
            
            if len(database.all_servers(guild_id=interaction.guild.id)) > limit:
                await interaction.response.send_message(f'The server quota has been exceeded. Limit: {limit}', ephemeral=True)
                return
        
        await interaction.response.send_modal(modal(game['id'], True))

@tree.command(name='delserver', description='Delete server in current channel', guilds=guilds)
@app_commands.check(is_administrator)
async def command_delserver(interaction: Interaction, address: str, query_port: int):
    """Delete server in current channel"""
    Logger.command(interaction, address, query_port)
    
    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer(thinking=True)
        database.delete_server(server)
        await refresh_channel_messages(interaction.channel.id, resend=True)

@tree.command(name='refresh', description='Refresh servers\' messages in current channel', guilds=guilds)
@app_commands.check(is_administrator)
async def command_refresh(interaction: Interaction):
    """Refresh servers\' messages in current channel"""
    Logger.command(interaction)
    
    await interaction.response.defer(thinking=True)
    await refresh_channel_messages(interaction.channel.id, resend=True)
    
@tree.command(name='factoryreset', description='Delete all servers in current guild', guilds=guilds)
@app_commands.check(is_administrator)
async def command_factoryreset(interaction: Interaction):
    """Delete all servers in current guild"""
    Logger.command(interaction)
    
    button = Button(style=ButtonStyle.red, label='Delete all servers')
    
    async def button_callback(interaction: Interaction):
        servers = database.all_servers(guild_id=interaction.guild.id)
        database.factory_reset(interaction.guild.id)
        await asyncio.gather(*[delete_message(server) for server in servers])
    
    button.callback = button_callback
    
    view = View()
    view.add_item(button)
    
    await interaction.response.send_message(content='Are you sure you want to delete all servers in current guild? This cannot be undone.', view=view, ephemeral=True)
    
@tree.command(name='moveup', description='Move the server message upward', guilds=guilds)
@app_commands.check(is_administrator)
async def command_move_up(interaction: discord.Interaction, address: str, query_port: int):
    """Move the server message upward"""
    Logger.command(interaction, address, query_port)

    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer(thinking=True)
        database.modify_server_position(server, True)
        await refresh_channel_messages(interaction.channel.id, resend=False)
        await interaction.delete_original_response()
    
@tree.command(name='movedown', description='Move the server message downward', guilds=guilds)
@app_commands.check(is_administrator)
async def command_move_down(interaction: discord.Interaction, address: str, query_port: int):
    """Move the server message downward"""
    Logger.command(interaction, address, query_port)
    
    if server := await find_server(interaction, address, query_port):
        await interaction.response.defer(thinking=True)
        database.modify_server_position(server, False)
        await refresh_channel_messages(interaction.channel.id, resend=False)
        await interaction.delete_original_response()

@tree.command(name='changestyle', description='Change server message style', guilds=guilds)
@app_commands.check(is_administrator)
async def command_change_style(interaction: discord.Interaction, address: str, query_port: int):
    """Change server message style"""
    Logger.command(interaction, address, query_port)
    
    if server := await find_server(interaction, address, query_port):
        style = styles.get(server.style_id, styles['Medium'])(server)
        options = []

        for id in styles:
            s = styles[id](server)
            options.append(SelectOption(label=s.display_name, value=id, description=s.description, emoji=s.emoji, default=id==style.id))
        
        select = Select(options=options)
        
        async def select_callback(interaction: Interaction):
            if select.values[0] not in styles:
                return

            await interaction.response.defer(thinking=True)
            server.style_id = select.values[0]
            database.update_server_style_id(server)
            await refresh_channel_messages(interaction.channel.id, resend=False)
            await interaction.delete_original_response()
        
        select.callback = select_callback
        view = View()
        view.add_item(select)
        
        await interaction.response.send_message(content=f'`{server.address}:{server.query_port}` Current style:', view=view, ephemeral=True)

@tree.command(name='editstyledata', description='Edit server message style data', guilds=guilds)
@app_commands.check(is_administrator)
async def command_edit_style_data(interaction: discord.Interaction, address: str, query_port: int):
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
            server.style_data = {k: str(v) for k, v in edit_fields.items()}
            database.update_server_style_data(server)
            await refresh_channel_messages(interaction.channel.id, resend=False)
        
        modal.on_submit = modal_on_submit
        
        await interaction.response.send_modal(modal)
    
@command_query.error
@command_addserver.error
@command_delserver.error
@command_refresh.error
@command_move_up.error
@command_move_down.error
@command_change_style.error
@command_edit_style_data.error
async def command_error_handler(interaction: Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message('You don\'t have sufficient privileges to use this command', ephemeral=True)
    else:
        Logger.error(str(error))
#endregion

#region Application functions
async def find_game(interaction: Interaction, game_id: str):
    """Find game by game_id, return """
    try:
        game = gamedig.find(game_id)
        return game
    except LookupError:
        await interaction.response.send_message(f'{game_id} is not a valid game id', ephemeral=True)
        return None

async def find_server(interaction: Interaction, address: str, query_port: int):
    """Find server by channel id, and return server"""
    try:
        server = database.find_server(interaction.channel.id, address, query_port)
        return server
    except database.ServerNotFoundError:
        await interaction.response.send_message('The server does not exist in the channel', ephemeral=True)
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
        messages[server.message_id] = await channel.fetch_message(server.message_id)
        return messages[server.message_id]
    except discord.NotFound as e:
        # The specified message was not found.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.NotFound {e}')
        server.message_id = None
        database.update_servers_message_id([server])
    except discord.Forbidden as e:
        # You do not have the permissions required to get a message.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.Forbidden {e}')
    except discord.HTTPException as e:
        # Retrieving the message failed.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] fetch_message discord.HTTPException {e}')

    return None

async def refresh_channel_messages(channel_id: int, resend: bool):
    servers = database.all_servers(channel_id=channel_id)
    
    if not resend:
        await asyncio.gather(*[edit_message(chunks) for chunks in database.all_channels_servers(servers).values()])
        return
    
    channel = client.get_channel(channel_id)
    await channel.purge(check=lambda m: m.author==client.user)
    
    for chunks in to_chunks(servers, 10):
        try:
            message = await channel.send(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in chunks])
        except discord.Forbidden as e:
            # You do not have the proper permissions to send the message.
            Logger.error(f'Channel {channel_id} send_message discord.Forbidden {e}')
            break
        except discord.HTTPException as e:
            # Sending the message failed.
            Logger.error(f'Channel {channel_id} send_message discord.HTTPException {e}')
            break
        
        for server in chunks:
            server.message_id = message.id
        
        messages[message.id] = message
    
    database.update_servers_message_id(servers)

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
#endregion

#region Application tasks
@tasks.loop(seconds=float(os.getenv('TASK_EDIT_MESSAGE', 60)))
async def edit_messages():
    """Edit messages (Scheduled)"""
    messages_servers = database.all_messages_servers()
    message_ids = [*messages_servers]
    Logger.debug(f'Edit messages: Tasks = {len(message_ids)} messages')
    
    results = []
    
    # Rate limit: 50 requests per second
    for chunks in to_chunks(message_ids, 50):
        results += await asyncio.gather(*[edit_message(messages_servers[message_id]) for message_id in chunks])
        await asyncio.sleep(1)
    
    success = sum(result == True for result in results)
    failed = len(results) - success
    Logger.info(f'Edit messages: Total = {len(results)}, Success = {success}, Failed = {failed} ({success and int(failed / len(results) * 100) or 0}% fail)')
    
async def edit_message(servers: list[Server]):
    if len(servers) <= 0:
        return True
    
    message = await fetch_message(servers[0])
    
    if message is None:
        channel = client.get_channel(servers[0].channel_id)
        
        if channel is None:
            Logger.error(f'Send messages: discord.Forbidden channel not found ({servers[0].channel_id})')
            return False
    
        try:
            message = await channel.send(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in servers])
            Logger.debug(f'Send messages: {message}')
        except discord.Forbidden as e:
            # You do not have the proper permissions to send the message.
            Logger.error(f'Send messages: discord.Forbidden {e}')
            return False
        except discord.HTTPException as e:
            # Sending the message failed.
            Logger.error(f'Send messages: discord.HTTPException {e}')
            return False
        
        messages[message.id] = message
        database.update_servers_message_id(servers)
        return True
    
    try:
        message = await message.edit(embeds=[styles.get(server.style_id, styles['Medium'])(server).embed() for server in servers])
        Logger.debug(f'Edit messages: {message.id} success')
        return True
    except discord.Forbidden as e:
        # Tried to suppress a message without permissions or edited a message's content or embed that isn't yours.
        Logger.debug(f'Edit messages: {message.id} edit_messages discord.Forbidden {e}')
        return False
    except discord.HTTPException as e:
        # Editing the message failed.
        Logger.debug(f'Edit messages: {message.id} edit_messages discord.HTTPException {e}')
        return False

@tasks.loop(seconds=float(os.getenv('TASK_QUERY_SERVER', 60)))
async def query_servers():
    """Query servers (Scheduled)"""
    distinct_servers = database.distinct_servers()
    Logger.debug(f'Query servers: Tasks = {len(distinct_servers)} unique servers')

    with ThreadPoolExecutor() as executor:
        servers, success, failed = await asyncio.get_event_loop().run_in_executor(executor, query_servers_func, distinct_servers)
        
    database.update_servers(servers) 
    Logger.info(f'Query servers: Total = {len(servers)}, Success = {success}, Failed = {failed} ({len(servers) > 0 and int(failed / len(servers) * 100) or 0}% fail)')
    
def query_servers_func(distinct_servers: list[Server]):
    """Query servers with ThreadPoolExecutor"""
    with ThreadPoolExecutor() as executor:
        servers: list[Server] = []
        success = 0
        
        for i, server in enumerate(executor.map(query_server, distinct_servers)):
            Logger.debug(f'Query servers: {i + 1}/{len(distinct_servers)} ({server.game_id})[{server.address}:{server.query_port}] success: {server.status}')
            servers.append(server)
            success += 0 if not server.status else 1

    return servers, success, len(servers) - success

def query_server(server: Server):
    """Query server"""
    try:
        server.result = gamedig.query(server)
        server.status = True
    except:
        server.status = False
        
    return server

@tasks.loop(minutes=5)
async def presence_update():
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

    with open('public/static/guilds.json', 'w', encoding='utf-8') as f:
        json.dump(guilds, f, ensure_ascii=False)
        
@tasks.loop(minutes=5)
async def heroku_query():
    """Heroku - Prevent a web dyno from sleeping"""
    url = f"https://{os.environ['HEROKU_APP_NAME']}.herokuapp.com"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        Logger.debug(f'Sends a GET request to {url}')
    except Exception as e:
        Logger.error(f'Sends a GET request to {url}, {e}')
#endregion

if __name__ == '__main__':
    client.run(os.environ['APP_TOKEN'])
