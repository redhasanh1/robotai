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
    ("get the dirty clothes out of the way",               # washer or laundry basket are both sensible
     lambda b: all(b.where[o] in (("in", "washer"), ("in", "basket")) for o in ("red shirt", "white shirt"))),
    ("make the counter in the kitchen clean and put the fruit in the living room", _all(
        lambda b: "kitchen" in b.wiped, _on("apple", "living room"))),
    ("I spilled something in the living room", lambda b: "living room" in b.wiped),
]
assert len(PROMPTS) == 50

# the room when the prompt is given: which counters have a stain on them (sim ground truth). The robot is NOT told this -
# its counter cameras see it (hand/perceive.py) and describe it; that description is all the planner gets.
SCENES = {"I spilled something in the living room": {"living room"}}
_EYES = {}


def seen_messes(m, rooms):
    """Put stains on these counters, then look: -> {room: what the camera saw}. Eyes learn the clean house once."""
    from . import perceive
    if id(m) not in _EYES:
        perceive.set_messes(m, ())
        _EYES[id(m)] = perceive.Eyes(m).learn()
    perceive.set_messes(m, rooms or ())
    return _EYES[id(m)].survey()


HIGH_LEVEL = ("go", "pick", "put_in", "put_on", "give", "wipe", "pass", "toss", "point", "look", "wave", "box",
              "clap", "nod", "shake", "say", "wait")


def actions_doc(high_level=True):
    """The action list the AI plans with. high_level (default): skills only - a small model given raw move_hand
    coordinates invented targets 1-2 m away that it could not repair (house test, round 8)."""
    if high_level:
        # each skill with its PURPOSE / EFFECT (Kimi round 8: give the planner an action-effect model, not
        # task-specific rules - "wipe removes spills" is what wipe does, not the answer to one test prompt)
        return """Actions (JSON), one object per step - with what each one is for:
  {"do": "go", "to": "kitchen|laundry|living room|you"}      move the robot; others drive there by themselves
  {"do": "pick", "obj": "<object>"}                          hold an object (drives to it first)
  {"do": "put_in", "obj": "<object>", "into": "sink|rack|washer|basket"}
        sink: dirty dishes wait here to be washed    rack: clean dishes dry and are stored here
        washer: dirty clothes get washed here        basket: clean or folded laundry is kept here
  {"do": "put_on", "obj": "<object>", "room": "kitchen|laundry|living room"}   leave it on that room's counter/table
  {"do": "give", "obj": "<object>"}                          hand it to the person (for things they need or ask for)
  {"do": "wipe", "room": "kitchen|laundry|living room"}      clean that room's surface: removes spills, crumbs, mess
  {"do": "toss", "obj": "<object>", "to": "left|right", "height": 0.3}        throw between hands (play, juggling)
  {"do": "point", "obj": "<object>"}  {"do": "look", "obj": "<object>"}  show or attend to something
  {"do": "wave"}  {"do": "say", "text": "..."}               greet / talk to the person
Use only these actions and only the objects, containers and rooms listed. Think about the GOAL first (where should
each object end up?) and then write the fewest steps that get there."""
    from . import motor
    return (home.__doc__[home.__doc__.index("body = HomeBody"):home.__doc__.index("The robot faces")] +
            motor.__doc__[motor.__doc__.index("Actions"):])


EXAMPLES = [  # (request, program) the robot already knows works - its experience, shown to the AI in context
    ("I spilled coffee on the kitchen counter", [{"do": "wipe", "room": "kitchen"}]),
    ("take the empty soda can out of the living room", [{"do": "put_on", "obj": "soda can", "room": "kitchen"}]),
    ("the dirty laundry is everywhere", [{"do": "put_in", "obj": "red shirt", "into": "washer"},
                                         {"do": "put_in", "obj": "white shirt", "into": "washer"}]),
    ("the dishes are dirty", [{"do": "put_in", "obj": "cup", "into": "sink"},
                              {"do": "put_in", "obj": "plate", "into": "sink"}]),
    ("the fruit should be where people sit", [{"do": "put_on", "obj": "apple", "room": "living room"}]),
    ("I'm cold and wet", [{"do": "give", "obj": "towel"}]),
]


def _words(s):
    return set(re.findall(r"[a-z]+", s.lower())) - {"the", "a", "an", "to", "in", "on", "of", "and", "i", "my", "it"}


def examples_for(command, k=4, hints=False):
    """Most similar known tasks, by word overlap: the prompts the robot already solves (its experience), plus the
    hand-written EXAMPLES only when hints=True. The EXAMPLES paraphrase the three judgement-call test prompts, so
    a score with hints is a ceiling, not a fair result."""
    pool = list(EXAMPLES) if hints else []                   # hints = hand-written; off for a fair score
    for p, _ in PROMPTS:
        prog, unknown = plan(p)
        if prog and not unknown:
            pool.append((p, prog))
    cw = _words(command)
    pool.sort(key=lambda e: len(cw & _words(e[0])), reverse=True)
    return pool[:k]


def think(command, m, brain, rounds=2, say=print, use_examples=True, hints=False, situate=False, messes=None, splice=True):
    """AI writes a home program, the body checks it, the AI repairs it. With use_examples the most similar tasks
    the robot already knows are put in the prompt (in-context learning - no training)."""
    world = home.describe_world(home.HomeBody(m, messes))
    if use_examples:
        world += "\n\nTasks you have done before (request -> program that worked):\n" + "\n".join(
            f'- "{r}" -> {json.dumps(p)}' for r, p in examples_for(command, hints=hints) if r != command)
    doc = actions_doc()
    goal = ""
    if situate and hasattr(brain, "goal"):          # scene-state step first (Kimi round 8, lever 2)
        g = brain.goal(command, world)
        goal = "; ".join(str(g.get(k, "")).strip() for k in ("wrong", "goal") if str(g.get(k, "")).strip())
        say(f"  situation: {goal}")
    reply = brain.program(command, world, doc, goal=goal)
    prog = reply.get("program") or []
    rewrites = 0
    for r in range(rounds + 1 + (len(prog) if splice else 0)):      # step repairs are cheap: one per step at most
        low = [f"step {i + 1}: '{a.get('do')}' is not allowed - use only: {', '.join(HIGH_LEVEL)}"
               for i, a in enumerate(prog) if isinstance(a, dict) and a.get("do") not in HIGH_LEVEL]
        prog = [a for a in prog if isinstance(a, dict) and a.get("do") in HIGH_LEVEL]      # drop, and say so
        problems = low + (home.HomeBody(m, messes).run(prog).problems if prog else ["the program was empty"])
        say(f"  {'plan' if r == 0 else f'repair {r}'}: {len(prog)} steps" +
            (f", problems: {'; '.join(problems[:2])}" if problems else ", checks out on the body"))
        if not problems:
            break
        if splice and hasattr(brain, "choose_step") and not low:
            fixed = splice_repair(command, prog, m, brain, messes, say)
            if fixed is not None:
                prog = fixed
                continue
        if rewrites == rounds:
            break
        rewrites += 1
        reply = brain.program(command, world, doc, problems=problems, previous=prog, goal=goal)
        prog = reply.get("program") or prog
    return prog, reply.get("say", "")


def step_options(prog, k, m, messes):
    """Concrete replacements for step k, each checked on the body first: only steps that physically work are offered
    (physics veto, then the AI chooses - the grasp pipeline's pattern, applied to plans). Rooms come from the plan so
    far and from what the camera sees; nothing here knows about any particular request."""
    bad = prog[k]
    rooms = [a.get("to") for a in prog[:k] if a.get("do") == "go"]
    rooms = list(dict.fromkeys(rooms[-1:] + list(messes or {}) + [bad.get("room"), bad.get("to")]))
    rooms = [r for r in rooms if r in home.ROOMS]
    obj = bad.get("obj") if bad.get("obj") in home.OBJECTS else None
    cands = [{"do": "remove"}]
    for r in rooms:
        cands += [{"do": "wipe", "room": r}, {"do": "go", "to": r}]
        if obj:
            cands.append({"do": "put_on", "obj": obj, "room": r})
    if obj:
        cands += [{"do": "pick", "obj": obj}, {"do": "give", "obj": obj}] + \
                 [{"do": "put_in", "obj": obj, "into": c} for c in home.CONTAINERS]
    out = []
    for c in cands:
        if c == bad:
            continue
        trial = prog[:k] + ([] if c["do"] == "remove" else [c])
        if not home.HomeBody(m, messes).run(trial).problems:        # the step itself must work where it stands
            out.append(c)
    return out[:6]


def splice_repair(command, prog, m, brain, messes, say=print):
    """Repair ONE step instead of rewriting the program (Kimi round 9): a small model anchored on its own plan
    returns it unchanged when asked to rewrite, but can pick from a short list of steps that already work."""
    probs = home.HomeBody(m, messes).run(prog).problems
    hit = re.match(r"step (\d+): (.*)", probs[0]) if probs else None
    if not hit:
        return None
    k = int(hit.group(1)) - 1
    if not 0 <= k < len(prog):
        return None
    opts = step_options(prog, k, m, messes)
    if not opts:
        return None
    i = brain.choose_step(command, prog, k, hit.group(2), opts)
    c = opts[i if 0 <= i < len(opts) else 0]
    say(f"  step {k + 1} {json.dumps(prog[k])} -> {json.dumps(c)}")
    return prog[:k] + ([] if c["do"] == "remove" else [c]) + prog[k + 1:]


def score(m, brain=None, say=print, only=None):
    rows = []
    for i, (p, check) in enumerate(PROMPTS):
        if only and i not in only:
            continue
        messes = seen_messes(m, SCENES.get(p)) if SCENES.get(p) or id(m) in _EYES else None     # clears old stains too
        prog, unknown = plan(p)
        how = "rules"
        if unknown:
            if brain is None:
                rows.append({"prompt": p, "how": "not understood", "passed": False, "unknown": unknown})
                say(f"[{i + 1:2d}] --   not understood (no AI): {p}")
                continue
            try:
                extra, _ = think(", ".join(unknown), m, brain, say=lambda s: None, messes=messes)
            except Exception as e:                    # brain died: count it as not understood
                extra = []
                say(f"      AI error {type(e).__name__}")
            prog += extra
            how = "rules+AI" if len(prog) > len(extra) else "AI"
        body = home.HomeBody(m, messes).run(prog)
        ok = bool(prog) and bool(check(body))
        rows.append({"prompt": p, "how": how, "passed": ok, "problems": body.problems[:3],
                     "program": prog, "seconds": round(sum(f[0] for f in body.frames), 1)})
        say(f"[{i + 1:2d}] {'PASS' if ok else 'fail'} {how:9s} {p}" + (f"   ({body.problems[0]})" if body.problems else ""))
    return rows


def do_task(command, m, brain=None, library=None, messes=None, say=print):
    """Rules first; then a skill the robot wrote for itself earlier (no model call); then the AI composes one.
    -> (program, how, ai_part, key) - key is what to pass to library.learn once the outcome is known."""
    prog, unknown = plan(command)
    if not unknown:
        return prog, "rules", [], None
    key = ", ".join(unknown)
    hit = library.recall(key) if library is not None else None
    if hit and not home.HomeBody(m, messes).run(prog + hit["program"]).problems:     # re-checked with the new objects
        say(f"  own skill '{hit['name']}' (p={hit['p']}, used {hit['tries']}x): no model call")
        return prog + hit["program"], "own skill", hit["program"], key
    if brain is None:
        return prog, "not understood", [], key
    extra, _ = think(key, m, brain, say=say, messes=messes)
    return prog + extra, "AI", extra, key
