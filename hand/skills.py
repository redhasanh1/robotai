"""Skills the robot writes for itself (Kimi round 10): a library that grows at inference time, no training.

When a request is beyond the built-in skills, the AI composes a program from them (home_tasks.think). If it works, the
program is saved as a new NAMED skill - with the objects the request mentioned turned into slots - and the next time a
request fits, the robot just does it: no model call, no 20-60 s of thinking. "hide the remote" teaches "hide {0}", so
"hide the book" is free.

Two gates keep a saved skill honest:
- the body check runs on every reuse, with the new objects filled in (a slot that makes no physical sense fails there);
- a Beta count per skill, the same rule as grasp habits (hand/habit.py): used only while its posterior mean success is
  high enough AND its last use worked. One failure and the AI is asked again; its new program replaces the old one.

The claim is not "a model can sequence two skills" (that's planning) - it's that the sequence becomes a first-class,
reusable, physics-checked skill without a gradient step. Voyager did skill libraries in Minecraft; this is the same idea
on a body, gated by the body.

    lib = Library("logs/skills.json")
    hit = lib.recall("hide the book")            # None, or {"name", "program", "p", "tries"}
    lib.learn("hide the remote", program, ok)    # after the outcome is known
"""
import itertools
import json
import os
import re

from . import home, home_tasks as H

MIN_P = 0.6            # (wins + 1) / (tries + 2): one clean success (2/3 = 0.67) is enough to try it again
FILLER = r"\b(please|could you|can you|would you|for me|the|a|an|my|some|now)\b"
# rooms are slots too; bare "laundry" is only a room before counter/table ("put the laundry away" means the clothes)
ROOM_RE = r"\b(kitchen|living room|lounge|laundry (?:room|area)|laundry(?= (?:counter|table|surface)))\b"
ROOM_OF = {"lounge": "living room", "laundry room": "laundry", "laundry area": "laundry"}


def _slots(text):
    """Objects named in the request, in the order they are mentioned - only words that mean exactly one object."""
    hits = []
    low = text.lower()
    for w in sorted(H.OBJ_WORDS, key=len, reverse=True):
        if len(H.OBJ_WORDS[w]) != 1:
            continue
        for mt in re.finditer(rf"\b{re.escape(w)}\b", low):
            if not any(a < mt.end() and mt.start() < b for a, b, _, _ in hits):      # longest word wins overlaps
                hits.append((mt.start(), mt.end(), w, H.OBJ_WORDS[w][0]))
    return sorted(hits)


def template(text):
    """'Please hide the remote' -> ('hide {0}', ['remote'], []);
    'clear the laundry counter' -> ('clear {r0} counter', [], ['laundry'])."""
    low = text.lower()
    rooms = [ROOM_OF.get(mt.group(1), mt.group(1)) for mt in re.finditer(ROOM_RE, low)]
    for k in range(len(rooms)):
        low = re.sub(ROOM_RE, "{r%d}" % k, low, count=1)
    low = re.sub(r"\b(table|counter|surface)\b", "counter", low)
    hits = _slots(low)
    for i, (a, b, _, o) in enumerate(reversed(hits)):
        low = low[:a] + "{%d}" % (len(hits) - 1 - i) + low[b:]
    objs = [o for _, _, _, o in hits]
    low = re.sub(FILLER, " ", low)
    low = re.sub(r"[^a-z0-9{} ]", " ", low)
    return " ".join(low.split()), objs, rooms


def _abstract(program, objs, rooms=()):
    """Replace the request's objects and rooms in the program with their slots."""
    out = []
    for a in program:
        a = dict(a)
        if a.get("obj") in objs:
            a["obj"] = "{%d}" % objs.index(a["obj"])
        for f in ("room", "to"):
            if a.get(f) in rooms:
                a[f] = "{r%d}" % list(rooms).index(a[f])
        out.append(a)
    return out


def _tied(program, rooms):
    """Room slots whose objects the program names ('clear the living room table' moves the ball, book, ... BECAUSE
    they are in the living room): such a skill must not be reused for another room."""
    homes = {home.OBJECTS[a["obj"]][0] for a in program if a.get("obj") in home.OBJECTS}
    return [k for k, r in enumerate(rooms) if r in homes]


def _pin(name, rooms, ks):
    """Put the actual rooms back into the tied slots: a room-tied skill is only ever found for its own room."""
    for k in ks:
        name = name.replace("{r%d}" % k, rooms[k])
    return name


def _fill(program, objs, rooms=()):
    out = []
    for a in program:
        a = dict(a)
        for f in ("room", "to"):
            rm = re.fullmatch(r"\{r(\d+)\}", str(a.get(f, "")))
            if rm:
                if int(rm.group(1)) >= len(rooms):
                    return None
                a[f] = rooms[int(rm.group(1))]
        m = re.fullmatch(r"\{(\d+)\}", str(a.get("obj", "")))
        if m:
            k = int(m.group(1))
            if k >= len(objs):
                return None
            a["obj"] = objs[k]
        out.append(a)
    return out


class Library:
    def __init__(self, path=None):
        self.path = path
        self.skills = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self.skills = json.load(f)

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.skills, f, indent=1)

    def recall(self, request):
        """A saved skill for this request with its objects filled in, if it is trusted; else None."""
        name, objs, rooms = template(request)
        keys = [_pin(name, rooms, ks) for n in range(len(rooms), -1, -1)                  # most specific first
                for ks in itertools.combinations(range(len(rooms)), n)]
        name = next((k for k in keys if k in self.skills), None)
        if name is None:
            return None
        s = self.skills[name]
        p = (s["wins"] + 1) / (s["tries"] + 2)
        if p < MIN_P or not s["last_ok"]:
            return None
        if any(k < len(rooms) and rooms[k] != s["rooms"][k] for k in s.get("tied", [])):
            return None                       # its objects were picked for the room it learned in
        prog = _fill(s["program"], objs, rooms)
        return None if prog is None else {"name": name, "program": prog, "p": round(p, 2), "tries": s["tries"]}

    def learn(self, request, program, ok):
        """Record how a program for this request went. A new program that worked replaces the saved one."""
        name, objs, rooms = template(request)
        tied = _tied(program or [], rooms)
        name = _pin(name, rooms, tied)           # 'clear kitchen counter' and 'clear {r0} counter' are different skills
        s = self.skills.setdefault(name, {"program": [], "wins": 0, "tries": 0, "last_ok": False, "from": request})
        s["tries"] += 1
        s["wins"] += int(bool(ok))
        s["last_ok"] = bool(ok)
        if ok and program:
            s["program"] = _abstract(program, objs, rooms)
            s["rooms"], s["tied"] = rooms, tied
        if not s["program"]:              # never worked: nothing worth keeping
            del self.skills[name]
        return name
