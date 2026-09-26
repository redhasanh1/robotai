"""Watch the brain loop work in the MuJoCo sim.

    .venv/Scripts/python tools/demo.py                  # live 3D window, stub brain, all four objects
    .venv/Scripts/python tools/demo.py --watch          # slow motion, loops forever (close the window to go on,
                                                        # Ctrl+C in the terminal to stop)
    .venv/Scripts/python tools/demo.py --video demo.mp4 # no window: save a video instead
    BRAIN=openai .venv/Scripts/python tools/demo.py     # real model (BRAIN_URL / BRAIN_KEY or CEREBRAS_API_KEY)

For each object the brain picks a grasp family, the physics predicts 8 variants, the brain ranks them, the
self-check retries on failure, and the final grasp is played back: close, turn over (gravity flips), shake.
The console shows what it chose and why.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, loop, memory, primitives  # noqa: E402

PHASES = [(0.8, None), (0.2, (0, 0, 9.81))] + [(0.2, (0, 3.0 if k % 2 == 0 else -3.0, 9.81)) for k in range(4)]


def play(world, q, on_frame):
    world.set_target(q)
    for secs, g in PHASES:
        if g is not None:
            world.model.opt.gravity[:] = g
        for _ in range(int(secs / 0.02)):
            world.step(0.02)
            on_frame(world)


def report(obj, r):
    for s in r.log:
        if s["step"] == "veto":
            print(f"[{obj}] physics veto: {s['family']} - {s['why']}")
        elif s["step"] in ("choose", "rank"):
            what = s.get("family", s.get("order"))
            print(f"[{obj}] {s['step']}: {what} - {s['why']} ({s['latency'] * 1000:.0f} ms)")
        elif s["step"] == "execute":
            print(f"[{obj}] try {s['try']}: {s['cand']} physics said {'hold' if s['pred'] else 'drop'}"
                  f" -> {'HELD' if s['truth'] else 'dropped'}")
    print(f"[{obj}] {'SUCCESS' if r.success else 'FAILED'} after {r.tries} tr{'y' if r.tries == 1 else 'ies'}, "
          f"{r.seconds:.2f} s thinking + physics\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--say", default="", help='a command, e.g. --say "pick up the orange"')
    a = ap.parse_args()
    b = brain.make(os.environ.get("BRAIN", "stub:cerebras"))
    mem = memory.Memory()
    frames = []
    slow = 3.0 if (a.watch or a.say) else 1.0
    objs = ["ball", "can", "block", "bar"]
    rounds = 1                                  # play each object once, then stop (no endless loop)
    todo = [(k, objs[k % 4]) for k in range(4 * rounds)]
    if a.say:
        plan = b.plan(a.say)
        print(f'you: "{a.say}"')
        for st in plan["steps"]:
            print(f"  step: {st.get('skill')} {st.get('object', '')}" + ("" if st["ready"] else "   (skill not built yet)"))
        print(f"robot: {plan['say']}", flush=True)
        todo = [(0, st["sim_object"]) for st in plan["steps"] if st["ready"]][:1]
        if not todo:
            return
    for i, obj in todo:
        r = loop.attempt(f"pick up the {obj}", obj, b, mem, n=a.n, seed=i, verify=True)
        report(obj, r)
        q = primitives.shape(r.chosen["family"], r.chosen["s"], r.chosen["t"])
        world = loop.randomized_world(obj, i)
        if a.video:
            play(world, q, lambda w: frames.append(w.render("front", 480, 360)))
        else:
            import mujoco.viewer
            with mujoco.viewer.launch_passive(world.model, world.data) as v:
                v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.45, 130, -25
                v.cam.lookat[:] = (0.03, 0, 0.11)
                time.sleep(1.0 * slow)
                play(world, q, lambda w: (v.sync(), time.sleep(0.02 * slow)))
                time.sleep(1.5 * slow)
                while a.say and v.is_running():         # a single command: keep the result on screen until closed
                    v.sync()
                    time.sleep(0.05)
    if a.video:
        import cv2
        vw = cv2.VideoWriter(a.video, cv2.VideoWriter_fourcc(*"mp4v"), 50, (480, 360))
        for f in frames:
            vw.write(f[:, :, ::-1])
        vw.release()
        print("saved", a.video)


if __name__ == "__main__":
    main()
