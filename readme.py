import discord
from main import tree
from service import public, guilds, gamedig
import operator


def main():
    """Generate README.md"""
    text = f'''# Discord Game Server Monitor
[![Open Source Love svg1](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/DiscordGSM/GameServerMonitor/)
[![GitHub license](https://img.shields.io/github/license/GameServerMonitor/DiscordGSM.svg)](https://github.com/DiscordGSM/GameServerMonitor/blob/master/LICENSE)
[![GitHub release](https://img.shields.io/github/release/GameServerMonitor/DiscordGSM.svg)](https://github.com/DiscordGSM/GameServerMonitor/releases/)
[![Discord Shield](https://discordapp.com/api/guilds/680159496584429582/widget.png?style=shield)](https://discord.gg/Cg4Au9T)

📺 Monitor your game servers on Discord and tracks the live data of your game servers.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/amjCni?referralCode=DylKEu)
'''

    with open('README.md', 'w', encoding='utf-8') as fp:
        fp.write(text + available_commands() + supported_games() + developer_notes())

def available_commands():
    commands = tree.get_commands(guild=None if public else guilds[0], type=discord.AppCommandType.chat_input)
    header = f'\n## Available Commands\n{len(commands)} commands are available.'
    table = '\n| Command | Description |\n| - | - |\n'

    for command in sorted(commands, key=operator.attrgetter('name')):
        params_string = ' '.join([f'`{param.name}`' for param in command._params.values()])
        table += f"| **/{command.name}** {params_string} | {command.description} |\n"
        
    return header + table

def supported_games():
    header = f'\n## Supported Games\n{len(gamedig.games)} game servers are supported.'
    table = '\n| Game Id | Name | Add server slash command |\n| - | - | - |\n'
    
    for game_id, game in gamedig.games.items():
        table += f"| {game_id} | {game['fullname']} | `/addserver {game_id}` |\n"
        
    return header + table

def developer_notes():
    header = '\n## Developer Notes'
    return header + '''
venv commands
```
py -m venv venv
venv\\Scripts\\activate.bat
deactivate
```

Run Flask locally
```
py -m pip install Flask
set FLASK_ENV=development
set FLASK_APP=app:app
flask run
```
'''

if __name__ == '__main__':
    main()
