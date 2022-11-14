import os

from discordgsm import client

if __name__ == '__main__':
    client.run(os.environ['APP_TOKEN'])
