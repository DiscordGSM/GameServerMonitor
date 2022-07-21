from gamedig import Gamedig

gamedig = Gamedig()

def main():
    """Generate README.md"""
    text = f'''# Game Server Monitor
📺 Monitor your game servers on Discord and tracks the live data of your game servers.

## Supported Games
{len(gamedig.games)} game servers are supported.

'''

    with open('README.md', 'w', encoding='utf-8') as fp:
        fp.write(text + supported_games_table() + developer_notes())

def supported_games_table():
    table = '''| Game Id | Name | Add server slash command |\n| - | - | - |\n'''
    
    for game_id, game in gamedig.games.items():
        table += f"| {game_id} | {game['fullname']} | `/addserver {game_id}`\n"
        
    return table

def developer_notes():
    return '''This file is generate by readme.py

```
py -m venv venv
venv\\Scripts\\activate.bat
py main.py
deactivate

git clone https://github.com/Rapptz/discord.py
cd discord.py
py -m pip install -U .[voice]

py st

py -m manage runserver

py -m pip install Flask
set FLASK_ENV=development
set FLASK_APP=app:app
flask run
```

'''

if __name__ == '__main__':
    main()
