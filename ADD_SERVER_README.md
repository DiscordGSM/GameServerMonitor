# DiscordGSM Server Automation Script

Script for automating server additions to DiscordGSM's SQLite database.

## Requirements

- Python 3.9+
- SQLite3
- DiscordGSM's virtual environment
```bash
source /path/to/discordgsm/venv/bin/activate  # Linux/Mac
\path\to\discordgsm\venv\Scripts\activate     # Windows
```

## Basic Usage

```bash
python3 add_server.py \
    --guild_id YOUR_GUILD_ID \
    --channel_id YOUR_CHANNEL_ID \
    --game_id GAME_ID \
    --address SERVER_ADDRESS \
    --query_port QUERY_PORT
```

## Server Configuration Arguments

Required:
- `--guild_id`: Discord server ID
- `--channel_id`: Discord channel ID
- `--game_id`: Game identifier
- `--address`: Server address
- `--query_port`: Query port number

Optional:
- `--db_path`: Custom path to servers.db
- `--ignore-existing`: Continue on existing servers

## Style Configuration

Display styles:
- `--style`: Message style (ExtraSmall, Small, Medium, Large, ExtraLarge)

Customization:
- `--description`: Server description
- `--fullname`: Custom game name
- `--image_url`: Embed image URL
- `--thumbnail_url`: Embed thumbnail URL
- `--country`: Server country (Medium style)
- `--locale`: Translation locale (default: en-US)
- `--timezone`: Timestamp timezone (default: UTC)
- `--clock_format`: Time format (12/24)

## Game-Specific Authentication

Terraria:
- `--token`: REST token

SCPSL:
- `--account_id`: Account ID
- `--api_key`: API key

GPortal:
- `--server_id`: Server ID

TeamSpeak3:
- `--voice_port`: Voice port

Trackmania Nations Forever:
- `--username`: Query username
- `--password`: Query password

## Examples

Minecraft server with basic styling:
```bash
python3 add_server.py \
    --guild_id 123456789 \
    --channel_id 987654321 \
    --game_id minecraft \
    --address mc.example.com \
    --query_port 25565 \
    --style Large \
    --description "Our community Minecraft server" \
    --timezone "America/New_York"
```

TeamSpeak server with authentication:
```bash
python3 add_server.py \
    --guild_id 123456789 \
    --channel_id 987654321 \
    --game_id teamspeak3 \
    --address ts.example.com \
    --query_port 10011 \
    --voice_port 9987
```

## Ansible Integration

Use with `add_servers.yml` for automated deployments. Set `ignore_existing: true` to skip existing servers.