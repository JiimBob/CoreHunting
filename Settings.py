import json


class Settings:

    def __init__(self, settings_file='settings.json'):
        with open(settings_file) as f:
            settings = json.load(f)
        self.channels = settings['channels']
        self.servers = settings['servers']
        self.ranks = settings['ranks']
        self.bot_only_channel = settings['bot-only-channel']
