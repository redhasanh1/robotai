"""Understanding chores in the simulated home: sentence -> program -> body check -> world-state check.

    prog, unknown = plan("do the dishes and bring me an apple")
    PROMPTS: 50 (prompt, check) pairs; check(body) looks at where every object ended up.
    score(brain=None) -> results per prompt: planned by rules / by the AI / not understood, passed or not.

Words it knows: objects (and synonyms), containers (sink, rack, washer, basket), rooms, and a handful of wishes
("I'm hungry" -> bring the apple). Anything else is left for the AI brain, which gets the home's action list,
the world state, and the body's problem list to repair from - same loop as tools/robot_do.py.
"""
import json
import re

from . import home

OBJ_WORDS = {"cup": ["cup"], "mug": ["cup"], "glass": ["cup"], "plate": ["plate"], "dish": ["cup", "plate"],
             "dishes": ["cup", "plate"], "apple": ["apple"], "fruit": ["apple"], "snack": ["apple"],
             "sponge": ["sponge"], "towel": ["towel"], "red shirt": ["red shirt"], "white shirt": ["white shirt"],
             "shirts": ["red shirt", "white shirt"], "shirt": ["red shirt", "white shirt"],
             "clothes": ["red shirt", "white shirt"], "laundry": ["red shirt", "white shirt"],
             "ball": ["ball"], "toy": ["ball"], "book": ["book"], "remote": ["remote"], "soda can": ["soda can"],
             "soda": ["soda can"], "can": ["soda can"], "drink": ["soda can"], "trash": ["soda can"],
             "rubbish": ["soda can"]}
CONT_WORDS = {"sink": "sink", "rack": "rack", "dish rack": "rack", "drying rack": "rack", "dishwasher": "rack",
              "washer": "washer", "washing machine": "washer", "basket": "basket", "hamper": "basket"}
ROOM_WORDS = {"kitchen": "kitchen", "laundry room": "laundry", "laundry area": "laundry", "living room": "living room",
              "lounge": "living room", "couch": "living room", "sofa": "living room", "coffee table": "living room"}
WISHES = [  # (pattern, program) - things people say instead of instructions
    (r"hungry|something to eat|snack", [{"do": "give", "obj": "apple"}]),
    (r"thirsty|something to drink", [{"do": "give", "obj": "soda can"}]),
    (r"watch (tv|television)|change the channel", [{"do": "give", "obj": "remote"}]),
    (r"(want|like) to read|bored", [{"do": "give", "obj": "book"}]),
    (r"play (catch|ball)|let'?s play", [{"do": "give", "obj": "ball"}]),
    (r"(dry|wipe) my hands", [{"do": "give", "obj": "towel"}]),
]
DISHES, DIRTY = ["cup", "plate"], ["red shirt", "white shirt"]


def _objs(c):
    out = []
    for w in sorted(OBJ_WORDS, key=len, reverse=True):                   # longest first: "red shirt" before "shirt"
        if re.search(rf"\b{w}\b", c):
            for o in OBJ_WORDS[w]:
                if o not in out:
                    out.append(o)
            c = re.sub(rf"\b{w}\b", " ", c)
    return out


def _first(c, table):
    for w in sorted(table, key=len, reverse=True):
        if re.search(rf"\b{w}\b", c):
            return table[w]
    return None


VERBS = r"\b(put|place|drop|load|throw|stick|move|take|carry|bring|give|hand|fetch|get|pass|wipe|clean|go|fold|" \
        r"pick|grab|juggle|point|look|wave|box|clap|nod|do|wash|start|tidy|make)\b"


def plan(command):
    prog, unknown, last, last_verb = [], [], [], ""
    for c in [c.strip() for c in re.split(r",|\band then\b|\bthen\b|\balso\b|\band\b(?! then)", command.lower())
              if c.strip()]:
        os_ = _objs(c) or (last if re.search(r"\b(it|them|those|that|these)\b", c) else [])
        last = os_ or last
        if os_ and not re.search(VERBS, c) and not re.search(r"\b(i'?m|i want|i need|let'?s)\b", c) and last_verb:
            c = f"{last_verb} {c}"                     # "put the cup in the sink and [put] the plate in the rack"
        v = re.search(VERBS, c)
        last_verb = (c[:c.index(" me ") + 3] if re.search(r"\b(give|bring|hand|fetch|get) me\b", c)
                     else v.group(1)) if v else last_verb
        cont, room = _first(c, CONT_WORDS), _first(c, ROOM_WORDS)
        wish = next((p for pat, p in WISHES if re.search(pat, c)), None)
        if re.search(r"out of the way|belongs?|spill|mess|where it goes|put .* back\b", c):
            unknown.append(c)                          # judgement calls: leave to the AI rather than guess
        elif wish:
            prog += wish
        elif re.search(r"(clean|tidy|sort out) (up )?(the )?(whole )?(house|home|everything)|clean up everything", c):
            prog += [{"do": "put_in", "obj": o, "into": "rack"} for o in DISHES]
            prog += [{"do": "put_in", "obj": o, "into": "washer"} for o in DIRTY]
            prog += [{"do": "put_on", "obj": "soda can", "room": "kitchen"}, {"do": "wipe", "room": "kitchen"}]
        elif re.search(r"(do|wash|clean) the dishes|dishes (done|clean)", c):
            prog += [{"do": "put_in", "obj": o, "into": "sink"} for o in DISHES]
            prog += [{"do": "put_in", "obj": o, "into": "rack"} for o in DISHES]
        elif re.search(r"load the (dish(es)?|rack|dishwasher)|put (the )?dishes away", c):
            prog += [{"do": "put_in", "obj": o, "into": "rack"} for o in DISHES]
        elif re.search(r"(do|start) the laundry|wash (the |my )?clothes|start a load|laundry (in|into)", c):
            prog += [{"do": "put_in", "obj": o, "into": "washer"} for o in DIRTY]
        elif re.search(r"\b(wipe|clean)\b.*\b(table|counter)\b", c):          # "clean the living room table"
            prog.append({"do": "wipe", "room": room or ("living room" if "table" in c else "kitchen")})
        elif re.search(r"(tidy|clean up|clean) (the )?living room|tidy up$|pick up the living room", c):
            prog += [{"do": "put_on", "obj": "soda can", "room": "kitchen"},
                     {"do": "put_in", "obj": "ball", "into": "basket"}]
        elif re.search(r"\b(wipe|clean)\b", c) and (room or re.search(r"counter|table", c)):
            prog.append({"do": "wipe", "room": room or ("living room" if "table" in c else "kitchen")})
        elif re.search(r"\b(fold|put away)\b", c) and "towel" in os_:
            prog.append({"do": "put_in", "obj": "towel", "into": "basket"})
        elif re.search(r"\b(give|bring|hand|fetch|pass|get) me\b|\b(give|hand|bring)\b.*\bto me\b", c) and os_:
            prog += [{"do": "give", "obj": o} for o in os_]
        elif re.search(r"\b(put|place|drop|load|throw|stick|move)\b", c) and os_ and cont:
            prog += [{"do": "put_in", "obj": o, "into": cont} for o in os_]
        elif re.search(r"\b(take|move|carry|bring|put|place)\b", c) and os_ and room:
            prog += [{"do": "put_on", "obj": o, "room": room} for o in os_]
        elif re.search(r"\b(go|drive|head|come)\b", c) and (room or re.search(r"\b(me|here)\b", c)):
            prog.append({"do": "go", "to": room or "you"})
        elif re.search(r"juggl", c):
            o = os_[0] if os_ else "ball"
            prog += [{"do": "pick", "obj": o}] + [{"do": "toss", "obj": o, "to": s, "height": 0.3}
                                                  for s in ("left", "right", "left", "right")]
        elif re.search(r"\b(point|show)\b", c) and os_:
            prog.append({"do": "point", "obj": os_[0]})
        elif re.search(r"\b(look|find)\b", c) and os_:
            prog.append({"do": "look", "obj": os_[0]})
        elif re.search(r"\b(pick|grab|get|take|lift|hold)\b", c) and os_:
            prog += [{"do": "pick", "obj": o} for o in os_[:2]]
        elif re.search(r"\b(wave|hello|hi|bye)\b", c):
            prog.append({"do": "wave"})
        elif re.search(r"\b(box|boxing|punch)\b", c):
            prog.append({"do": "box"})
        elif re.search(r"\bclap\b", c):
            prog.append({"do": "clap"})
        elif re.search(r"\b(nod|yes)\b", c):
            prog.append({"do": "nod"})
        elif re.search(r"\b(shake your head|no)\b", c):
            prog.append({"do": "shake"})
        else:
            unknown.append(c)
    return prog, unknown


# ------------------------------------------------------------------ the 50 prompts and how each is judged
def W(o):
    return lambda b: b.where[o]


def _in(o, c):
    return lambda b: b.where[o] == ("in", c)


def _on(o, r):
    return lambda b: b.where[o] == ("on", r)


def _given(o):
    return lambda b: b.where[o] == ("given",)


def _all(*fs):
    return lambda b: all(f(b) for f in fs)


def _untouched(b):
    return all(b.where[o] == ("on", home.OBJECTS[o][0]) for o in home.OBJECTS)


def _moved(b):
    return not _untouched(b) or b.frames


PROMPTS = [
    # direct instructions
    ("put the cup in the dish rack", _in("cup", "rack")),
    ("put the plate in the sink", _in("plate", "sink")),
    ("load the dishes into the rack", _all(_in("cup", "rack"), _in("plate", "rack"))),
    ("do the dishes", _all(_in("cup", "rack"), _in("plate", "rack"))),
    ("put the red shirt in the washing machine", _in("red shirt", "washer")),
    ("do the laundry", _all(_in("red shirt", "washer"), _in("white shirt", "washer"))),
    ("put the towel in the basket", _in("towel", "basket")),
    ("fold the towel", _in("towel", "basket")),
    ("bring me the apple", _given("apple")),
    ("give me the remote", _given("remote")),
    ("hand me the book", _given("book")),
    ("fetch me the ball", _given("ball")),
    ("take the soda can to the kitchen", _on("soda can", "kitchen")),
    ("move the book to the kitchen", _on("book", "kitchen")),
    ("carry the apple to the living room", _on("apple", "living room")),
    ("put the ball in the basket", _in("ball", "basket")),
    ("put the white shirt in the hamper", _in("white shirt", "basket")),
    ("wipe the kitchen counter", lambda b: "kitchen" in b.wiped),
    ("clean the living room table", lambda b: "living room" in b.wiped),
    ("go to the laundry room", lambda b: b.room == "laundry"),
    ("come here", lambda b: b.room == "you"),
    ("juggle the ball", lambda b: any(f[2] and f[2][0] == "fly" for f in b.frames)),
    ("wave hello", lambda b: len(b.frames) >= 4),
    ("point at the remote", lambda b: b.room == "living room"),
    ("put the cup in the sink and the plate in the rack", _all(_in("cup", "sink"), _in("plate", "rack"))),
    ("put the apple in the sink", _in("apple", "sink")),
    ("throw the soda can in the sink", _in("soda can", "sink")),
    ("put the sponge in the sink", _in("sponge", "sink")),
    ("pick up the towel", lambda b: b.where["towel"][0] in ("on", "held")),
    ("put the remote in the basket", _in("remote", "basket")),
    # things people say instead of instructions
    ("I'm hungry", _given("apple")),
    ("I'm thirsty", _given("soda can")),
    ("I want to watch TV", _given("remote")),
    ("I'm bored", _given("book")),
    ("let's play catch", _given("ball")),
    ("I need to dry my hands", _given("towel")),
    ("tidy the living room", _all(_on("soda can", "kitchen"), _in("ball", "basket"))),
    ("clean up the house", _all(_in("cup", "rack"), _in("plate", "rack"), _in("red shirt", "washer"),
                                _in("white shirt", "washer"), _on("soda can", "kitchen"))),
    ("start a load of washing", _all(_in("red shirt", "washer"), _in("white shirt", "washer"))),
    ("put the dishes away", _all(_in("cup", "rack"), _in("plate", "rack"))),
    # several steps
    ("do the dishes, then bring me the apple", _all(_in("cup", "rack"), _in("plate", "rack"), _given("apple"))),
    ("put the shirts in the washer and fold the towel", _all(_in("red shirt", "washer"),
                                                               _in("white shirt", "washer"), _in("towel", "basket"))),
    ("take the book to the laundry room, then wave", _on("book", "laundry")),
    ("bring me the remote and the soda can", _all(_given("remote"), _given("soda can"))),
    ("wipe the kitchen counter and then put the cup in the rack", _all(lambda b: "kitchen" in b.wiped,
                                                                         _in("cup", "rack"))),
    ("move the ball to the kitchen and juggle it", _on("ball", "kitchen")),
    # need real thinking - the rules alone will not get these (the AI's job)
    ("put everything that belongs in the kitchen back in the kitchen", _on("soda can", "kitchen")),
    ("get the dirty clothes out of the way", _all(_in("red shirt", "washer"), _in("white shirt", "washer"))),
    ("make the counter in the kitchen clean and put the fruit in the living room", _all(
        lambda b: "kitchen" in b.wiped, _on("apple", "living room"))),
    ("I spilled something in the living room", lambda b: "living room" in b.wiped),
]
assert len(PROMPTS) == 50


def actions_doc():
    from . import motor
    return (home.__doc__[home.__doc__.index("body = HomeBody"):home.__doc__.index("The robot faces")] +
            motor.__doc__[motor.__doc__.index("Actions"):])


def think(command, m, brain, rounds=2, say=print):
    """AI writes a home program, the body checks it, the AI repairs it."""
    world = home.describe_world(home.HomeBody(m))
    doc = actions_doc()
    reply = brain.program(command, world, doc)
    prog = reply.get("program") or []
    for r in range(rounds + 1):
        problems = home.HomeBody(m).run(prog).problems if prog else ["the program was empty"]
        say(f"  {'plan' if r == 0 else f'repair {r}'}: {len(prog)} steps" +
            (f", problems: {'; '.join(problems[:2])}" if problems else ", checks out on the body"))
        if not problems or r == rounds:
            break
        reply = brain.program(command, world, doc, problems=problems, previous=prog)
        prog = reply.get("program") or prog
    return prog, reply.get("say", "")


def score(m, brain=None, say=print, only=None):
    rows = []
    for i, (p, check) in enumerate(PROMPTS):
        if only and i not in only:
            continue
        prog, unknown = plan(p)
        how = "rules"
        if unknown:
            if brain is None:
                rows.append({"prompt": p, "how": "not understood", "passed": False, "unknown": unknown})
                say(f"[{i + 1:2d}] --   not understood (no AI): {p}")
                continue
            try:
                extra, _ = think(", ".join(unknown), m, brain, say=lambda s: None)
            except Exception as e:                    # brain died: count it as not understood
                extra = []
                say(f"      AI error {type(e).__name__}")
            prog += extra
            how = "rules+AI" if len(prog) > len(extra) else "AI"
        body = home.HomeBody(m).run(prog)
        ok = bool(prog) and bool(check(body))
        rows.append({"prompt": p, "how": how, "passed": ok, "problems": body.problems[:3],
                     "program": prog, "seconds": round(sum(f[0] for f in body.frames), 1)})
        say(f"[{i + 1:2d}] {'PASS' if ok else 'fail'} {how:9s} {p}" + (f"   ({body.problems[0]})" if body.problems else ""))
    return rows
