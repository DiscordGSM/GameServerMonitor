import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

from database import Database
from service import gamedig, invite_link
from version import __version__

load_dotenv()

app = Flask(__name__, static_url_path='', static_folder='public/static', template_folder='public')

@app.route('/')
def index():
    return render_template('index.html', invite_link=invite_link)

if os.getenv('WEB_ENABLE_API', '').lower() == 'true':
    @app.route('/games')
    def games():
        return jsonify(gamedig.games)
    
    @app.route('/info')
    def info():
        return jsonify({
            'version': __version__, 
            'invite_link': invite_link,
            'statistics': Database().statistics(),
        })
    
    @app.route('/guilds')
    def guilds():
        with open('guilds.json', 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
            
        return jsonify(data)

    @app.route('/servers')
    def servers():
        return jsonify(Database().all_servers())

    @app.route('/channels')
    @app.route('/channels/<channel>')
    def channels(channel: str = None):
        if channel is None:
            return jsonify(Database().all_channels_servers())
        
        if not channel.isdigit():
            return jsonify({'error': 'Invalid channel id'})
        
        channels_servers = Database().all_channels_servers()
        
        if not int(channel) in channels_servers:
            return jsonify({'error': 'Channel id does not exist'})
        
        return jsonify(channels_servers[int(channel)])

if __name__ == '__main__':
    app.run(debug=os.getenv('APP_DEBUG', '').lower() == 'true')
