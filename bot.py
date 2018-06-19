import json
import os

from discord.ext.commands import Bot
from discord.ext import commands
from discord import Game
from analyzer import Analyzer

BOT_PREFIX = ("~", "?")
client = Bot(command_prefix=BOT_PREFIX)
analyzer = Analyzer()
auth_file = 'auth.json'


@client.command(name='reset', help='Refreshes current world data.')
async def reset():
    my_list = list(analyzer.worlds.items())
    for key, value in my_list:
        value[0] = 0
        value[1] = 0


@client.command(name='stop', help='Stops bot vigorously. Works only with Staff rank.')
@commands.has_any_role('Staff')
async def stop():
    await client.logout()
    exit(0)


@client.command(name='commands', help='Lists commands for calling/scouting.')
async def commands():
    await client.say("To add a world to queue: `w[#] [number of plinths]`.\n"
                     "Example: `w59 4` or `14 2.`\n\n"
                     "To declare a core: `w[#] [core name]`.\n"
                     "Example: `w12 cres` or `42 seren`.\n"
                     "Aliases for core names are shown here: `['cres', 'c', 'sword', 'edicts', 'sw', 'juna', 'j', 'seren', 'se', 'aagi', 'a']`.\n\n"
                     "To delete a world from queue: `w[#] [0, d, dead, or gone]`.\n"
                     "Example: `w103 d` or `56 0`\n\n")


@client.command(name='info', help='Lists FC info.')
async def info():
    await client.say("This will say FC info! Eventually.")


@client.command(name='ranks', help='Lists current FC ranks.')
async def ranks():
    await client.say("This will display current FC ranks if Insulate wasn't being such a slow ass and gave them to me.")


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="Hall of Memories"))
    print('Connected!')
    print('Username: ' + client.user.name)
    print('ID: ' + client.user.id)
    await start_thread()


mainMessage = None


@client.event
async def on_message(message):
    # Check if we are in the right channel
    if message.channel != channel:
        return

    # Check if it's not our own message, don't want infinite loops
    if message.author == client.user:
        return

    await client.process_commands(message)

    # Analyse the message
    ret = analyzer.analyze_call(message.content)

    # and send it
    if ret is not None:
        await client.send_message(channel, ret)


async def start_thread():
    global mainMessage, channel, newMessage
    newMessage = True
    mainMessage = None
    server = [server for server in client.servers if server.name == "Core Hunting"][0]
    channel = [channel for channel in server.channels if channel.name == "bottom-secret"][0]


async def send_message(message):
    global channel
    await client.send_message(channel, message)

if not os.path.exists(auth_file):
    print("no auth json found, please create one")

with open(auth_file) as f:
    auth_data = json.load(f)
client.run(auth_data['token'])
