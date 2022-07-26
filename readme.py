import discord
from main import tree
from service import public, guilds, gamedig
import operator


def main():
    """Generate README.md"""
    text = f'''# Discord Game Server Monitor
📺 Monitor your game servers on Discord and tracks the live data of your game servers.
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

Download discord.py 2.0 manually
```
git clone https://github.com/Rapptz/discord.py
cd discord.py
py -m pip install -U .[voice]
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
