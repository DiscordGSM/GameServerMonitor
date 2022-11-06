import json
import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from discordgsm.database import Database
from discordgsm.main import tree
from discordgsm.service import gamedig, invite_link, public, whitelist_guilds
from discordgsm.translator import Locale, translations
from discordgsm.version import __version__

load_dotenv()

app = Flask(__name__, static_url_path='', static_folder='public/static', template_folder='public')
cmd = [command.to_dict() for command in tree.get_commands(guild=None if public or len(whitelist_guilds) <= 0 else whitelist_guilds[0])]


@app.route('/')
def index():
    show_alert = False
    heroku_app_name = ''

    if match := re.search(r':\/\/([a-z|\d|-]+)\.herokuapp\.com', request.base_url):
        heroku_app_name = match.groups()[0]

        if os.getenv('HEROKU_APP_NAME').strip() != heroku_app_name:
            show_alert = True

    return render_template('index.html', invite_link=invite_link, show_alert=show_alert, heroku_app_name=heroku_app_name)


if os.getenv('WEB_API_ENABLE', '').lower() == 'true':
    @app.route('/api/v1/games')
    def games():
        return jsonify(gamedig.games)

    @app.route('/api/v1/info')
    def info():
        return jsonify({
            'version': __version__,
            'invite_link': invite_link,
            'statistics': Database().statistics(),
        })

    @app.route('/api/v1/commands')
    def commands():
        return jsonify(cmd)

    @app.route('/api/v1/locales')
    @app.route('/api/v1/locales/<locale>')
    def locales(locale: str = 'en-US'):
        if locale in translations:
            return jsonify(translations[locale])
        else:
            return jsonify({'error': 'Invalid locale', 'locales': [str(value) for value in Locale]})

    @app.route('/api/v1/guilds')
    def guilds():
        with open('public/static/guilds.json', 'r', encoding='utf-8') as f:
            data = json.loads(f.read())

        return jsonify(data)

    @app.route('/api/v1/servers')
    def servers():
        return jsonify(Database().all_servers(filter_secret=True))

    @app.route('/api/v1/channels')
    @app.route('/api/v1/channels/<channel_id>')
    def channels(channel_id: str = None):
        if channel_id is not None and not channel_id.isdigit():
            return jsonify({'error': 'Invalid channel id'})

        database = Database()

        if channel_id is None:
            servers = database.all_servers(filter_secret=True)
            return jsonify(database.all_channels_servers(servers))

        return jsonify(database.all_servers(channel_id=int(channel_id), filter_secret=True))

if __name__ == '__main__':
    app.run(debug=os.getenv('APP_DEBUG', '').lower() == 'true')
