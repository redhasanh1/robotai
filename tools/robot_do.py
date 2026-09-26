"""Type a command, the full InMoov does it in the simulator (the real-looking one when meshes are cached).

    .venv/Scripts/python tools/robot_do.py "pick up the ball"
    .venv/Scripts/python tools/robot_do.py "wave"
    .venv/Scripts/python tools/robot_do.py "box"           (punch, punch)
    .venv/Scripts/python tools/robot_do.py "walk the dog"  (tells you what's missing - no legs yet)
    add --video out.mp4 to save instead of opening a window

What is real here: the brain's plan, the reach (inverse kinematics on the URDF arm, palm lands within ~5 mm),
joint limits. What is simplified: in this full-body scene the object sticks to the palm once the fingers close -
the physics of whether a grasp HOLDS lives in the detailed hand sim (hand/sim.py, tools/demo.py).
The window stays on the last pose until you close it; nothing loops.
"""
import argparse
import os
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import brain, reach  # noqa: E402
from hand.inmoov_sim import build_model  # noqa: E402

TABLE = (-0.25, -0.34, 0.88)        # in front of the right hand, table top height (m)
OBJECTS = {"ball": ('sphere', "0.035", "0.85 0.3 0.25 1", 0.035), "can": ('cylinder', "0.03 0.05", "0.3 0.55 0.9 1", 0.05),
           "block": ('box', "0.03 0.03 0.03", "0.95 0.8 0.2 1", 0.03), "bar": ('capsule', "0.015 0.07", "0.4 0.8 0.4 1", 0.015)}
FINGERS = ("index", "majeure", "ringFinger", "ringfinger", "pinky", "thumb")


def scene(obj):
    x, y, z = TABLE
    geoms = ""
    for i, (name, (typ, size, rgba, h)) in enumerate(OBJECTS.items()):
        ox = x + (i - 1.5) * 0.11 if name != obj else x
        oy = y if name == obj else y - 0.12
        euler = ' euler="90 0 0"' if name == "bar" else ""
        geoms += (f'<body name="obj_{name}" mocap="true" pos="{ox} {oy} {z + h}">'
                  f'<geom type="{typ}" size="{size}" rgba="{rgba}"{euler}/></body>')
    return (f'<body name="table" pos="{x} {y - 0.05} {z / 2}"><geom type="box" size="0.3 0.2 {z / 2}" '
            f'rgba="0.45 0.35 0.28 1"/></body>' + geoms)


def act(m, name):
    try:
        return m.actuator(name).id
    except KeyError:
        return None


def fingers(m, amount):
    out = {}
    for i in range(m.nu):
        n = m.actuator(i).name
        if n.startswith("rightHand_") and any(f in n for f in FINGERS):
            out[n] = float(m.actuator_ctrlrange[i, 1]) * amount
    return out


def keyframes(m, command):
    """-> (list of (seconds, {actuator: target}), what the robot says, object to carry or None)."""
    low = command.lower()
    if re.search(r"\b(wave|hello|hi)\b", low):
        # measured directions: +shoulder_x swings the arm forward/up, +elbow bends the forearm up
        up = {"right_shoulder_x": 2.1, "right_elbow_x": 0.9, "right_shoulder_z": 0.2}
        frames = [(1.2, up)]
        for k in range(4):
            frames.append((0.35, {**up, "right_shoulder_z": 0.8 if k % 2 == 0 else -0.35,
                                  "right_wrist_z": 0.6 if k % 2 == 0 else -0.6}))
        return frames + [(0.8, {})], "Hi!", None
    if re.search(r"\b(box|boxing|punch|fight)\b", low):
        guard = {"right_shoulder_x": 0.25, "right_elbow_x": 1.5, "left_shoulder_x": 0.25, "left_elbow_x": 1.5}
        frames = [(0.8, guard)]
        for k in range(4):
            side = "right" if k % 2 == 0 else "left"
            frames.append((0.25, {**guard, f"{side}_shoulder_x": 1.1, f"{side}_elbow_x": 0.1}))
            frames.append((0.3, guard))
        return frames + [(0.8, {})], "Boxing! (arms only - no footwork without legs)", None
    b = brain.make(os.environ.get("BRAIN", "stub:instant"))
    plan = b.plan(command)
    step = next((s for s in plan["steps"] if s.get("skill") == "grasp" and s.get("sim_object") in OBJECTS), None)
    if step is None:
        return [], plan["say"], None
    obj = step["sim_object"]
    h = OBJECTS[obj][3]
    target = (TABLE[0], TABLE[1], TABLE[2] + h + 0.06)          # palm just above the object
    q, err = reach.solve(m, target)
    if q is None:
        return [], f"The {obj} is out of reach ({err * 100:.0f} cm short).", None
    lift = dict(q, right_elbow_x=min(q["right_elbow_x"] + 0.5, 1.5))
    frames = [(1.8, q), (0.8, {**q, **fingers(m, 0.8)}), (1.2, {**lift, **fingers(m, 0.8)})]
    return frames, f"Picking up the {obj}.", obj


def play(m, d, frames, carry, on_frame):
    """Kinematic playback: joint angles are SET each frame (mj_forward, no dynamics). This view shows what the
    robot does; whether a grasp physically holds is the detailed hand sim's job. First version stepped the
    dynamics and the unmotored/weak waist let the whole robot spin from the arms' reaction torques."""
    import mujoco
    cur = {m.actuator(i).name: 0.0 for i in range(m.nu)}
    adr = {n: m.jnt_qposadr[m.actuator_trnid[act(m, n), 0]] for n in cur}
    palm = m.body(reach.PALM).id
    held_off = None
    for seconds, goal in frames:
        start = dict(cur)
        target = {n: 0.0 for n in cur} if goal == {} else {**cur, **goal}
        steps = max(1, int(seconds / 0.02))
        for k in range(1, steps + 1):
            a = k / steps
            a = a * a * (3 - 2 * a)
            for n in cur:
                cur[n] = start[n] + (target[n] - start[n]) * a
                d.qpos[adr[n]] = cur[n]
            mujoco.mj_forward(m, d)
            if carry and any(v > 0.5 for n, v in cur.items() if n.startswith("rightHand_")):
                mid = m.body(f"obj_{carry}").mocapid[0]
                if held_off is None:
                    held_off = d.mocap_pos[mid] - d.xpos[palm]
                d.mocap_pos[mid] = d.xpos[palm] + held_off          # simplified: object follows the palm
                mujoco.mj_forward(m, d)
            on_frame()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="+")
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    command = " ".join(a.command)
    import mujoco
    m0 = build_model()
    frames, say, carry = keyframes(m0, command)
    print(f'you: "{command}"\nrobot: {say}', flush=True)
    if not frames:
        return
    m = build_model(extra=scene(carry or "ball"))
    d = mujoco.MjData(m)
    cam = dict(lookat=(-0.1, -0.2, 1.35), distance=2.4, azimuth=125, elevation=-12)
    if a.video:
        import cv2
        r = mujoco.Renderer(m, 480, 640)
        c = mujoco.MjvCamera()
        c.lookat[:], c.distance, c.azimuth, c.elevation = cam["lookat"], cam["distance"], cam["azimuth"], cam["elevation"]
        vw = cv2.VideoWriter(a.video, cv2.VideoWriter_fourcc(*"mp4v"), 50, (640, 480))
        play(m, d, frames, carry, lambda: (r.update_scene(d, c), vw.write(r.render()[:, :, ::-1])))
        vw.release()
        print("saved", a.video)
        return
    import mujoco.viewer
    with mujoco.viewer.launch_passive(m, d) as v:
        v.cam.lookat[:] = cam["lookat"]
        v.cam.distance, v.cam.azimuth, v.cam.elevation = cam["distance"], cam["azimuth"], cam["elevation"]
        play(m, d, frames, carry, lambda: (v.sync(), time.sleep(0.02)))
        while v.is_running():
            v.sync()
            time.sleep(0.05)


if __name__ == "__main__":
    main()
