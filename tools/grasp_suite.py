"""Every rule-planned house task with the real grasps, on the model you choose - clean count + what goes wrong.

    .venv/Scripts/python tools/grasp_suite.py              # the InMoov meshes (what the viewer shows)
    .venv/Scripts/python tools/grasp_suite.py --skeleton   # capsule arms (what the tests use)
"""
import argparse
import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import collide, home, home_tasks as H  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skeleton", action="store_true")
    ap.add_argument("--replay", action="store_true", help="also replay at 50 Hz and count contacts > 2 mm")
    a = ap.parse_args()
    m = build_model(meshes=not a.skeleton, extra=home.scene_xml(), mobile=True)
    t0 = time.time()
    why, bad, ok, n, touched = collections.Counter(), [], 0, 0, 0
    for p, check in H.PROMPTS:
        prog, unknown = H.plan(p)
        if unknown:
            continue
        n += 1
        try:
            b = home.HomeBody(m).run(prog)
        except Exception as e:                       # a crash is a result too
            why[f"CRASH {type(e).__name__}: {e}"[:80]] += 1
            bad.append(p)
            continue
        good = not b.problems and bool(check(b))
        ok += good
        if not good:
            bad.append(p)
        for pr in b.problems[:1]:
            why[pr.split(": ", 1)[-1][:80]] += 1
        if a.replay and good:
            touched += bool(collide.sweep(m, b, stride=2))
    print(f"{ok}/{n} clean ({'skeleton' if a.skeleton else 'meshes'}, {time.time() - t0:.0f} s)"
          + (f"; {touched} of the clean ones touch something > 2 mm in the replay" if a.replay else ""))
    for k, v in why.most_common(12):
        print(f"  {v:2d}  {k}")
    print("failing:", bad)


if __name__ == "__main__":
    main()
