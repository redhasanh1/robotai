"""Does the robot's own skill library pay off? (Kimi round 10: skill composition, hand/skills.py)

Requests the built-in rules can't do. Three passes over one growing library:
  1  first time: the AI composes a program from the robot's skills; if it works it is saved as a named skill
  2  the same requests again: the robot should just do them - no model call
  3  new wordings / other objects ("hide the book" after learning "hide the remote"): slots + body check
For each pass: tasks done, model calls, model seconds.

    .venv/Scripts/python tools/skill_growth.py            # scripted teacher writes pass 1 (tests the LIBRARY only)
    .venv/Scripts/python tools/skill_growth.py --ai       # the local model at :8766 writes pass 1 (the real test)
Writes results/skill_growth.md (teacher) or results/skill_growth_ai.md.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import home, home_tasks as H, skills  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

LR = ["ball", "book", "remote", "soda can"]
LAUNDRY = ["red shirt", "white shirt", "towel"]


def _in(o):
    return lambda b: b.where[o][0] == "in"


def _on(o, room):
    return lambda b: b.where[o] == ("on", room)


REQUESTS = [  # (request, done?, what a person would do - the scripted teacher's program)
    ("hide the remote", _in("remote"), [{"do": "put_in", "obj": "remote", "into": "basket"}]),
    ("put the toy away", _in("ball"), [{"do": "put_in", "obj": "ball", "into": "basket"}]),
    ("set the table in the living room", lambda b: _on("cup", "living room")(b) and _on("plate", "living room")(b),
     [{"do": "put_on", "obj": "cup", "room": "living room"}, {"do": "put_on", "obj": "plate", "room": "living room"}]),
    ("clear the living room table", lambda b: not any(b.where[o] == ("on", "living room") for o in home.OBJECTS),
     [{"do": "put_in", "obj": "ball", "into": "basket"}] +
     [{"do": "put_on", "obj": o, "room": "kitchen"} for o in ("book", "remote", "soda can")]),
    ("empty the laundry counter onto the living room table", lambda b: all(_on(o, "living room")(b) for o in LAUNDRY),
     [{"do": "put_on", "obj": o, "room": "living room"} for o in LAUNDRY]),
    ("put the laundry away", lambda b: b.where["towel"] == ("in", "basket"),
     [{"do": "put_in", "obj": "towel", "into": "basket"}]),
    ("clear the kitchen counter",
     lambda b: not any(b.where[o] == ("on", "kitchen") for o in home.OBJECTS if o != "sponge"),
     [{"do": "put_in", "obj": "cup", "into": "rack"}, {"do": "put_in", "obj": "plate", "into": "rack"},
      {"do": "put_on", "obj": "apple", "room": "living room"}]),
]
VARIANTS = [  # new wording or other objects; last two share no template with anything learned (honest misses)
    ("hide the book", _in("book")),
    ("please hide the soda can", _in("soda can")),
    ("hide the apple", _in("apple")),
    ("put the book away", _in("book")),
    ("set the table in the kitchen", lambda b: _on("cup", "kitchen")(b) and _on("plate", "kitchen")(b)),
    ("clear the laundry counter", lambda b: not any(b.where[o] == ("on", "laundry") for o in home.OBJECTS)),
]


class Teacher:
    """Stands in for the model in pass 1: returns what a person would do. Counts as a model call."""

    def __init__(self):
        self.book = {H.plan(r)[1] and ", ".join(H.plan(r)[1]): p for r, _, p in REQUESTS}
        self.calls = []

    def program(self, command, world, doc, **kw):
        self.calls.append(0.0)
        return {"program": self.book.get(command, []), "say": ""}


def run_pass(name, items, m, brain, lib, say):
    rows = []
    for req, done, *_ in items:
        n0, t0 = len(brain.calls), sum(brain.calls)
        prog, how, ai_part, key = H.do_task(req, m, brain, lib, say=lambda s: None)
        body = home.HomeBody(m).run(prog)
        ok = bool(prog) and not body.problems and bool(done(body))
        if key and how in ("AI", "own skill"):
            lib.learn(key, ai_part, ok)
        calls, secs = len(brain.calls) - n0, sum(brain.calls) - t0
        rows.append((req, how, ok, calls, secs))
        say(f"  [{name}] {'PASS' if ok else 'fail'} {how:10s} calls={calls} {secs:5.1f}s  {req}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true")
    a = ap.parse_args()
    m = build_model(meshes=False, extra=home.scene_xml(), mobile=True)
    for r, _, _ in REQUESTS + [(v, None, None) for v, _ in VARIANTS]:
        assert H.plan(r)[1], f"rules already do '{r}' - not a held-out request"
    if a.ai:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from robot_do import get_brain
        brain, url = get_brain()
        if url is None:
            sys.exit("no model running on :8766 (panel: Start AI brain)")
    else:
        brain = Teacher()
    lib = skills.Library()
    t0 = time.time()
    passes = [("1 first time", REQUESTS), ("2 again", REQUESTS), ("3 new wording/objects", VARIANTS)]
    table = []
    for name, items in passes:
        rows = run_pass(name, items, m, brain, lib, print)
        table.append((name, len(rows), sum(r[2] for r in rows), sum(r[3] for r in rows), sum(r[4] for r in rows),
                      sum(r[1] == "own skill" for r in rows), rows))
    who = "the local model (Qwen2.5-3B 4-bit, :8766)" if a.ai else \
        "a SCRIPTED TEACHER in pass 1 (measures the library, not the model's composing)"
    out = [f"# Skills the robot writes for itself (tools/skill_growth.py{' --ai' if a.ai else ''})", "",
           f"Pass 1 programs come from {who}. Every task starts from the same clean house.", "",
           "| pass | tasks | done | model calls | model seconds | done by its own skill |", "|---|---|---|---|---|---|"]
    for name, n, ok, calls, secs, own, _ in table:
        out.append(f"| {name} | {n} | {ok}/{n} | {calls} | {secs:.0f} | {own} |")
    out += ["", "| pass | request | how | done | calls |", "|---|---|---|---|---|"]
    for name, *_, rows in table:
        out += [f"| {name[0]} | {r} | {h} | {'yes' if ok else 'no'} | {c} |" for r, h, ok, c, _ in rows]
    out += ["", "Skills in the library afterwards:", ""]
    out += [f"- `{k}` (from \"{v['from']}\", {v['wins']}/{v['tries']} worked): {v['program']}"
            for k, v in lib.skills.items()]
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results",
                        "skill_growth_ai.md" if a.ai else "skill_growth.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out[4:4 + len(table) + 2]), f"\n({time.time() - t0:.0f} s) -> {path}")


if __name__ == "__main__":
    main()
