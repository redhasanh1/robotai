"""Tell the full InMoov what to do. It plans it, checks it on its own body, and does it in the simulator.

    .venv/Scripts/python tools/robot_do.py "put the ball on the left, then wave"
    .venv/Scripts/python tools/robot_do.py "juggle the ball"
    .venv/Scripts/python tools/robot_do.py "hand the can from one hand to the other and give it to me"
    .venv/Scripts/python tools/robot_do.py --random | --showcase
    .venv/Scripts/python tools/robot_do.py --think "..."      # always let the AI write the program
    add --video out.mp4 to save instead of opening a window

How it thinks:
  1. Phrasings it already knows (pick/put/stack/give/point/push/look/wave/box/clap/nod/shake/tidy) become a program
     instantly.
  2. Anything else goes to the AI brain, which writes its own program from the action list in hand/motor.py
     (both arms, move_hand, grip, pass, toss/catch, joints...).
  3. The program is run on the body model first: out-of-reach targets, joint limits, empty grips, catches the hand
     can't make in time are reported back, and the AI repairs its own program (up to 2 rounds).
  4. Then it plays. The window keeps the last pose until you close it; nothing loops.
AI brain: BRAIN_URL if set, else the local model server on http://127.0.0.1:8766/v1 if it is running (panel button
"Start AI brain"), else built-in routines only. Held objects follow the palm; grasp physics lives in hand/sim.py.
"""
import argparse
import json
import os
import random
import re
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain as brain_mod, motor  # noqa: E402
from hand.brain import OBJECT_WORDS  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

SHOWCASE = ("tidy the table, then stack the block on the can, then give me the ball, then point at the bar, "
            "then push the can toward me, then look at the bar and nod, then juggle the ball, then wave, then box")
TASKS = ["put the ball on the left", "stack the block on the can", "give me the bar", "point at the can",
         "push the ball forward", "tidy the table", "put the can on the right and then wave",
         "pick up the block", "look at the ball and nod", "clap", "box", "put the bar in the middle",
         "give me the ball, then shake your head", "stack the ball on the block", "juggle the ball",
         "pass the can to your other hand", "throw the block and catch it"]
LOCAL_BRAIN = "http://127.0.0.1:8766/v1"


# ------------------------------------------------------------------ phrasings it knows -> program
def _word_obj(w):
    return OBJECT_WORDS.get(w) or (OBJECT_WORDS.get(w[:-1]) if w.endswith("s") else None)


def objs_in(text):
    out = []
    for w in re.findall(r"[a-z]+", text):
        o = _word_obj(w)
        if o and o not in out:
            out.append(o)
    return out


def spot_in(text):
    for k, words in {"left": ("left",), "right": ("right",), "middle": ("middle", "center", "centre"),
                     "front": ("front", "near", "closer")}.items():
        if any(re.search(rf"\b{w}\b", text) for w in words):
            return k
    return None


def plan(command):
    """-> (program, unknown clauses). Clauses split on commas, 'and', 'then'; 'it' = last object named."""
    prog, unknown, last = [], [], None
    for c in [c.strip() for c in re.split(r",|\band then\b|\bthen\b|\band\b", command.lower()) if c.strip()]:
        os_, spot = objs_in(c), spot_in(c)
        if not os_ and last and re.search(r"\b(it|that|this|them)\b", c):
            os_ = [last]
        o = os_[0] if os_ else None
        last = os_[-1] if os_ else last
        if re.search(r"(juggl|toss|throw|catch|\bpass\b|swap|other hand)", c):
            unknown.append(c)                                   # needs thought: leave it to the AI / routines
        elif re.search(r"\b(tidy|clean up|clean the table|organi[sz]e|line up|sort)\b", c):
            prog += [{"do": "place", "obj": x, "at": s} for x, s in
                     zip(("ball", "can", "block", "bar"), ("right", "middle", "left", "front"))]
        elif re.search(r"\b(stack|on top of)\b", c) or (re.search(r"\b(put|place|set)\b", c) and len(os_) == 2):
            if len(os_) == 2:
                prog.append({"do": "place", "obj": os_[0], "on": os_[1]})
            else:
                unknown.append(c)
        elif re.search(r"\b(give|hand|bring)\b", c) and o:
            prog.append({"do": "give", "obj": o})
        elif re.search(r"\b(put|place|set|move|drop)\b", c) and o:
            prog.append({"do": "place", "obj": o, "at": spot or "middle"})
        elif re.search(r"\b(push|slide|nudge)\b", c) and o:
            way = "away" if re.search(r"\b(forward|away|back)\b", c) else (spot if spot in ("left", "right")
                                                                          else "toward")
            prog.append({"do": "push", "obj": o, "dir": way})
        elif re.search(r"\b(point|show)\b", c) and o:
            prog.append({"do": "point", "obj": o})
        elif re.search(r"\b(look|watch|find)\b", c) and o:
            prog.append({"do": "look", "obj": o})
        elif re.search(r"\b(pick|grab|get|take|lift|hold|grasp)\b", c) and o:
            prog.append({"do": "pick", "obj": o})
        elif re.search(r"\b(wave|hello|hi|bye)\b", c):
            prog.append({"do": "wave"})
        elif re.search(r"\b(box|boxing|punch|fight)\b", c):
            prog.append({"do": "box"})
        elif re.search(r"\bclap\b", c):
            prog.append({"do": "clap"})
        elif re.search(r"\b(nod|yes)\b", c):
            prog.append({"do": "nod"})
        elif re.search(r"\b(shake|no)\b", c):
            prog.append({"do": "shake"})
        else:
            unknown.append(c)
    return prog, unknown


# ------------------------------------------------------------------ the AI
def _reachable(url):
    try:
        host, port = re.match(r"https?://([^:/]+):?(\d+)?", url).groups()
        with socket.create_connection((host, int(port or (443 if url.startswith("https") else 80))), timeout=0.5):
            return True
    except (OSError, AttributeError):
        return False


def get_brain():
    url = os.environ.get("BRAIN_URL")
    if url:
        return brain_mod.OpenAIBrain(url=url), url
    if _reachable(LOCAL_BRAIN):
        return brain_mod.OpenAIBrain(url=LOCAL_BRAIN, model="local", timeout=180), LOCAL_BRAIN
    return brain_mod.StubBrain(), None


def think(command, m, brain, say, rounds=2):
    """AI writes a program, the body checks it, the AI repairs it. -> (program, problems, what it said)."""
    doc = motor.__doc__[motor.__doc__.index("Actions"):]
    world = motor.describe_world(motor.Body(m).pos, {"right": None, "left": None})
    reply = brain.program(command, world, doc)
    prog = reply.get("program") or []
    problems = []
    for r in range(rounds + 1):
        problems = motor.Body(m).run(prog).problems if prog else ["the program was empty"]
        say(f"  {'plan' if r == 0 else f'repair {r}'}: {len(prog)} steps"
            + (f", {len(problems)} problem(s): " + "; ".join(problems[:3]) if problems else ", checks out on the body"))
        if not problems or r == rounds or isinstance(brain, brain_mod.StubBrain):
            break
        reply = brain.program(command, world, doc, problems=problems, previous=prog)
        prog = reply.get("program") or prog
    return prog, problems, reply.get("say", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="*")
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--showcase", action="store_true")
    ap.add_argument("--think", action="store_true", help="let the AI write the whole program")
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    command = random.choice(TASKS) if a.random or not a.command else " ".join(a.command)
    if a.showcase:
        command = SHOWCASE
    say = lambda s: print(s, flush=True)
    import mujoco
    m = build_model(extra=motor.scene_xml())
    say(f'task: "{command}"')
    prog, unknown = ([], [command]) if a.think else plan(command)
    said = ""
    if unknown:
        brain, url = get_brain()
        rest = ", ".join(unknown)
        if url:
            say(f"  thinking about \"{rest}\" with the AI brain ({url}) - can take ~30 s on the laptop GPU...")
        else:
            say(f"  AI brain is off (panel: Start AI brain) - using built-in routines for \"{rest}\"")
        t0 = time.time()
        try:
            extra, _, said = think(rest, m, brain, say)
        except (OSError, ValueError, KeyError) as e:        # the brain crashed or timed out: don't die with it
            say(f"  AI brain stopped answering ({type(e).__name__}) - falling back to built-in routines")
            extra, _, said = think(rest, m, brain_mod.StubBrain(), say)
        if url:
            say(f"  thought for {time.time() - t0:.0f} s")
        prog += extra
    for step in prog:
        say("  step: " + json.dumps(step))
    if not prog:
        say("robot: I couldn't work out how to do that with two arms and these four objects (ball, can, block, "
            "bar). No legs or other objects yet.")
        return
    body = motor.Body(m).run(prog)
    words = ([said] if said else []) + body.said
    say("robot: " + ("; ".join(words) or "done.")
        + (f"  (couldn't do: {'; '.join(body.problems[:3])})" if body.problems else ""))
    d = mujoco.MjData(m)
    cam = dict(lookat=(-0.05, -0.28, 1.12), distance=2.0, azimuth=115, elevation=-15)
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
