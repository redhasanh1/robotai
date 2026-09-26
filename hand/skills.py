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
import json
import os
import re

from . import home_tasks as H

MIN_P = 0.6            # (wins + 1) / (tries + 2): one clean success (2/3 = 0.67) is enough to try it again
FILLER = r"\b(please|could you|can you|would you|for me|the|a|an|my|some|now)\b"


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
    """'Please hide the remote' -> ('hide {0}', ['remote'])."""
    hits = _slots(text)
    low, objs = text.lower(), []
    for i, (a, b, _, o) in enumerate(reversed(hits)):
        low = low[:a] + "{%d}" % (len(hits) - 1 - i) + low[b:]
    objs = [o for _, _, _, o in hits]
    low = re.sub(FILLER, " ", low)
    low = re.sub(r"[^a-z0-9{} ]", " ", low)
    return " ".join(low.split()), objs


def _abstract(program, objs):
    """Replace the request's objects in the program with their slot numbers."""
    out = []
    for a in program:
        a = dict(a)
        if a.get("obj") in objs:
            a["obj"] = "{%d}" % objs.index(a["obj"])
        out.append(a)
    return out


def _fill(program, objs):
    out = []
    for a in program:
        a = dict(a)
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
        name, objs = template(request)
        s = self.skills.get(name)
        if not s:
            return None
        p = (s["wins"] + 1) / (s["tries"] + 2)
        if p < MIN_P or not s["last_ok"]:
            return None
        prog = _fill(s["program"], objs)
        return None if prog is None else {"name": name, "program": prog, "p": round(p, 2), "tries": s["tries"]}

    def learn(self, request, program, ok):
        """Record how a program for this request went. A new program that worked replaces the saved one."""
        name, objs = template(request)
        s = self.skills.setdefault(name, {"program": [], "wins": 0, "tries": 0, "last_ok": False, "from": request})
        s["tries"] += 1
        s["wins"] += int(bool(ok))
        s["last_ok"] = bool(ok)
        if ok and program:
            s["program"] = _abstract(program, objs)
        if not s["program"]:              # never worked: nothing worth keeping
            del self.skills[name]
        return name
