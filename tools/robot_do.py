"""Tell the full InMoov what to do; it plans with its skills and does it in the simulator.

    .venv/Scripts/python tools/robot_do.py "put the ball on the left"
    .venv/Scripts/python tools/robot_do.py "stack the block on the can"
    .venv/Scripts/python tools/robot_do.py "give me the bar, then wave"
    .venv/Scripts/python tools/robot_do.py "tidy the table"
    .venv/Scripts/python tools/robot_do.py --random            # makes up a task and does it
    add --video out.mp4 to save instead of opening a window

Skills (all real motions, planned with inverse kinematics on the URDF arm):
    pick X | place X at left/middle/right/front | stack X on Y | give X (hand it to you) | point at X |
    push X left/right/forward | look at X | wave | box | clap | nod | shake (head) | tidy (line everything up)
"left/right" are the ROBOT's left and right (it faces you). Objects: ball, can, block, bar (+ synonyms such as
orange, bottle, cube, pen). Several steps can be chained with "and" / "then".
Simplified on purpose: a held object follows the palm - whether a grasp physically HOLDS is the detailed hand
sim's job (hand/sim.py). The window keeps the last pose until you close it; nothing loops.
"""
import argparse
import os
import random
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import reach  # noqa: E402
from hand.brain import OBJECT_WORDS  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

TABLE_Z = 0.88
SPOTS = {"right": (-0.40, -0.30), "middle": (-0.25, -0.30), "left": (-0.10, -0.30), "front": (-0.25, -0.24)}
START = {"ball": (-0.36, -0.35), "can": (-0.26, -0.35), "block": (-0.16, -0.35), "bar": (-0.08, -0.27)}
OBJ = {  # type, size, rgba, half-height
    "ball": ("sphere", "0.03", "0.85 0.3 0.25 1", 0.03),
    "can": ("cylinder", "0.028 0.045", "0.3 0.55 0.9 1", 0.045),
    "block": ("box", "0.028 0.028 0.028", "0.95 0.8 0.2 1", 0.028),
    "bar": ("capsule", "0.013 0.06", "0.4 0.8 0.4 1", 0.013),
}
FINGERS = ("index", "majeure", "ringFinger", "ringfinger", "pinky", "thumb")
HANDOVER = (-0.25, -0.52, 1.20)
NECK = "head_neck_001"          # nod (pitch)
TURN = "head_rothead"           # look left/right, shake
SHOWCASE = ("tidy the table, then stack the block on the can, then give me the ball, then point at the bar, "
            "then push the can toward me, then look at the bar and nod, then wave, then box")
TASKS = ["put the ball on the left", "stack the block on the can", "give me the bar", "point at the can",
         "push the ball forward", "tidy the table", "put the can on the right and then wave",
         "pick up the block", "look at the ball and nod", "clap", "box", "put the bar in the middle",
         "give me the ball, then shake your head", "stack the ball on the block"]


def scene():
    x0, y0 = SPOTS["middle"]
    body = (f'<body name="table" pos="{x0} {y0 - 0.03} {TABLE_Z / 2}"><geom type="box" '
            f'size="0.26 0.14 {TABLE_Z / 2}" rgba="0.45 0.35 0.28 1"/></body>')
    for name, (typ, size, rgba, h) in OBJ.items():
        x, y = START[name]
        euler = ' euler="0 90 0"' if name == "bar" else ""
        body += (f'<body name="obj_{name}" mocap="true" pos="{x} {y} {TABLE_Z + h}">'
                 f'<geom type="{typ}" size="{size}" rgba="{rgba}"{euler}/></body>')
    return body


# ------------------------------------------------------------------ planning: sentence -> skill steps
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
                     "front": ("front", "near", "closer", "forward")}.items():
        if any(re.search(rf"\b{w}\b", text) for w in words):
            return k
    return None


def plan(command):
    """-> (steps, unknown clauses). Clauses split on commas, 'and', 'then'."""
    steps, unknown = [], []
    clauses = [c.strip() for c in re.split(r",|\band then\b|\bthen\b|\band\b", command.lower()) if c.strip()]
    last = None
    for c in clauses:
        os_, spot = objs_in(c), spot_in(c)
        if not os_ and last and re.search(r"\b(it|that|this|them)\b", c):
            os_ = [last]                                   # "grab the orange and put it on the right"
        o = os_[0] if os_ else None
        last = os_[-1] if os_ else last
        if re.search(r"\b(tidy|clean up|clean the table|organi[sz]e|line up|sort)\b", c):
            steps.append(("tidy",))
        elif re.search(r"\b(stack|on top of)\b", c) or (re.search(r"\b(put|place|set)\b", c) and len(os_) == 2):
            if len(os_) == 2:
                steps.append(("stack", os_[0], os_[1]))
            else:
                unknown.append(c)
        elif re.search(r"\b(give|hand|pass|bring)\b", c) and o:
            steps.append(("give", o))
        elif re.search(r"\b(put|place|set|move|drop)\b", c) and o:
            steps.append(("place", o, spot or "middle"))
        elif re.search(r"\b(push|slide|nudge)\b", c) and o:
            way = "away" if re.search(r"\b(forward|away|back)\b", c) else (spot if spot in ("left", "right") else "toward")
            steps.append(("push", o, way))
        elif re.search(r"\b(point|show)\b", c) and o:
            steps.append(("point", o))
        elif re.search(r"\b(look|watch|find)\b", c) and o:
            steps.append(("look", o))
        elif re.search(r"\b(pick|grab|get|take|lift|hold|grasp)\b", c) and o:
            steps.append(("pick", o))
        elif re.search(r"\b(wave|hello|hi|bye)\b", c):
            steps.append(("wave",))
        elif re.search(r"\b(box|boxing|punch|fight)\b", c):
            steps.append(("box",))
        elif re.search(r"\bclap\b", c):
            steps.append(("clap",))
        elif re.search(r"\b(nod|yes)\b", c):
            steps.append(("nod",))
        elif re.search(r"\b(shake|no)\b", c):
            steps.append(("shake",))
        else:
            unknown.append(c)
    return steps, unknown


# ------------------------------------------------------------------ execution: skills -> keyframes + events
class Robot:
    def __init__(self, m):
        self.m = m
        self.pos = {k: np.array([*START[k], TABLE_Z + OBJ[k][3]]) for k in OBJ}
        self.held = None
        self.frames = []                    # (seconds, {actuator: target}, event or None)
        self.q = {}
        self.say = []

    def _fingers(self, amount=None):
        amount = (0.8 if self.held else 0.0) if amount is None else amount
        out = {}
        for i in range(self.m.nu):
            n = self.m.actuator(i).name
            if n.startswith("rightHand_") and any(f in n for f in FINGERS):
                out[n] = float(self.m.actuator_ctrlrange[i, 1]) * amount
        return out

    def _arm(self, xyz, seconds, extra=None, event=None):
        q, err = reach.solve(self.m, xyz)
        if q is None:
            self.say.append(f"a spot was out of reach by {err * 100:.0f} cm")
            return False
        self.q = q
        self.frames.append((seconds, {**q, **self._fingers(), **(extra or {})}, event))
        return True

    def _pose(self, seconds, joints, event=None):
        self.frames.append((seconds, joints, event))

    def pick(self, o):
        if self.held == o:
            return
        if self.held:
            self.place(self.held, "front")
        p = self.pos[o]
        top = p[2] + OBJ[o][3]
        if not self._arm((p[0], p[1], top + 0.12), 1.4):
            return
        self._arm((p[0], p[1], top + 0.04), 0.8)
        self.frames.append((0.6, {**self.q, **self._fingers(0.8)}, ("attach", o)))
        self.held = o
        self._arm((p[0], p[1], top + 0.14), 0.8)

    def place(self, o, spot, on=None):
        self.pick(o)
        if self.held != o:
            return
        if on:
            x, y = self.pos[on][:2]
            z = self.pos[on][2] + OBJ[on][3] + OBJ[o][3]
        else:
            x, y = SPOTS[spot]
            for k in OBJ:                        # spot taken by something else: shift so they don't overlap
                if k != o and np.linalg.norm(self.pos[k][:2] - (x, y)) < 0.06:
                    x += 0.07 if x < -0.2 else -0.07
            z = TABLE_Z + OBJ[o][3]
        if not self._arm((x, y, z + OBJ[o][3] + 0.14), 1.2):
            return
        self._arm((x, y, z + OBJ[o][3] + 0.04), 0.8)
        self.pos[o] = np.array([x, y, z])
        self.frames.append((0.5, {**self.q, **self._fingers(0.0)}, ("detach", o, (x, y, z))))
        self.held = None
        self._arm((x, y, z + OBJ[o][3] + 0.16), 0.7)

    def give(self, o):
        self.pick(o)
        if self.held != o:
            return
        self._arm(HANDOVER, 1.4)
        self.frames.append((0.6, {**self.q, **self._fingers(0.0)}, ("give", o)))
        self.held = None
        self.pos[o] = np.array([HANDOVER[0], HANDOVER[1] - 0.12, TABLE_Z + 0.35])
        self.say.append(f"here's the {o}")

    def point(self, o):
        p = self.pos[o]
        extra = self._fingers(0.9)
        for n in extra:
            if "index" in n:
                extra[n] = 0.0                                   # index finger stays straight
        self._arm((p[0], p[1] + 0.05, 1.12), 1.2, extra)
        self._pose(0.8, {**self.q, **extra})

    def push(self, o, d):
        p = self.pos[o]
        # robot faces -y: "away" = further from the robot (short - the arm runs out of reach), "toward" = closer
        step = np.array({"left": (0.12, 0, 0), "right": (-0.12, 0, 0), "away": (0, -0.04, 0), "toward": (0, 0.07, 0)}[d])
        back = p - step * np.array([0.5, 0.8, 0])
        self._arm(back + [0, 0, 0.12], 1.2)
        self._arm((back[0], back[1], TABLE_Z + 0.09), 0.7)
        new = p + step
        self._arm((new[0] - step[0] * 0.5, new[1] - step[1] * 0.8, TABLE_Z + 0.09), 1.0, event=("slide", o, tuple(new)))
        self.pos[o] = new
        self._arm((new[0], new[1], p[2] + 0.14), 0.7)

    def look(self, o):
        turn = float(np.clip(-np.arctan2(self.pos[o][0], 0.5), -0.34, 0.34))
        self._pose(1.0, {TURN: turn})

    def gesture(self, g):
        if g == "wave":
            up = {"right_shoulder_x": 2.1, "right_elbow_x": 0.9, "right_shoulder_z": 0.2}
            self._pose(1.0, up)
            for k in range(4):
                self._pose(0.35, {**up, "right_shoulder_z": 0.8 if k % 2 == 0 else -0.35})
        elif g == "box":
            guard = {"right_shoulder_x": 0.25, "right_elbow_x": 1.5, "left_shoulder_x": 0.25, "left_elbow_x": 1.5}
            self._pose(0.7, guard)
            for k in range(4):
                s = "right" if k % 2 == 0 else "left"
                self._pose(0.25, {**guard, f"{s}_shoulder_x": 1.1, f"{s}_elbow_x": 0.1})
                self._pose(0.3, guard)
        elif g == "clap":
            apart = {"right_shoulder_x": 1.2, "left_shoulder_x": 1.2, "right_elbow_x": 0.6, "left_elbow_x": 0.6,
                     "right_shoulder_z": 0.6, "left_shoulder_z": 0.6}
            together = dict(apart, right_shoulder_z=-0.3, left_shoulder_z=-0.3)
            for _ in range(3):
                self._pose(0.35, apart)
                self._pose(0.2, together)
        elif g in ("nod", "shake"):
            j = NECK if g == "nod" else TURN
            for k in range(4):
                self._pose(0.3, {j: 0.3 if k % 2 == 0 else -0.3})
            self._pose(0.3, {j: 0.0})

    def run(self, steps):
        for s in steps:
            kind = s[0]
            if kind == "pick":
                self.pick(s[1])
            elif kind == "place":
                self.place(s[1], s[2])
            elif kind == "stack":
                if s[1] == s[2]:
                    self.say.append("can't stack something on itself")
                else:
                    self.place(s[1], None, on=s[2])
            elif kind == "give":
                self.give(s[1])
            elif kind == "point":
                self.point(s[1])
            elif kind == "push":
                self.push(s[1], s[2])
            elif kind == "look":
                self.look(s[1])
            elif kind == "tidy":
                for o, spot in zip(("ball", "can", "block", "bar"), ("right", "middle", "left", "front")):
                    self.place(o, spot)
            else:
                self.gesture(kind)
        if self.held:
            self.place(self.held, "front")
        self._pose(1.0, {})                       # back to rest


def act_id(m, n):
    try:
        return m.actuator(n).id
    except KeyError:
        return None


def play(m, d, frames, on_frame):
    """Kinematic playback (joint angles set per frame) plus object events: attach / detach / give / slide."""
    import mujoco
    cur = {m.actuator(i).name: 0.0 for i in range(m.nu)}
    adr = {n: m.jnt_qposadr[m.actuator_trnid[act_id(m, n), 0]] for n in cur}
    palm = m.body(reach.PALM).id
    held, off = None, None
    moc = lambda o: m.body(f"obj_{o}").mocapid[0]
    for seconds, goal, ev in frames:
        start = dict(cur)
        target = {n: 0.0 for n in cur} if goal == {} else {**cur, **{k: v for k, v in goal.items() if k in cur}}
        slide_from = d.mocap_pos[moc(ev[1])].copy() if ev and ev[0] == "slide" else None
        steps = max(1, int(seconds / 0.02))
        for k in range(1, steps + 1):
            a = k / steps
            a = a * a * (3 - 2 * a)
            for n in cur:
                cur[n] = start[n] + (target[n] - start[n]) * a
                d.qpos[adr[n]] = cur[n]
            mujoco.mj_forward(m, d)
            if held is not None:
                d.mocap_pos[moc(held)] = d.xpos[palm] + off
            if slide_from is not None:
                d.mocap_pos[moc(ev[1])] = slide_from + (np.array(ev[2]) - slide_from) * a
            mujoco.mj_forward(m, d)
            on_frame()
        if ev and ev[0] == "attach":
            held, off = ev[1], d.mocap_pos[moc(ev[1])] - d.xpos[palm]
        elif ev and ev[0] == "detach":
            d.mocap_pos[moc(ev[1])] = ev[2]
            held = None
        elif ev and ev[0] == "give":
            d.mocap_pos[moc(ev[1])] = (HANDOVER[0], HANDOVER[1] - 0.12, TABLE_Z + 0.35)   # now in your hand
            held = None
        mujoco.mj_forward(m, d)
        on_frame()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="*")
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--showcase", action="store_true", help="run a long chain of tasks in one window")
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    command = random.choice(TASKS) if a.random or not a.command else " ".join(a.command)
    if a.showcase:
        command = SHOWCASE
    import mujoco
    m = build_model(extra=scene())
    steps, unknown = plan(command)
    print(f'task: "{command}"', flush=True)
    for s in steps:
        print("  step:", " ".join(str(x) for x in s), flush=True)
    for u in unknown:
        print(f'  (skipped "{u}" - no skill for that yet)', flush=True)
    if not steps:
        print("robot: I don't have a skill for that yet. Try: put the ball on the left, stack the block on the "
              "can, give me the bar, point at the can, tidy the table, wave, box, clap.")
        return
    rb = Robot(m)
    rb.run(steps)
    print("robot: " + ("; ".join(rb.say) if rb.say else "done."), flush=True)
    d = mujoco.MjData(m)
    cam = dict(lookat=(-0.18, -0.25, 1.12), distance=1.9, azimuth=128, elevation=-18)
    if a.video:
        import cv2
        r = mujoco.Renderer(m, 480, 640)
        c = mujoco.MjvCamera()
        c.lookat[:], c.distance, c.azimuth, c.elevation = cam["lookat"], cam["distance"], cam["azimuth"], cam["elevation"]
        vw = cv2.VideoWriter(a.video, cv2.VideoWriter_fourcc(*"mp4v"), 50, (640, 480))
        play(m, d, rb.frames, lambda: (r.update_scene(d, c), vw.write(r.render()[:, :, ::-1])))
        vw.release()
        print("saved", a.video)
        return
    import mujoco.viewer
    with mujoco.viewer.launch_passive(m, d) as v:
        v.cam.lookat[:] = cam["lookat"]
        v.cam.distance, v.cam.azimuth, v.cam.elevation = cam["distance"], cam["azimuth"], cam["elevation"]
        play(m, d, rb.frames, lambda: (v.sync(), time.sleep(0.02)))
        while v.is_running():
            v.sync()
            time.sleep(0.05)


if __name__ == "__main__":
    main()
