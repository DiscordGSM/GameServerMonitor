from discordgsm import Logger, __version__, env

if __name__ == '__main__':
    Logger.info(f'Started Discord Game Server Monitor {__version__}')
    Logger.info('Thank you for using DiscordGSM, you may consider sponsoring us ♥. Github Sponsors: https://github.com/sponsors/DiscordGSM')

    token = str(env('APP_TOKEN')).strip()
    items = token.split('.')

    # A valid token should contains 2 dots and 3 items
    if len(items) != 3:
        Logger.critical('Improper token has been passed, please change APP_TOKEN to a valid token. Learn more: https://discordgsm.com/guide/how-to-get-a-discord-bot-token')
        exit(1)

    hmac_hide = '*' * len(items[2])  # Hide the secret
    Logger.debug(f'Static token: {items[0]}.{items[1]}.{hmac_hide}')

    # Run the bot
    from discordgsm.main import client, exit_signal
    client.run(token)

    exit_signal.set()
    Logger.info('Stopping Discord Game Server Monitor...')
