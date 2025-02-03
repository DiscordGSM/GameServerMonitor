# DiscordGSM Server Automation Script

Command-line tool to automate adding game servers to DiscordGSM's SQLite database.

## Requirements

- Python 3.6+
- SQLite3
- Access to DiscordGSM's `servers.db` file
- **Important**: Must run in DiscordGSM's virtual environment
  ```bash
  source /path/to/discordgsm/venv/bin/activate  # Linux/Mac
  # or
  \path\to\discordgsm\venv\Scripts\activate     # Windows
  ```

## Installation

1. Save `add_server.py` to your desired location
2. Ensure you have write access to DiscordGSM's database directory

## Usage

### Command Line

```bash
python3 add_server.py \
    --guild_id YOUR_GUILD_ID \
    --channel_id YOUR_CHANNEL_ID \
    --game_id GAME_ID \
    --address SERVER_ADDRESS \
    --query_port QUERY_PORT \
    [--db_path PATH_TO_DB] \
    [--ignore-existing]
```

### Arguments

Required:
- `--guild_id`: Discord server (guild) ID
- `--channel_id`: Discord channel ID
- `--game_id`: Game identifier (e.g., "minecraft", "valheim")
- `--address`: Server address/hostname
- `--query_port`: Query port number

Optional:
- `--db_path`: Custom path to `servers.db` (defaults to `./data/servers.db`)
- `--ignore-existing`: Continue execution if server already exists

## Examples

Basic usage:
```bash
python3 add_server.py \
    --guild_id 123456789 \
    --channel_id 987654321 \
    --game_id minecraft \
    --address mc.example.com \
    --query_port 25565
```

Ignoring existing servers:
```bash
python3 add_server.py \
    --guild_id 123456789 \
    --channel_id 987654321 \
    --game_id valheim \
    --address valheim.example.com \
    --query_port 2457 \
    --ignore-existing
```

## Error Handling

- Validates database existence
- Checks for existing servers with same address and query port
- Provides detailed error messages including channel and game info for existing servers
- Returns exit code 1 on error unless `--ignore-existing` is set

## Ansible Integration

Use `add_servers.yml` for automated deployment:

```yaml
vars:
  ignore_existing: true  # Set to false to fail on existing servers
```

Key features:
- Database existence validation
- Optional failure on existing servers (`ignore_existing`)
- Detailed output summary
- Proper idempotency handling