import re
import time


def parse_line(line):
    line = line.lower()
    line = re.sub("(?<=[a-z])(?=\\d)|(?<=\\d)(?=[a-z])|\\.", " ", line)
    line = line.replace("w", "").replace(",", " ").replace("/", " ").replace(" and ", "").strip()
    line = line.replace("  ", " ")
    line = re.sub("(dead|gone|d)", "0", line)
    return line


def get_worlds():
    return [1, 2, 4, 5, 6, 9, 10, 12, 14, 15, 16, 18, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32, 35, 36, 37, 39
        , 40, 42, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72
        , 73, 74, 76, 77, 78, 79, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 96, 98, 99, 100, 103, 104, 105, 114
        , 115, 116, 117, 119, 123, 124, 134, 137, 138, 139, 140]


class Analyzer:

    def __init__(self):
        self.worlds = {}
        for w in get_worlds():
            self.worlds[w] = [0, 0]

    def analyze_call(self, message):
        parsed = parse_line(message)
        split = parsed.split()
        if len(split) != 2:
            return
        world = split[0]
        call = split[1]

        if not world.isdigit():
            return

        world = int(world)
        if world not in get_worlds():
            return "{} is not a p2p english world".format(world)

        if call.isdigit():
            flints_filled = int(call)
            if 0 <= flints_filled <= 5:
                self.worlds[world] = [flints_filled, time.time()]
        # else. check for juna/aagi/seren/cres/sword/reset etc

        return self.get_order()

    def get_order(self):
        s = sorted(self.worlds.items(), key=lambda v: (v[1][0], -v[1][1]), reverse=True)
        res = []
        for key, value in s[:5]:
            if value[0] == 0:
                break
            res.append("w{} ({}/6)".format(key, value[0]))
        return "->".join(res)
