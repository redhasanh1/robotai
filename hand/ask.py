"""Ask once, never again (Kimi round 11): one good question instead of a guess, and the answer kept for good.

Two facts a request can be missing, and the robot can tell which:
- WHICH one: "put the shirt in the washer" when there are two shirts. The rules used to do both.
- WHERE it lives: "put the book away" - nobody has said where the book goes. The rules couldn't do it at all.
The robot says what it knows and asks exactly the one thing it doesn't ("I see a red shirt and a white shirt - which
one do you mean?"). The answer goes into house knowledge (a JSON file) and the request is rewritten into words the
planner already understands. Next time: no question. One-shot learning from one human answer - no training.

    know = Knowledge("logs/house_knowledge.json")
    q = question(command, know)          # None, or {"kind", "about", "options", "text"}
    know.learn(q, "the white one")       # -> "white shirt"
    command = rewrite(command, know)     # "put the white shirt in the washer"
"""
import json
import os
import re

from . import home, home_tasks as H

# words that mean one thing but match several ("the shirt"); plurals ("shirts", "clothes") mean all of them
SINGULAR = sorted([w for w, v in H.OBJ_WORDS.items() if len(v) > 1 and not w.endswith("s")
                   and w not in ("clothes", "laundry")], key=len, reverse=True)
PLACES = list(home.CONTAINERS) + ["kitchen", "laundry", "living room"]
AWAY = r"\b(put|take|bring)\s+(the\s+|my\s+)?(?P<o>[a-z ]+?)\s+(away|back)\b|\btidy\s+(up\s+)?(the\s+)?(?P<o2>[a-z ]+?)$"


class Knowledge:
    def __init__(self, path=None):
        self.path, self.means, self.homes = path, {}, {}
        if path and os.path.exists(path):
            with open(path) as f:
                d = json.load(f)
            self.means, self.homes = d.get("means", {}), d.get("homes", {})

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w") as f:
                json.dump({"means": self.means, "homes": self.homes}, f, indent=1)

    def learn(self, q, answer):
        """Store what the answer says; returns what was understood (None if nothing matched)."""
        a = " " + answer.lower() + " "
        pick = None
        for opt in sorted(q["options"], key=len, reverse=True):
            words = [opt] + ([opt.split()[0]] if q["kind"] == "which" and " " in opt else [])   # "the white one"
            if any(re.search(rf"\b{re.escape(w)}\b", a) for w in words):
                pick = opt
                break
        if pick is None:
            return None
        (self.means if q["kind"] == "which" else self.homes)[q["about"]] = pick
        self.save()
        return pick


def _obj_in(text):
    o = H._objs(text)
    return o[0] if len(o) == 1 else None


def question(command, know):
    """The one fact this request is missing, as a question - or None if nothing is missing."""
    low = command.lower()
    for w in SINGULAR:
        if re.search(rf"\b(the|a|my|that|this)\s+{w}\b", low) and w not in know.means:
            opts = H.OBJ_WORDS[w]
            return {"kind": "which", "about": w, "options": opts,
                    "text": f"I see {' and '.join('a ' + o for o in opts)} - which one do you mean?"}
    m = re.search(AWAY, low)
    if m:
        what = (m.group("o") or m.group("o2") or "").strip()
        o = know.means.get(what) or _obj_in(what)
        if o and o not in know.homes:
            return {"kind": "where", "about": o, "options": PLACES,
                    "text": f"I don't know where the {o} lives yet - where does it go? ({', '.join(PLACES)})"}
    return None


def rewrite(command, know):
    """Say it in words the planner already knows, using what the robot has been told."""
    low = command.lower()
    for w in SINGULAR:
        if w in know.means:
            low = re.sub(rf"\b(the|a|my|that|this)\s+{w}\b", f"the {know.means[w]}", low)
    m = re.search(AWAY, low)
    if m:
        what = (m.group("o") or m.group("o2") or "").strip()
        o = know.means.get(what) or _obj_in(what)
        place = know.homes.get(o)
        if place:
            said = f"put the {o} in the {place}" if place in home.CONTAINERS else f"take the {o} to the {place}"
            low = low[:m.start()] + said + low[m.end():]
    return low


def plan(command, know, ask=None, budget=1):
    """-> (program, unknown, questions asked). ask(question) -> answer text, or None to not ask (then it guesses)."""
    asked = []
    while ask is not None and len(asked) < budget:
        q = question(command, know)
        if q is None:
            break
        asked.append(q["text"])
        if know.learn(q, ask(q)) is None:
            break
    prog, unknown = H.plan(rewrite(command, know))
    return prog, unknown, asked
