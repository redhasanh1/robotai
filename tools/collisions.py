"""Does the arm hit anything? Every rule-planned house task, replayed at 50 Hz with robot-vs-house contacts on.

    .venv/Scripts/python tools/collisions.py      # prints the table, writes results/collisions_now.md
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import collide, home, home_tasks as H  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--skeleton", action="store_true", help="capsule arms instead of the InMoov meshes (what tests use)")
    a = ap.parse_args()
    m = build_model(meshes=not a.skeleton, extra=home.scene_xml(), mobile=True)
    n = planner = over2 = over5 = 0
    kinds = collections.Counter()
    for p, _ in H.PROMPTS:
        prog, unknown = H.plan(p)
        if unknown:
            continue
        n += 1
        b = home.HomeBody(m).run(prog)
        planner += bool(b.problems)
        hits = collide.sweep(m, b, stride=1)
        over2 += bool(hits)
        over5 += any(h["depth"] > 0.005 for h in hits)
        for h in hits:
            kinds[(h["robot"].split("_")[0], h["hit"], (h["do"] or {}).get("do"), h["depth"] > 0.005)] += 1
    lines = ["| tasks | planner found a problem | any contact > 2 mm | any contact > 5 mm |", "|---|---|---|---|",
             f"| {n} | {planner} | {over2} | {over5} |", "", "| hand | touched | during | deeper than 5 mm | frames |",
             "|---|---|---|---|---|"]
    lines += [f"| {r} | {t} | {d} | {'yes' if deep else 'no'} | {c} |" for (r, t, d, deep), c in kinds.most_common(12)]
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "collisions_now_skeleton.md" if a.skeleton else "collisions_now.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
