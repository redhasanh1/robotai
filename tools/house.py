"""Tell the InMoov what to do around the house; it plans, checks it on its body, then does it in the sim.

    .venv/Scripts/python tools/house.py "do the dishes, then bring me the apple"
    .venv/Scripts/python tools/house.py "I'm thirsty"
    .venv/Scripts/python tools/house.py --random            # one of the 50 test prompts
    .venv/Scripts/python tools/house.py --showcase          # a long run through the whole house
    .venv/Scripts/python tools/house.py --score [--ai]      # the 50-prompt test (rules, or rules + AI brain)
    add --video out.mp4 to save instead of opening a window

Rules understand the usual phrasings; judgement calls ("I spilled something in the living room") go to the AI
brain (the local model on :8766 when it's running - panel "Start AI brain" - or BRAIN_URL), which writes its own
program, gets it checked on the body, and repairs it. The window keeps the last pose until you close it.
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain as brain_mod, home, home_tasks as H, motor  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robot_do import get_brain  # noqa: E402

SHOWCASE = "do the dishes, then do the laundry, then bring me the remote, then wipe the kitchen counter, then wave"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="*")
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--showcase", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--ai", action="store_true", help="with --score: use the AI brain for what rules don't get")
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    say = lambda s: print(s, flush=True)
    import mujoco
    if a.score:
        m = build_model(meshes=False, extra=home.scene_xml(), mobile=True)
        brain, url = get_brain() if a.ai else (None, None)
        if a.ai and url is None:
            say("no AI brain running (panel: Start AI brain) - scoring with rules only")
            brain = None
        rows = H.score(m, brain if url else None, say=say)
        passed = sum(r["passed"] for r in rows)
        say(f"\n{passed}/50 passed ({'rules + AI at ' + url if url else 'rules only'})")
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        with open(os.path.join(ROOT, "logs", f"house_score_{'ai' if url else 'rules'}.json"), "w") as f:
            json.dump(rows, f, indent=1, default=str)
        return
    command = SHOWCASE if a.showcase else (random.choice(H.PROMPTS)[0] if a.random or not a.command
                                           else " ".join(a.command))
    m = build_model(extra=home.scene_xml(), mobile=True)
    say(f'task: "{command}"')
    prog, unknown = H.plan(command)
    said, seen = "", {}
    if a.showcase:            # someone spills in the living room; after the chores the robot checks every counter
        from hand import perceive
        eyes = perceive.Eyes(m).learn()
        perceive.set_messes(m, {"living room"})
        seen = eyes.survey()
        for room, what in seen.items():
            say(f"  counter camera, {room}: {what} - wiping it after the chores")
        prog += [{"do": "wipe", "room": r} for r in seen]
    if unknown:
        brain, url = get_brain()
        rest = ", ".join(unknown)
        if url:
            say(f'  thinking about "{rest}" with the AI brain - ~30-60 s on the laptop GPU...')
            t0 = time.time()
            try:
                extra, said = H.think(rest, m, brain, say=say)
                prog += extra
            except (OSError, ValueError, KeyError) as e:
                say(f"  AI brain stopped answering ({type(e).__name__})")
            say(f"  thought for {time.time() - t0:.0f} s")
        else:
            say(f'  "{rest}" needs thinking - start the AI brain (panel) and ask again')
    for step in prog:
        say("  step: " + json.dumps(step))
    if not prog:
        say("robot: I don't know how to do that yet.")
        return
    body = home.HomeBody(m, seen).run(prog)
    words = ([said] if said else []) + body.said
    say("robot: " + ("; ".join(words) or "done.") +
        (f"  (couldn't do: {'; '.join(body.problems[:3])})" if body.problems else "") +
        f"  [{sum(f[0] for f in body.frames):.0f} s]")
    d = mujoco.MjData(m)
    cam = dict(lookat=(0.0, 0.5, 0.7), distance=4.6, azimuth=90, elevation=-50)
    if a.video:
        import cv2
        r = mujoco.Renderer(m, 480, 640)
        c = mujoco.MjvCamera()
        c.lookat[:], c.distance, c.azimuth, c.elevation = cam["lookat"], cam["distance"], cam["azimuth"], cam["elevation"]
        vw = cv2.VideoWriter(a.video, cv2.VideoWriter_fourcc(*"mp4v"), 50, (640, 480))
        motor.play(m, d, body.frames, lambda: (r.update_scene(d, c), vw.write(r.render()[:, :, ::-1])))
        vw.release()
        say("saved " + a.video)
        return
    import mujoco.viewer
    with mujoco.viewer.launch_passive(m, d) as v:
        v.cam.lookat[:] = cam["lookat"]
        v.cam.distance, v.cam.azimuth, v.cam.elevation = cam["distance"], cam["azimuth"], cam["elevation"]
        motor.play(m, d, body.frames, lambda: (v.sync(), time.sleep(0.02)))
        while v.is_running():
            v.sync()
            time.sleep(0.05)


if __name__ == "__main__":
    main()
