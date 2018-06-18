import json
import os
import discord

from discord import Game
from analyzer import Analyzer

client = discord.Client()
analyzer = Analyzer()
auth_file = 'auth.json'


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

    if message.content == '!stop':
        await client.logout()
        exit(0)

    # Analyse the message
    ret = analyzer.analyze_call(message.content)

    # and send it
    send_message(ret)


async def start_thread():
    global mainMessage, channel, newMessage
    newMessage = True
    mainMessage = None
    server = [server for server in client.servers if server.name == "Core Hunting"][0]
    channel = [channel for channel in server.channels if channel.name == "bottom-secret"][0]


async def send_message(message):
    global channel
    if message:
        await client.send_message(channel, message)

if not os.path.exists(auth_file):
    print("no auth json found, please create one")

with open(auth_file) as f:
    auth_data = json.load(f)
client.run(auth_data['token'])
