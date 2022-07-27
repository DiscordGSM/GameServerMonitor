import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests
from dotenv import load_dotenv

import discord
from discord import (ActivityType, AutoShardedClient, ButtonStyle, Client,
                     Interaction, Message, SelectOption, app_commands)
from discord.ext import tasks
from discord.ui import Button, Modal, Select, TextInput, View
from logger import Logger
from server import Server
from service import database, gamedig, guilds, invite_link, public
from styles import Style

load_dotenv()

messages: dict[int, Message] = {}
styles = {style.__name__: style for style in Style.__subclasses__()}

intents = discord.Intents.default()
shard_ids = [int(shard_id) for shard_id in os.getenv('APP_SHARD_IDS').replace(';', ',').split(',') if shard_id] if len(os.getenv('APP_SHARD_IDS', '')) > 0 else None
shard_count = int(os.getenv('APP_SHARD_COUNT', 1))
client = Client(intents=intents) if not public else AutoShardedClient(intents=intents, shard_ids=shard_ids, shard_count=shard_count)

@client.event
async def on_ready():
    await client.wait_until_ready()
    
    Logger.info(f'Logged on as {client.user}')
    Logger.info(f'Invite link: {invite_link}')
    
    await sync_commands()
    query_servers.start()
    edit_messages.start()
    presence_update.start()
    
    if os.getenv('WEB_ENABLE_API', '').lower() == 'true':
        cache_guilds.start()
        
    if os.getenv('HEROKU_APP_NAME') is not None:
        heroku_query.start()

async def sync_commands():
    """Syncs the application commands to Discord.""" 
    if not public:
        for guild in guilds:
            await tree_sync(guild)
                
        # Remove global commands
        tree.clear_commands(guild=None)
        
    await tree_sync()
                
async def tree_sync(guild=None):
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

tree = app_commands.CommandTree(client)

def modal(game_id: str, save: bool):
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
    # elif game_id == 'terraria' or game_id == 'tshock':
    #     query_extra['token'] = TextInput(label='REST user token')
    #     modal.add_item(query_extra['token'])
    
    async def modal_on_submit(interaction: Interaction):
        if save:
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
        
        if save:
            try:
                server = database.add_server(server)
            except Exception as e:
                await interaction.response.send_message(f"Fail to add the server `{query_param['host']}:{query_param['port']}`. Please try again.")
                Logger.error(f"Fail to add the server {query_param['host']}:{query_param['port']} {e}")
                return
        
            await interaction.response.defer()
            await send_message(server, True)
        else:
            style = styles.get(server.style_id, styles['Medium'])(server)
            await interaction.response.send_message(content=style.content(), embed=style.embed(), view=style.view())
        
    modal.on_submit = modal_on_submit
    
    return modal

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

@tree.command(name='queryserver', description='Query server', guilds=guilds)
@app_commands.check(custom_command_query_check)
@app_commands.checks.dynamic_cooldown(cooldown_for_everyone_except_administrator)
async def command_query(interaction: Interaction, game_id: str):
    """Query server"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 

    # Check game_id exists
    try:
        game = gamedig.find(game_id)
    except LookupError:
        await interaction.response.send_message(f'{game_id} is not a valid game id', ephemeral=True)
        return
    
    await interaction.response.send_modal(modal(game['id'], False))

@tree.command(name='addserver', description='Add server in current channel', guilds=guilds)
@app_commands.check(is_administrator)
async def command_addserver(interaction: Interaction, game_id: str):
    """Add server in current channel"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    
    # Check game_id exists
    try:
        game = gamedig.find(game_id)
    except LookupError:
        await interaction.response.send_message(f'{game_id} is not a valid game id', ephemeral=True)
        return
    
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
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    
    await interaction.response.defer(thinking=True)
    
    try:
        server = database.find_server(interaction.channel.id, address, query_port)
    except database.ServerNotFoundError:
        await interaction.response.send_message('The server does not exist in the channel', ephemeral=True)
        return

    database.delete_server(server)
    await delete_message(server)
    await interaction.delete_original_message()

@tree.command(name='refresh', description='Refresh servers\' messages in current channel', guilds=guilds)
@app_commands.check(is_administrator)
async def command_refresh(interaction: Interaction):
    """Refresh servers\' messages in current channel"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    await interaction.response.defer(thinking=True)
    servers = database.all_servers(channel_id=interaction.channel.id)
    await delete_messages(servers)
    await send_messages(servers)
    await interaction.delete_original_message()
    
@tree.command(name='factoryreset', description='Delete all servers in current guild', guilds=guilds)
@app_commands.check(is_administrator)
async def command_factoryreset(interaction: Interaction):
    """Delete all servers in current guild"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    
    button = Button(style=ButtonStyle.red, label='Delete all servers')
    
    async def button_callback(interaction: Interaction):
        servers = database.all_servers(guild_id=interaction.guild.id)
        database.factory_reset(interaction.guild.id)
        await delete_messages(servers)
    
    button.callback = button_callback
    
    view = View()
    view.add_item(button)
    
    await interaction.response.send_message(content='Are you sure you want to delete all servers in current guild? This cannot be undone.', view=view, ephemeral=True)
    
@tree.context_menu(name='Move Upward', guilds=guilds)
@app_commands.check(is_administrator)
async def context_menu_move_up(interaction: discord.Interaction, message: discord.Message):
    """Move the server message upward"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    await interaction.response.defer(thinking=True)
    await asyncio.gather(*[edit_message(server) for server in database.modify_server_position(interaction.channel.id, message.id, True)])    
    await interaction.delete_original_message()
    
@tree.context_menu(name='Move Downward', guilds=guilds)
@app_commands.check(is_administrator)
async def context_menu_move_down(interaction: discord.Interaction, message: discord.Message):
    """Move the server message downward"""
    await interaction.response.defer(thinking=True)
    await asyncio.gather(*[edit_message(server) for server in database.modify_server_position(interaction.channel.id, message.id, False)])
    await interaction.delete_original_message()
    
@tree.context_menu(name='Delete Server', guilds=guilds)
@app_commands.check(is_administrator)
async def context_menu_delete_server(interaction: discord.Interaction, message: discord.Message):
    """Delete server in current channel"""
    Logger.info(f'{interaction.guild.name}({interaction.guild.id}) #{interaction.channel.name}({interaction.channel.id}) {interaction.user.name}({interaction.user.id}): /{interaction.command.name}') 
    await interaction.response.defer(thinking=True)
    
    try:
        server = database.find_server(interaction.channel.id, message_id=message.id)
    except database.ServerNotFoundError:
        await interaction.delete_original_message()
        return
    
    database.delete_server(server)
    await delete_message(server)
    await interaction.delete_original_message()

@tree.context_menu(name='Change Style', guilds=guilds)
@app_commands.check(is_administrator)
async def context_menu_change_style(interaction: discord.Interaction, message: discord.Message):
    try:
        server = database.find_server(interaction.channel.id, message_id=message.id)
    except database.ServerNotFoundError:
        await interaction.response.send_message('The server does not exist in the channel', ephemeral=True)
        return
    
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
        await edit_message(server)
        await interaction.delete_original_message()
    
    select.callback = select_callback
    
    button = Button(label='Edit Style Data')
    
    async def button_callback(interaction: Interaction):
        await interaction.response.send_modal(style.edit_modal())
    
    button.callback = button_callback
    
    view = View()
    view.add_item(select)
    # view.add_item(button)
    
    await interaction.response.send_message(content=f'`{server.address}:{server.query_port}` Current style:', view=view, ephemeral=True)

@tree.context_menu(name='Edit Style Data', guilds=guilds)
@app_commands.check(is_administrator)
async def context_menu_edit_style_style(interaction: discord.Interaction, message: discord.Message):
    try:
        server = database.find_server(interaction.channel.id, message_id=message.id)
    except database.ServerNotFoundError:
        await interaction.response.send_message('The server does not exist in the channel', ephemeral=True)
        return
    
    style = styles.get(server.style_id, styles['Medium'])(server)
    modal = Modal(title=f'Edit {server.address}:{server.query_port}')
    edit_fields = style.default_edit_fields

    for item in edit_fields.values():
        modal.add_item(item)
        
    async def modal_on_submit(interaction: Interaction):
        await interaction.response.defer()
        server.style_data = {k: str(v) for k, v in edit_fields.items()}
        database.update_server_style_data(server)
        await edit_message(server)
    
    modal.on_submit = modal_on_submit
    
    await interaction.response.send_modal(modal)
    
@command_query.error
@command_addserver.error
@command_delserver.error
@command_refresh.error
@context_menu_move_up.error
@context_menu_move_down.error
@context_menu_delete_server.error
@context_menu_change_style.error
@context_menu_edit_style_style.error
async def command_error_handler(interaction: Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(str(error), ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message('You don\'t have sufficient privileges to use this command', ephemeral=True)
    else:
        Logger.error(str(error))

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

async def send_messages(servers: list[Server]):
    """Send messages"""
    for server in servers:
        await send_message(server)
        
    database.update_servers_message_id(servers)

async def send_message(server: Server, update_message_id: bool = False):
    """Send message"""
    channel = client.get_channel(server.channel_id)
    
    try:
        style = styles.get(server.style_id, styles['Medium'])(server)
        message = await channel.send(content=style.content(), embed=style.embed(), view=style.view())
    except discord.Forbidden as e:
        # You do not have the proper permissions to send the message.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] send_message discord.Forbidden {e}')
        return
    except discord.HTTPException as e:
        # Sending the message failed.
        Logger.error(f'({server.game_id})[{server.address}:{server.query_port}] send_message discord.HTTPException {e}')
        return
    
    server.message_id = message.id
    messages[message.id] = message
    
    if update_message_id:
        database.update_servers_message_id([server])

async def delete_messages(servers: list[Server]):
    """Delete messages"""
    await asyncio.gather(*[delete_message(server) for server in servers])
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

@tasks.loop(seconds=os.getenv('RR_EDIT_MESSAGE', 60))
async def edit_messages():
    """Edit messages (Scheduled)"""
    servers = database.all_servers()
    Logger.debug(f'Edit messages: Tasks = {len(servers)} messages')
    
    channels_servers = database.all_channels_servers(servers)
    results = await asyncio.gather(*[edit_message(server) for servers in channels_servers.values() for server in servers])
    
    success = sum(result == True for result in results)
    failed = len(results) - success
    Logger.info(f'Edit messages: Total = {len(results)}, Success = {success}, Failed = {failed} ({success and int(failed / len(results) * 100) or 0}% fail)')

async def edit_message(server: Server):
    """Edit message"""
    if server.message_id is None:
        Logger.debug(f'Edit messages: {server.message_id} ({server.game_id})[{server.address}:{server.query_port}] ignored')
        return None
    
    message = await fetch_message(server)
    
    if message is None:
        Logger.debug(f'Edit messages: {server.message_id} ({server.game_id})[{server.address}:{server.query_port}] ignored')
        return None

    try:
        style = styles.get(server.style_id, styles['Medium'])(server)
        message = await message.edit(content=style.content(), embed=style.embed(), view=style.view())
        Logger.debug(f'Edit messages: {server.message_id} ({server.game_id})[{server.address}:{server.query_port}] success')
        return True
    except discord.Forbidden as e:
        # Tried to suppress a message without permissions or edited a message's content or embed that isn't yours.
        Logger.debug(f'Edit messages: {server.message_id} ({server.game_id})[{server.address}:{server.query_port}] edit_messages discord.Forbidden {e}')
        return False
    except discord.HTTPException as e:
        # Editing the message failed.
        Logger.debug(f'Edit messages: {server.message_id} ({server.game_id})[{server.address}:{server.query_port}] edit_messages discord.HTTPException {e}')
        return False

@tasks.loop(seconds=os.getenv('RR_QUERY_SERVER', 60))
async def query_servers():
    """Query servers (Scheduled)"""
    distinct_servers = database.distinct_servers()
    Logger.debug(f'Query servers: Tasks = {len(distinct_servers)} unique servers')

    with ThreadPoolExecutor() as executor:
        servers, success, failed = await asyncio.get_event_loop().run_in_executor(executor, query_servers_sync, distinct_servers)
        
    database.update_servers(servers) 
    Logger.info(f'Query servers: Total = {len(servers)}, Success = {success}, Failed = {failed} ({len(servers) > 0 and int(failed / len(servers) * 100) or 0}% fail)')
    
def query_servers_sync(distinct_servers: list[Server]):
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

    with open('guilds.json', 'w', encoding='utf-8') as f:
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

if __name__ == '__main__':
    client.run(os.environ['APP_TOKEN'])
