"""Is the brain's grasp-FAMILY choice doing real work, or would a random family do as well? (Kimi round 5)

    .venv/Scripts/python tools/ablation.py          # ~10 min, writes results/ablation.md

Conditions x {bare (no veto, no self-check), full (veto + self-check)}:
  rank-8 + brain family | CEM (dense physics search) + brain family | CEM + RANDOM family
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, loop  # noqa: E402

OBJ = ["ball", "can", "block", "bar"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(seeds=12):
    rows = []
    for mode in ("bare", "full"):
        full = mode == "full"
        for search, fam in (("rank", "brain"), ("cem", "brain"), ("cem", "random"), ("rank", "random")):
            t = time.perf_counter()
            res = [loop.attempt(f"pick up the {o}", o, brain.StubBrain(), None, n=8, seed=300 + s, verify=full,
                                veto=full, search=search, family_policy=fam) for o in OBJ for s in range(seeds)]
            row = {"mode": mode, "search": search, "family": fam, "success": sum(r.success for r in res) / len(res),
                   "tries": sum(r.tries for r in res) / len(res),
                   "physics_s": sum(r.physics_s for r in res) / len(res), "n": len(res)}
            rows.append(row)
            print(row, f"{time.perf_counter() - t:.0f}s", flush=True)
    L = ["# Ablation: does the family choice matter?", "", f"_{time.strftime('%Y-%m-%d %H:%M')}, sim, stub brain, "
         f"{rows[0]['n']} tasks per row (4 objects x {seeds} seeds)_", "",
         "| safety | search | family | success | tries | physics s/task |", "|---|---|---|---|---|---|"]
    L += [f"| {r['mode']} | {r['search']} | {r['family']} | {r['success']:.0%} | {r['tries']:.2f} | "
          f"{r['physics_s']:.2f} |" for r in rows]
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    open(os.path.join(ROOT, "results", "ablation.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    run()
