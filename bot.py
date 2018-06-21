import json
import os
import random
import sys

from discord.ext.commands import Bot
from discord.ext import commands
from discord import Game
from Settings import Settings
from analyzer import Analyzer

BOT_PREFIX = ("~", "?")
client = Bot(command_prefix=BOT_PREFIX)
analyzer = Analyzer(client)
auth_file = 'auth.json'

settings = Settings()


@client.command(name='relay', help="Relays the current world data", pass_context=True)
async def relay(ctx):
    channel = ctx.message.channel
    if channel.name in settings.channels:
        await analyzer.relay(channel)


@client.command(name='reset', help='Refreshes current world data. If you are found abusing, you will be removed.',
                aliases=['clear', 'erase', 'empty', 'wipe', 'destroy'], pass_context=True)
@commands.has_any_role(*settings.ranks)
async def reset(ctx):
    channel = ctx.message.channel
    possible_replies = [
        'abolished',
        'obliterated',
        'annihilated',
        'eliminated',
        'removed',
        'cleared',
        'erased',
        'emptied,'
        'nulled',
        'terminated',
        'eradicated',
        'negated',
        'undone',
        'wiped'
        'destroyed'
    ]
    if channel.name in settings.channels:
        analyzer.reset()
        response = "World data has been {}.".format(random.choice(possible_replies))
        await client.send_message(channel, response)
        await analyzer.relay(channel)


@client.command(name='stop', help='Stops bot vigorously. Works only with Staff rank.', pass_context=True)
@commands.has_any_role(*settings.ranks)
async def stop(ctx):
    print("Attempting to stop")
    analyzer.save()
    await client.logout()
    exit(0)


@client.command(name='commands', help='Lists commands for calling/scouting.')
async def commands():
    await client.say("To add a world to queue: `w[#] [number of plinths]`.\n"
                     "Example: `w59 4` or `14 2.`\n"
                     "**Note:** Only works in #calls channel.\n\n"
                     "To declare a core: `w[#] [core name]`.\n"
                     "Example: `w12 cres` or `42 seren`.\n"
                     "Aliases for core names are shown here: `['cres', 'c', 'sword', 'edicts', 'sw', 'juna', 'j', "
                     "'seren', 'se', 'aagi', 'a']`.\n "
                     "**Note:** Only works in #calls channel.\n\n"
                     "To delete a world from queue: `w[#] [0, d, dead, or gone]`.\n"
                     "Example: `w103 d` or `56 0`\n"
                     "**Note:** Only works in #calls channel.\n\n"
                     "To get a list of current ranks in the friends chat: `?ranks`.\n"
                     "Example: `?ranks`\n"
                     "**Note:** Only works in #bots channel.\n\n"
                     "To get information about the friends chat: `?info`\n"
                     "Example: `?info`\n"
                     "**Note:** Only works in #bots channel.\n\n")


@client.command(name='info', help='Lists FC info.', pass_context=True)
async def info(ctx):
    channel = ctx.message.channel.name
    if channel == 'bots' or channel == 'bottom-secret':
        await client.say("This will say FC info! Eventually.")
    else:
        pass


@client.command(name='ranks', help='Lists current FC ranks.', pass_context=True)
async def ranks(ctx):
    channel = ctx.message.channel.name
    if channel == 'bots' or channel == 'bottom-secret':
        await client.say("```"
                         "Blue Raivyn  - General\n"
                         "Sscared      - General\n"
                         "Wokkafumpe   - General\n"
                         "Bomy         - General\n"
                         "Insulate     - General\n"
                         "WealthRS     - Captain\n"
                         "DTP          - Captain\n"
                         "Pur          - Captain\n"
                         "Z oD         - Captain\n"
                         "Legend-ary   - Captain\n"
                         "HuntrMetroid - Captain"
                         "```")
    else:
        pass


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="Hall of Memories"))
    print('Connected!')
    print('Username: ' + client.user.name)
    print('ID: ' + client.user.id)

    server = [x for x in client.servers if x.name == settings.servers[0]][0]
    bot_only_channel = [x for x in server.channels if x.name == settings.bot_only_channel][0]

    await analyzer.relay(bot_only_channel)


mainMessage = None


@client.event
async def on_message(message):
    # Check if it's not our own message, don't want infinite loops
    if message.author == client.user:
        return

    if message.content == "!stop":
        await client.logout()
        sys.exit(0)

    print("Received message {} in channel {} from {}".format(message.content, message.channel, message.author.name))
    # Check if we are in the right channel
    if message.channel.name not in settings.channels:
        return

    if message.server.name not in settings.servers:
        return

    await client.process_commands(message)

    # Analyse the message
    await analyzer.analyze_call(message)


@client.event
async def on_command_error(ctx, error):
    print("Rip, error {}".format(error))


if not os.path.exists(auth_file):
    print("no auth json found, please create one")

with open(auth_file) as f:
    auth_data = json.load(f)
client.run(auth_data['token'])
