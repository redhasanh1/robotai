"""Random things in the way: every rule-planned house task on randomly cluttered counters.

Each layout puts every object at a random spot on its own counter (inside the strip the arms reach, not on the
containers, at least 7 cm apart). For every task: did it get done, did the planner flag a problem, and does the 50 Hz
replay show the arm inside anything (> 5 mm)? Run with the robot moving obstacles aside and without.

    .venv/Scripts/python tools/clutter.py [--layouts 10]      # writes results/clutter.md
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import collide, home, home_tasks as H, perceive  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402


def layout(rng):
    """{object: world xyz}: each object somewhere random on its own counter."""
    pos = {}
    for room in ("kitchen", "laundry", "living room"):
        boxes = [np.array(c[1]) for c in home.CONTAINERS.values() if c[0] == room]
        taken = []
        for o in [o for o, v in home.OBJECTS.items() if v[0] == room]:
            for _ in range(500):
                p = np.array([rng.uniform(-0.36, 0.36), rng.uniform(-0.35, -0.25)])
                if all(np.linalg.norm(p - q) > 0.07 for q in taken) and all(np.linalg.norm(p - b) > 0.13 for b in boxes):
                    break
            taken.append(p)
            xy = home.to_world(room, p)
            pos[o] = np.array([xy[0], xy[1], home.TABLE_Z + home.OBJECTS[o][5]])
    return pos


def run(m, tasks, layouts, clear, seen=None, margin=False):
    """seen: per layout, what the cameras made of it ({obj: (xyz, sigma)}) - the robot plans from that, the replay
    checks against where things really were."""
    home.AUTO_CLEAR = clear
    done = flagged = deep = total = 0
    for i, pos in enumerate(layouts):
        for p, check in tasks:
            b = home.HomeBody(m)
            if seen is None:
                b.pos = {o: v.copy() for o, v in pos.items()}
            else:
                b.pos = {o: (seen[i][o][0] if o in seen[i] else pos[o]).copy() for o in pos}
                b.true_pos0 = {o: v.copy() for o, v in pos.items()}
                if margin:
                    b.pos_sigma = {o: sig for o, (_, sig) in seen[i].items()}
            b.run(H.plan(p)[0])
            total += 1
            flagged += bool(b.problems)
            done += bool(check(b)) and not b.problems
            deep += any(h["depth"] > 0.005 for h in collide.sweep(m, b, stride=2))
    return total, done, flagged, deep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layouts", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    m = build_model(meshes=False, extra=home.scene_xml(), mobile=True)
    rng = np.random.default_rng(a.seed)
    layouts = [layout(rng) for _ in range(a.layouts)]
    tasks = [(p, c) for p, c in H.PROMPTS if not H.plan(p)[1]]
    eyes = perceive.Eyes(m).learn_empty()
    seen = []
    for pos in layouts:                       # what the counter cameras make of each layout (hand/perceive.py)
        for o, p in pos.items():
            eyes.d.mocap_pos[m.body_mocapid[m.body(home.mocap_name(o)).id]] = p
        seen.append(eyes.locate())
    arms = [("told where things are", False, None, False), ("told, moves obstacles aside", True, None, False),
            ("seen by its cameras, moves obstacles", True, seen, False),
            ("seen, + 2-sigma margin round each seen object", True, seen, True)]
    rows = []
    for label, clear, sn, margin in arms:
        t0 = time.time()
        total, done, flagged, deep = run(m, tasks, layouts, clear, sn, margin)
        rows.append((label, total, done, flagged, deep, time.time() - t0))
        print(f"{label}: {done}/{total} done, {flagged} flagged, {deep} with the arm >5 mm inside something "
              f"({time.time() - t0:.0f} s)", flush=True)
    home.AUTO_CLEAR = True
    out = ["# Random things in the way (tools/clutter.py)", "",
           f"{a.layouts} random layouts (seed {a.seed}): every object at a random spot on its own counter, >= 7 cm "
           f"apart, off the containers. {len(tasks)} rule-planned tasks on each.", "",
           "| robot | runs | done cleanly | planner flagged a problem | arm > 5 mm inside something "
           "in the replay |", "|---|---|---|---|---|"]
    out += [f"| {c} | {t} | {d} ({100 * d / t:.0f}%) | {f} | {dp} |" for c, t, d, f, dp, _ in rows]
    out += ["", "'Flagged' means the body check caught it before doing it (a real robot would not try); the replay "
            "column is what would have hit something anyway."]
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "clutter.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("->", path)


if __name__ == "__main__":
    main()
