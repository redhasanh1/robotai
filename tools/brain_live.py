"""Replace ASSUMED brain speed with MEASURED, and run the real model through the real loop (Kimi round 4: the
thesis must be measured, not asserted).

    $env:CEREBRAS_API_KEY = "..."                       # PowerShell, never commit it
    .venv/Scripts/python tools/brain_live.py            # Cerebras (default BRAIN_URL)
    $env:BRAIN_URL = "http://localhost:8000/v1"; $env:BRAIN_MODEL = "..."; .venv/Scripts/python tools/brain_live.py
                                                        # any other OpenAI-compatible server (vLLM, llama.cpp, ...)

1. latency: real choose + rank calls with a rendered camera image, N = 1, 4, 8, 16, 3 repeats each
2. episodes: 8 real episodes (4 objects x 2) through hand.loop with the real model choosing, ranking and judging
Writes logs/brain_live_<label>.json; tools/bench.py prints measured rows next to the assumed ones.
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, loop, memory, primitives, sim  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latency(b, image, ns=(1, 4, 8, 16), reps=3):
    rows = []
    for n in ns:
        cands = primitives.sample("power", n, __import__("numpy").random.default_rng(0))
        for c in cands:
            c["pred"] = {"held": True, "touching": ["thumb", "index"], "dist": 0.03}
        ch, rk = [], []
        for _ in range(reps):
            b.choose("pick up the ball", image, "No past attempts yet.", "ball")
            ch.append(b.last_latency)
            b.rank("pick up the ball", image, cands, "No past attempts yet.")
            rk.append(b.last_latency)
        rows.append({"n": n, "choose_s": round(statistics.median(ch), 3), "rank_s": round(statistics.median(rk), 3),
                     "decision_s": round(statistics.median(ch) + statistics.median(rk), 3)})
        print("latency", rows[-1], flush=True)
    return rows


def episodes(b):
    mem = memory.Memory()
    out = []
    for k in range(8):
        obj = ["ball", "can", "block", "bar"][k % 4]
        try:
            r = loop.attempt(f"pick up the {obj}", obj, b, mem, n=8, seed=200 + k, render=True)
            out.append({"object": obj, "success": r.success, "tries": r.tries, "brain_s": round(r.brain_s, 3),
                        "family": r.family, "log": r.log})
            print(f"episode {k}: {obj} {'HELD' if r.success else 'dropped'} in {r.tries} tries, "
                  f"brain {r.brain_s:.2f} s", flush=True)
        except Exception as e:          # a bad JSON reply is a result too - record it, keep going
            out.append({"object": obj, "error": str(e)[:200]})
            print(f"episode {k}: {obj} ERROR {e}", flush=True)
    return out


def main():
    b = brain.OpenAIBrain()
    if not b.key and "cerebras" in b.url:
        sys.exit("Set CEREBRAS_API_KEY first (PowerShell: $env:CEREBRAS_API_KEY = '...').")
    label = os.environ.get("BRAIN_LABEL", "cerebras" if "cerebras" in b.url else "other")
    image = sim.SimHand("ball").render("front", 320, 240)
    print(f"brain: {b.url} model {b.model}")
    r = {"when": time.strftime("%Y-%m-%d %H:%M"), "url": b.url, "model": b.model,
         "latency": latency(b, image), "episodes": episodes(b)}
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    path = os.path.join(ROOT, "logs", f"brain_live_{label}.json")
    json.dump(r, open(path, "w"), indent=1)
    ok = [e for e in r["episodes"] if "success" in e]
    print(f"\n{sum(e['success'] for e in ok)}/{len(ok)} held with the real model; saved {path}")


if __name__ == "__main__":
    main()
