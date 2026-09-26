"""Ask once, never again (Kimi round 11): does one good question beat guessing, and is it never asked twice?

12 requests that are each missing one fact: WHICH of two things ("the shirt" - there are two), or WHERE something
lives ("put the book away"). A simulated person knows the answers (TRUTH) and answers any question truthfully.
  today   the planner as it was: no questions (it does both shirts, or doesn't understand "away")
  guess   the robot fills the gap itself (first idea, or a common-sense guess by kind) and sticks with it
  ask     the robot may ask ONE question per request; the answer is kept in house knowledge
  again   the same 12 requests later, same knowledge: it should ask nothing

    .venv/Scripts/python tools/ask_once.py        # writes results/ask_once.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import ask as A, home, home_tasks as H  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

TRUTH = {"means": {"shirt": "white shirt", "dish": "plate"},
         "homes": {"towel": "basket", "ball": "basket", "cup": "rack", "plate": "rack", "soda can": "kitchen",
                   "book": "kitchen", "sponge": "sink"}}


def _at(o, place):
    want = ("in", place) if place in home.CONTAINERS else ("on", place)
    return lambda b: b.where[o] == want


def _only(o, other, test):
    """Done to o - and the other one left where it was (doing both is not what was asked)."""
    return lambda b: test(b) and b.where[other] == ("on", home.OBJECTS[other][0])


TASKS = [
    ("put the towel away", _at("towel", "basket")),
    ("put the ball away", _at("ball", "basket")),
    ("put the cup away", _at("cup", "rack")),
    ("put the soda can back", _at("soda can", "kitchen")),
    ("put the book away", _at("book", "kitchen")),
    ("put the sponge back", _at("sponge", "sink")),
    ("put the shirt in the washer", _only("white shirt", "red shirt", _at("white shirt", "washer"))),
    ("bring me the dish", _only("plate", "cup", lambda b: b.where["plate"][0] == "given")),
    ("put the dish in the sink", _only("plate", "cup", _at("plate", "sink"))),
    ("hand me the shirt", _only("white shirt", "red shirt", lambda b: b.where["white shirt"][0] == "given")),
    ("put the plate away", _at("plate", "rack")),
    ("put the shirt on the living room table", _only("white shirt", "red shirt", _at("white shirt", "living room"))),
]


def person(q):
    """Answers truthfully, in words, the way a person would."""
    if q["kind"] == "which":
        return f"the {TRUTH['means'][q['about']]}"
    place = TRUTH["homes"][q["about"]]
    return f"it goes in the {place}" if place in home.CONTAINERS else f"it lives in the {place}"


def guesser(q):
    """The strawman: always its first idea."""
    return q["options"][0]


KIND_HOME = {"dish": "rack", "food": "kitchen", "tool": "sink", "dirty clothes": "washer", "clean clothes": "basket",
             "toy": "basket", "book": "living room", "remote": "living room", "trash": "kitchen"}


def common_sense(q):
    """A fair guess, the kind a model would make: where that KIND of thing usually lives; for 'which', the first."""
    if q["kind"] == "which":
        return q["options"][0]
    return KIND_HOME.get(home.OBJECTS[q["about"]][6], q["options"][0])


def run(m, name, know, ask):
    rows = []
    for cmd, done in TASKS:
        if ask == "today":
            prog, unknown = H.plan(cmd)
            asked = []
        else:
            prog, unknown, asked = A.plan(cmd, know, ask=ask)
        b = home.HomeBody(m).run(prog) if prog else None
        ok = b is not None and not unknown and not b.problems and bool(done(b))
        rows.append((cmd, ok, asked))
    return rows


def main():
    m = build_model(meshes=False, extra=home.scene_xml(), mobile=True)
    know = A.Knowledge()
    arms = [("today", run(m, "today", None, "today")),
            ("guess (first idea)", run(m, "guess", A.Knowledge(), guesser)),
            ("guess (common sense)", run(m, "sense", A.Knowledge(), common_sense)),
            ("ask one question", run(m, "ask", know, person)),
            ("again (same knowledge)", run(m, "again", know, person))]
    out = ["# Ask once, never again (tools/ask_once.py)", "",
           "12 requests each missing one fact (which of two things / where something lives). A simulated person "
           "answers truthfully. The robot may ask at most one question per request; answers are kept.", "",
           "| robot | done | questions asked |", "|---|---|---|"]
    for name, rows in arms:
        out.append(f"| {name} | {sum(r[1] for r in rows)}/12 | {sum(len(r[2]) for r in rows)} |")
        print(f"{name:24s} {sum(r[1] for r in rows):2d}/12 done, {sum(len(r[2]) for r in rows)} questions", flush=True)
    out += ["", "| request | today | common-sense guess | ask | question it asked |", "|---|---|---|---|---|"]
    for i, (cmd, _) in enumerate(TASKS):
        t, g, a = arms[0][1][i], arms[2][1][i], arms[3][1][i]
        out.append(f"| {cmd} | {'yes' if t[1] else 'no'} | {'yes' if g[1] else 'no'} | {'yes' if a[1] else 'no'} | "
                   f"{a[2][0] if a[2] else '-'} |")
    out += ["", f"House knowledge afterwards: which = {know.means}; lives in = {know.homes}"]
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "ask_once.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("->", path)


if __name__ == "__main__":
    main()
