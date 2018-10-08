import math
import os
import re
import ssl
import sys
import time
import random
import json
import asyncpg

from typing import Dict, List, Any


def parse_line(line):
    line = line.lower()
    line = re.sub("(?<=[a-z])(?=\\d)|(?<=\\d)(?=[a-z])|\\.", " ", line)
    line = re.sub("^(world|w)", "", line)
    line = line.replace("  ", " ")
    line = re.sub("(sword|edict)$", "sw", line)
    line = re.sub("( dead| gone| d)$", " 0", line)
    return line


_save_file = "saved_worlds.json"
_save_stats = "saved_stats.json"
_save_ranks = "ranks.json"
_save_bans = "bans.json"
_all_worlds = {1, 2, 4, 5, 6, 9, 10, 12, 14, 15, 16, 18, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32, 35, 36, 37, 39, 40,
               42, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
               73, 74, 76, 77, 78, 79, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 96, 98, 99, 100, 103, 104, 105, 114, 115,
               116, 117, 119, 123, 124, 134, 137, 138, 139, 140}
exp_table = {0: 0, 1: 83, 2: 174, 3: 276, 4: 388, 5: 512, 6: 650, 7: 801, 8: 969, 9: 1154, 10: 1358,
             11: 1584, 12: 1833, 13: 2107, 14: 2411, 15: 2746, 16: 3115, 17: 3523, 18: 3973, 19: 4470,
             20: 5018, 21: 5624, 22: 6291, 23: 7028, 24: 7842, 25: 2147483647}


def _get_special_worlds():
    eoc = "EOC only world, try to avoid"
    legacy = "Legacy only world, try to avoid"
    t1500 = "1500 total world"
    return {18: legacy, 115: legacy, 137: legacy, 52: "VIP world", 66: eoc, 106: eoc,
            96: "Quick chat world, try to avoid", 48: "2600 total world", 30: "2000 total world", 86: t1500, 114: t1500}


def _get_special_special_worlds():
    legacy = "Legacy only world, try to avoid"
    return {18: legacy, 115: legacy, 137: legacy, 52: "VIP world", 48: "2600 total world"}


_special_worlds = _get_special_worlds()
_special_special_worlds = _get_special_special_worlds()


def get_scout_level(scouts):
    for level in exp_table:
        if exp_table[level] >= scouts:
            return level


def get_core_name(argument):
    switcher = {
        'party': "Party",
        'p': "Party",
        'c': "Cres",
        'cres': "Cres",
        'sword': "Sword",
        'edicts': "Sword",
        'e': "Sword",
        'sw': "Sword",
        'juna': "Juna",
        'j': "Juna",
        'seren': "Seren",
        'se': "Seren",
        'aagi': "Aagi",
        'a': "Aagi",
    }
    return switcher.get(argument, "0")


MAPPING = {'Party': 0,
           'Cres': 1,
           'Sword': 2,
           'Juna': 3,
           'Seren': 4,
           'Aagi': 5,
           6: 6}


def _json_keys_to_str(x):
    if isinstance(x, dict):
        return {int(k): v for k, v in x.items()}
    return x


def _json_keys_to_dict(x):
    if isinstance(x, dict):
        return {str(k): v for k, v in x.items()}
    return x


class Analyzer:
    def __init__(self, client):
        self.worlds = {}
        self.scouts = {}  # current scouts with their assigned worlds
        self.ranks = []
        self.bans = []
        self.load()
        self.client = client
        self.table_messages = {}  # dict of tables with messages of the table

    async def analyze_call(self, message):
        # first split on comma/slash/|
        calls = re.split("[|,/]", message.content)
        # then loop over it
        for c in calls:
            parsed = parse_line(c)
            split = parsed.split()
            if len(split) != 2:
                return
            world = split[0]
            call = split[1]

            if not world.isdigit():
                return

            world = int(world)

            if world in _special_worlds:
                if str(message.channel.type) != "private":
                    await self.client.send_message(message.channel,
                                                   f"NOTE, w{world} is a {_special_worlds[world]}.")

            if world not in self.worlds:
                await self.client.send_message(message.channel, f"{world} is not a p2p english world.")
                return

            # clear worlds from scouts
            for scout in self.scouts:
                for to_be_scouted in self.scouts[scout]["worlds"]:
                    if to_be_scouted == world:
                        self.scouts[scout]["worlds"].remove(world)

            if call.isdigit():
                flints_filled = int(call)

                if 0 <= flints_filled <= 6:
                    # rescout worlds with more cores faster to stay on top of what is next
                    # extra time till rescout is 26 mins -4 min for each plinth
                    # for now this also includes 5/6 (this has 6 mins) if this gives a problem ill change it.
                    extra_time = (26 - flints_filled * 4) * 60
                    self.worlds[world] = (flints_filled, time.time(), time.time() + extra_time)
                    id = message.author.id
                    self.check_make_scout(id, message.author.name)
                    # self.scouts[id]["stats"][str(flints_filled) + "/6 calls"] += 1
                    self.scouts[id]["scouts"] += 1
                    scout_level = get_scout_level(self.scouts[id]["scouts"])
                    if self.scouts[id]["scout_level"] != scout_level:
                        self.scouts[id]["scout_level"] = scout_level
                        await self.client.send_message(message.channel,
                                                       f"{message.author.name} has leveled up in scouting! "
                                                       f"{message.author.name} is now level {scout_level} in scouting.")
            else:
                if str(call) in ['reset', 'r']:
                    return
                elif str(call) in ['party', 'p', 'cres', 'c', 'sword', 'edicts', 'sw', 'juna', 'j', 'seren', 'se',
                                   'aagi', 'a', 'e']:
                    core = str(call)
                    core = get_core_name(core.lower())
                    extra_time = 26 * 60  # default time till rescout on a 0/6 world
                    self.worlds[world] = (core, time.time(), time.time() + extra_time)
                    id = message.author.id
                    self.check_make_scout(id, message.author.name)
                    self.scouts[id]["calls"] += 1
            # else. check for cres/sword/juna/seren/aagi/reset etc
        # await self.savescouttodb(id)
        await self.saveworldtodb(world)
        await self.relay(message.channel)

    async def relay(self, channel):
        relay_message = self.get_table(True)
        for ch, msg in self.table_messages.items():
            if ch == channel:
                try:
                    await self.client.delete_message(self.table_messages[channel])
                except Exception as exc:
                    print('Error, passing. Exception: ' + str(exc))
                    pass
            else:
                await self.client.edit_message(msg, relay_message)

        if str(channel.type) != "private":
            self.table_messages[channel] = await self.client.send_message(channel, relay_message)

    def get_table(self, trim):
        active_list = [(k, v) for k, v in self.worlds.items() if self.is_ok(v[0], v[1])]
        next_list = [(k, v) for k, v in self.worlds.items() if
                     isinstance(v[0], int) and 7 > v[0] > 0]
        next_list_s = sorted(next_list, key=lambda v: (-v[1][0], v[1][1]))
        active_list_s = sorted(active_list, key=lambda v: (MAPPING[v[1][0]], -v[1][1]))
        n = max(len(next_list_s), len(active_list_s), 1)
        if trim:
            n = min(n, 10)
        table = "|   Active   |      Next      |\n"
        table += "-" * (3 + 12 + 16) + "\n"
        eoc_b = False
        legacy_b = False
        vip_b = False
        total_b = False
        qc_b = False
        for i in range(n):
            if i < len(active_list_s):
                (world, value) = active_list_s[i]
                s = "w" + str(world) + "(" + str(value[0]) + ")"
                length = len(s)
                s = " " * int(math.ceil(6 - length / 2)) + s + " " * int(math.floor(6 - length / 2))
                table += "|" + s + "|"
            else:
                table += "|" + " " * 12 + "|"
            if i < len(next_list_s):
                (world, value) = next_list_s[i]
                age = str(math.floor((time.time() - value[1]) / 60))
                s = "w" + str(world) + "(" + str(value[0]) + "/6) " + age + "m"
                if world in _special_worlds:
                    if str(_special_worlds[world]).find("total") != -1:
                        s = "*" + s
                        total_b = True
                    elif str(_special_worlds[world]).find("Legacy") != -1:
                        s = "!" + s
                        legacy_b = True
                    elif str(_special_worlds[world]).find("EOC") != -1:
                        s = "+" + s
                        eoc_b = True
                    elif str(_special_worlds[world]).find("VIP") != -1:
                        s = "#" + s
                        vip_b = True
                    elif str(_special_worlds[world].find("Quick") != -1):
                        s = "~" + s
                        qc_b = True
                length = len(s)
                s = " " * int(math.ceil(8 - length / 2)) + s + " " * int(math.floor(8 - length / 2))
                table += s + "|\n"
            elif i - 2 < len(next_list_s):
                table += " Nil, scout pls" + " " + "|\n"
            else:
                table += "" + " " * 16 + "|\n"
        if total_b:
            table += "* = world has total level req.\n"
        if legacy_b:
            table += "! = world is legacy only.\n"
        if eoc_b:
            table += "+ = world is eoc only.\n"
        if vip_b:
            table += "# = world is vip only.\n"
        if qc_b:
            table += "~ = world is quick chat only.\n"
        return "```" + table + "```"

    async def update_scout_stats(self):
        for id in self.scouts:
            self.check_make_scout(id, self.scouts[id]["name"])

    async def stats(self, channel, arg):
        scout_list = []
        if isinstance(arg, str):
            if arg in ["calls", "scouts", "scout_requests", "scout_level"]:
                sort_type = arg
                scout_list = sorted(self.scouts.items(), key=lambda x: x[1][sort_type], reverse=True)
            elif arg in ["name"]:
                sort_type = arg
                scout_list = sorted(self.scouts.items(), key=lambda x: x[1][sort_type], reverse=False)
            else:
                sort_type = "scouts"
                print(arg)
        response = "Here are all the stats of all the scouts: \n"
        for id, scout in scout_list[:10]:
            response += "{name}:   Scouts: `{scouts}`   Scout level: `{scout_level}`   Calls: `{calls}`    " \
                        "Scout Requests: `{scout_requests}`   Scout Level: `{scout_level}`   Current world list: " \
                        "`{worlds}` \n".format(**self.scouts[id])
        if len(response) > 1999:
            response = "Response reached max character limit and was removed. Let staff know of this issue."
        await self.client.send_message(channel, response)
        # make stats for scout mainly

    async def lookup(self, channel, *id):
        if len(id) >= 1 and len(id[0]) >= 1:
            if len(id[0][0]) > 3:
                if id[0][0][2] == "!":
                    id = id[0][0][3:-1]
                else:
                    id = id[0][0][2:-1]
        if id in self.scouts:
            response = "{name}:   Scouts: `{scouts}`   Scout level: `{scout_level}`   Calls: `{calls}`    " \
                       "Scout Requests: `{scout_requests}`   Scout Level: `{scout_level}`   Current world list: " \
                       "`{worlds}` \n".format(**self.scouts[id])
            await self.client.send_message(channel, response)
        else:
            await self.client.send_message(channel, "No stats available for this user.")

            # make stats for scout mainly

    # checks all field that a scout can use and makes them if not existent
    # add new stats on this list
    def check_make_scout(self, id, name):
        if id not in self.scouts:
            self.scouts[str(id)] = {}
        if "name" not in self.scouts[id]:
            self.scouts[id]["name"] = name
        if "calls" not in self.scouts[id]:
            self.scouts[id]["calls"] = 0
        if "scouts" not in self.scouts[id]:
            self.scouts[id]["scouts"] = 0
        if "scout_level" not in self.scouts[id]:
            self.scouts[id]["scout_level"] = 1
        if "scout_requests" not in self.scouts[id]:
            self.scouts[id]["scout_requests"] = 0
        if "worlds" not in self.scouts[id]:
            self.scouts[id]["worlds"] = []
        if "bot_mute" not in self.scouts[id]:
            self.scouts[id]["bot_mute"] = 0

    async def set_mute(self, channel, id, name, value):
        self.check_make_scout(id, name)
        self.scouts[id]["bot_mute"] = value
        await self.client.send_message(channel, f"{name} changed bot_mute.")

    async def reset_scout(self, channel, id, name):
        self.check_make_scout(id, name)
        extra_time = 0
        for world in self.scouts[id]["worlds"]:
            previous_call = self.worlds[world][0]
            previous_time = self.worlds[world][1]
            print(previous_call, previous_time)
            if type(previous_call) is int:  # temporary depending on your fix.
                extra_time = (26 - previous_call * 4) * 60
            self.worlds[world] = (previous_call, previous_time, previous_time + extra_time)
        self.scouts[id]["worlds"] = []
        await self.client.send_message(channel, f"{name} deleted their scout list.")

    # command = ?scout *amount
    # optional parameter amount can range from 1 to 10
    # tell s the user to scout a list of worlds
    async def get_scout_info(self, channel, author, username, args):
        id = author.id
        if id in self.scouts and len(self.scouts[id]["worlds"]) > 0:
            await self.client.send_message(channel,
                                           f"{username}, you still need to scout: {self.scouts[id]['worlds']} "
                                           f"Use `?resetscout` if you want to delete your list.")
            if self.scouts[id]["bot_mute"] == 0:
                await self.client.send_message(author,
                                               f"You still need to scout: {self.scouts[id]['worlds'] } "
                                               f"Use `?resetscout` if you want to delete your list.")
            return
        else:
            self.check_make_scout(id, username)
            self.scouts[id]["scout_requests"] += 1

        amount = 10
        if len(args) >= 1:
            if args[0].isdigit():
                amount = max(1, min(10, int(args[0])))
        all_worlds = [k for k, v in self.worlds.items() if time.time() - v[2] > 0]

        all_worlds = [world for world in all_worlds if world not in _special_special_worlds]

        if len(all_worlds) > 1:
            if amount > len(all_worlds):
                amount = len(all_worlds)
                i = 0
            else:
                i = random.randint(0, len(all_worlds) - amount)
            result = all_worlds[i:i + amount]
            worlds = all_worlds[i:i + amount]
            for j in range(i, i + amount):
                world = self.worlds[all_worlds[j]]
                extra_time = 15 * 60
                self.worlds[all_worlds[j]] = [world[0], world[1], time.time() + extra_time]

            response = "error getting worlds"
            if len(result) == 1:
                response = f"{username}, please scout world: {result[0]}."
            elif len(result) >= 2:
                response = f"{username}, please scout the following worlds: {result}."
            self.scouts[id]["worlds"] = worlds
            await self.client.send_message(channel, response)
            if self.scouts[id]["bot_mute"] == 0:
                await self.client.send_message(author, response)

    async def addban(self, username, channel):
        if username in self.bans:
            message = username + " is already on ban list."
            await self.client.send_message(channel, message)
            return
        self.bans.append(username)
        message = "Added '" + username + "' to ban list."
        await self.client.send_message(channel, message)
        self.saverb()

    async def removeban(self, username, channel):
        try:
            self.bans.remove(username)
        except ValueError:
            message = username + " is not on the ban list."
            await self.client.send_message(channel, message)
            return
        message = "Removed '" + username + "' from ban list."
        await self.client.send_message(channel, message)
        self.saverb()

    async def clearbans(self, channel):
        self.bans.clear()
        message = "Cleared banlist."
        await self.client.send_message(channel, message)
        self.saverb()

    async def addrank(self, username, channel):
        if username in self.ranks:
            message = username + " is already on rank list."
            await self.client.send_message(channel, message)
            return
        self.ranks.append(username)
        message = "Added '" + username + "' to rank list."
        await self.client.send_message(channel, message)
        self.saverb()

    async def removerank(self, username, channel):
        try:
            self.ranks.remove(username)
        except ValueError:
            message = username + " is not on the rank list."
            await self.client.send_message(channel, message)
            return
        message = "Removed '" + username + "' from rank list."
        await self.client.send_message(channel, message)
        self.saverb()

    async def clearranks(self, channel):
        self.ranks.clear()
        message = "Cleared rank list."
        await self.client.send_message(channel, message)
        self.saverb()

    async def showbans(self, channel):
        message = "Bans:\n```\n"
        for item in self.bans:
            message += item + "\n"
        message += "```"
        await self.client.send_message(channel, message)

    async def showranks(self, channel):
        message = "Ranks:\n```\n"
        for item in self.ranks:
            message += item + "\n"
        message += "```"
        await self.client.send_message(channel, message)

    async def showranksandbans(self, channel):
        message = "Ranks:\n```\n"
        for item in self.ranks:
            message += item + "\n"
        message += "```"
        message += "Bans:\n```\n"
        for item in self.bans:
            message += item + "\n"
        message += "```"
        await self.client.send_message(channel, message)

    async def reset(self):
        self.worlds = {w: (0, 0, 0) for w in _all_worlds}
        await self.savew()

    async def save(self):
        for item in self.scouts:
            await self.savescouttodb(item)
        for item in self.worlds:
            await self.saveworldtodb(item)

    async def savew(self):
        for item in self.worlds:
            await self.saveworldtodb(item)

    async def saves(self):
        for item in self.scouts:
            await self.savescouttodb(item)

    def load(self):
        if os.path.isfile(_save_stats):
            with open(_save_stats, 'r') as f:
                self.scouts = json.load(f)
        if os.path.isfile(_save_ranks):
            with open(_save_ranks, 'r') as f:
                self.ranks = json.load(f)
        if os.path.isfile(_save_bans):
            with open(_save_bans, 'r') as f:
                self.bans = json.load(f)

    def saverb(self):
        with open(_save_ranks, 'w') as f:
            json.dump(self.ranks, f, indent=2)
        with open(_save_bans, 'w') as f:
            json.dump(self.bans, f, indent=2)

    async def loadworlds(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = await asyncpg.connect(os.environ['DATABASE_URL'], ssl=ctx)
        dict1 = {}
        worlds = await conn.fetch('SELECT * FROM world_data')
        for item in worlds:
            dict2 = {
                item['world']:
                    [
                        int(item['plinths']) if self.representsint(item['plinths']) else
                        str(item['plinths']),
                        int(item['scout_time']),
                        int(item['reassign_time'])
                    ]
            }
            dict1 = {**dict1, **dict2}
        conn.close
        self.worlds = dict1

    async def loadscouts(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = await asyncpg.connect(os.environ['DATABASE_URL'], ssl=ctx)
        scouts = await conn.fetch('SELECT * FROM scouts')
        dict1 = {}
        for item in scouts:
            dict2 = {
                item['memberid']: {
                    "name": item['name'],
                    "calls": item['calls'],
                    "scouts": item['scouts'],
                    "scout_level": item['scout_level'],
                    "scout_requests": item['scout_requests'],
                    "worlds": [],
                    "bot_mute": item['bot_mute']
                }
            }
            dict1 = {**dict1, **dict2}
        conn.close
        self.scouts = dict1


    async def savescouttodb(self, data):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = await asyncpg.connect(os.environ['DATABASE_URL'], ssl=ctx)
        my_data: Dict[Any, List[Any]] = {
            data: [self.scouts[data]["name"], self.scouts[data]["calls"], self.scouts[data]["scouts"],
                   self.scouts[data]["scout_level"], self.scouts[data]["scout_requests"], self.scouts[data]["bot_mute"]]
        }
        await conn.execute('''
                INSERT INTO scouts(memberid, name, calls, scouts, scout_level, scout_requests, bot_mute) 
                VALUES($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (memberid) DO UPDATE 
                SET "name" = $2, "calls" = $3, "scouts" = $4, "scout_level" = $5, "scout_requests" = $6, "bot_mute" = $7
            ''', data, my_data[data][0], my_data[data][1], my_data[data][2], my_data[data][3], my_data[data][4],
                           my_data[data][5])
        await conn.close()

    async def saveworldtodb(self, data):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = await asyncpg.connect(os.environ['DATABASE_URL'], ssl=ctx)
        my_data: Dict[Any, List[Any]] = {
            data: [self.worlds[data][0], self.worlds[data][1], self.worlds[data][2]]
        }
        await conn.execute('''
                INSERT INTO world_data(world, plinths, scout_time, reassign_time) 
                VALUES($1, $2, $3, $4)
                ON CONFLICT (world) DO UPDATE 
                SET "plinths" = $2, "scout_time" = $3, "reassign_time" = $4
            ''', str(data), str(my_data[data][0]), my_data[data][1], my_data[data][2])
        await conn.close()

    @staticmethod
    def representsint(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_ok(v1, v2):
        if isinstance(v1, str):
            if v1 != "Party":
                if time.time() - v2 < 135:
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False

    @staticmethod
    def restart_program():
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        python = sys.executable
        os.execl(python, python, *sys.argv)
