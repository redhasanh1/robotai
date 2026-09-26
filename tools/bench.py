"""Capstone benchmark, all in simulation (seconds are virtual, see hand/loop.py).

    .venv/Scripts/python tools/bench.py                 # all experiments, ~10 min on CPU
    .venv/Scripts/python tools/bench.py --quick         # 4 seeds per cell, ~2 min
    BRAIN=openai .venv/Scripts/python tools/bench.py --live   # also run a few episodes on the real endpoint

Experiments (Kimi round 3: four graphs, zero gradient steps):
  1. best_of_n   success vs N candidates (brain ranks all N in one call); self-check AND veto off to isolate ranking
  2. verifier    success with vs without the self-check (retry on detected failure), N=4, no veto
  3. veto        physics veto on vs off (replan the family before acting when physics predicts all N drop), N=8
  4. memory      first-try success over successive episodes, with vs without episodic memory
  5. holdout     full system vs blind single try, in the development world and in a HELD-OUT contact model
  6. speed       decision latency vs N for each brain profile, and the largest N that fits a time budget
Results -> logs/bench.json and logs/bench.md (tables). Latency profiles for local / rented / Cerebras are
ASSUMPTIONS in hand/brain.py until tools/cerebras_latency.py and a rented-GPU run replace them.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, loop, memory  # noqa: E402

OBJECTS = ["ball", "can", "block", "bar"]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def rate(results):
    return round(sum(r.success for r in results) / max(1, len(results)), 3)


def best_of_n(seeds, ns=(1, 2, 4, 8, 16)):
    rows = []
    for n in ns:
        res = [loop.attempt(f"pick up the {o}", o, brain.StubBrain("instant"), None, n=n, seed=s, verify=False,
                            veto=False) for o in OBJECTS for s in range(seeds)]
        rows.append({"n": n, "success": rate(res), "physics_s": round(sum(r.physics_s for r in res) / len(res), 3)})
        print("best_of_n", rows[-1], flush=True)
    return rows


def verifier(seeds, n=4):
    rows = []
    for v in (False, True):
        res = [loop.attempt(f"pick up the {o}", o, brain.StubBrain("instant", verdict_error=0.05, seed=s), None,
                            n=n, seed=s, verify=v, veto=False) for o in OBJECTS for s in range(seeds)]
        rows.append({"verify": v, "success": rate(res), "tries": round(sum(r.tries for r in res) / len(res), 2)})
        print("verifier", rows[-1], flush=True)
    return rows


def veto(seeds, n=8):
    rows = []
    for v in (False, True):
        res = [loop.attempt(f"pick up the {o}", o, brain.StubBrain("instant"), None, n=n, seed=s, verify=False,
                            veto=v) for o in OBJECTS for s in range(seeds)]
        rows.append({"veto": v, "success": rate(res)})
        print("veto", rows[-1], flush=True)
    return rows


def holdout(seeds):
    rows = []
    for world in ("dev", "holdout"):
        h = world == "holdout"
        blind = [loop.attempt(f"pick up the {o}", o, brain.StubBrain("instant"), None, n=1, seed=100 + s,
                              verify=False, veto=False, holdout=h) for o in OBJECTS for s in range(seeds)]
        full = [loop.attempt(f"pick up the {o}", o, brain.StubBrain("instant", verdict_error=0.05, seed=s),
                             memory.Memory(), n=8, seed=100 + s, holdout=h) for o in OBJECTS for s in range(seeds)]
        rows.append({"world": world, "blind_single_try": rate(blind), "full_system": rate(full),
                     "tries": round(sum(r.tries for r in full) / len(full), 2)})
        print("holdout", rows[-1], flush=True)
    return rows


def memory_curve(episodes, n=4):
    out = {}
    for use in (False, True):
        mem = memory.Memory()
        b = brain.StubBrain("instant")
        curve = []
        for e in range(episodes):
            o = OBJECTS[e % len(OBJECTS)]
            r = loop.attempt(f"pick up the {o}", o, b, mem, n=n, seed=1000 + e, verify=True, use_memory=use)
            curve.append({"episode": e, "object": o, "first_try": r.tries == 1 and r.success, "tries": r.tries})
        out["with_memory" if use else "no_memory"] = curve
        half = episodes // 2
        print("memory", use, "first-try success 1st half",
              sum(c["first_try"] for c in curve[:half]), "/", half, "2nd half",
              sum(c["first_try"] for c in curve[half:]), "/", episodes - half, flush=True)
    return out


def speed(budget_s=1.0, ns=(1, 2, 4, 8, 16, 32)):
    rows = []
    for prof in ("local_1660ti", "rented_gpu", "cerebras"):
        b = brain.StubBrain(prof)
        lat = {}
        for n in ns:
            b.calls.clear()
            b.choose("x", None, "", "ball")
            b.rank("x", None, [{"family": "power", "s": 0.8, "t": 0.9,
                                "pred": {"held": True, "touching": [], "dist": 0.03}}] * n, "")
            lat[n] = round(sum(b.calls), 3)
        fits = max([n for n in ns if lat[n] <= budget_s], default=0)
        rows.append({"profile": prof, "decision_s": lat, "max_n_within_budget": fits, "budget_s": budget_s})
        print("speed", rows[-1], flush=True)
    return rows


def to_md(r):
    L = ["# Benchmark (simulation)", "", f"_{r['when']}; seeds per cell: {r['seeds']}; latency profiles are assumptions "
         "until measured_", "", "## 1. Best of N (self-check off)", "", "| N | success | physics s/decision |",
         "|---|---|---|"]
    L += [f"| {x['n']} | {x['success']:.0%} | {x['physics_s']} |" for x in r["best_of_n"]]
    L += ["", "## 2. Self-check", "", "| self-check | success | tries/task |", "|---|---|---|"]
    L += [f"| {'on' if x['verify'] else 'off'} | {x['success']:.0%} | {x['tries']} |" for x in r["verifier"]]
    L += ["", "## 3. Physics veto (N=8, self-check off)", "", "| veto | success |", "|---|---|"]
    L += [f"| {'on' if x['veto'] else 'off'} | {x['success']:.0%} |" for x in r["veto"]]
    L += ["", "## 4. Memory (first-try success, first half vs second half of the run)", ""]
    for k, c in r["memory"].items():
        h = len(c) // 2
        L.append(f"- {k}: {sum(e['first_try'] for e in c[:h])}/{h} -> {sum(e['first_try'] for e in c[h:])}/{len(c) - h}")
    L += ["", "## 5. Held-out contact model (softer contacts, pyramidal cone, condim 3 - nothing tuned on it)", "",
          "| world | blind single try | full system (N=8, veto, self-check, memory) | tries |", "|---|---|---|---|"]
    L += [f"| {x['world']} | {x['blind_single_try']:.0%} | {x['full_system']:.0%} | {x['tries']} |" for x in r["holdout"]]
    L += ["", f"## 6. Brain speed (decision = choose + rank all N, budget {r['speed'][0]['budget_s']} s)", "",
          "| brain | " + " | ".join(f"N={n}" for n in r["speed"][0]["decision_s"]) + " | max N in budget |",
          "|---|" + "---|" * (len(r["speed"][0]["decision_s"]) + 1)]
    L += [f"| {x['profile']} (assumed) | " + " | ".join(f"{v:.2f}s" for v in x["decision_s"].values()) +
          f" | {x['max_n_within_budget']} |" for x in r["speed"]]
    for f in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
        if f.startswith("brain_live_") and f.endswith(".json"):          # tools/brain_live.py measurements
            m = json.load(open(os.path.join(OUT, f)))
            lat = {x["n"]: x["decision_s"] for x in m["latency"]}
            L.append(f"| {f[11:-5]} MEASURED ({m['model']}, {m['when']}) | " +
                     " | ".join(f"{lat[int(n)]:.2f}s" if int(n) in lat else "-" for n in r["speed"][0]["decision_s"]) + " | |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--budget", type=float, default=1.0)
    a = ap.parse_args()
    seeds = 4 if a.quick else 12
    t0 = time.time()
    r = {"when": time.strftime("%Y-%m-%d %H:%M"), "seeds": seeds, "best_of_n": best_of_n(seeds),
         "verifier": verifier(seeds), "veto": veto(seeds), "holdout": holdout(seeds), "memory": memory_curve(16 if a.quick else 40), "speed": speed(a.budget)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "bench.json"), "w") as f:
        json.dump(r, f, indent=1)
    with open(os.path.join(OUT, "bench.md"), "w") as f:
        f.write(to_md(r))
    print(to_md(r))
    print(f"done in {time.time() - t0:.0f} s -> logs/bench.md")


if __name__ == "__main__":
    main()
