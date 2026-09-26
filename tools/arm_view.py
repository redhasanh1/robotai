"""The whole InMoov upper body in the MuJoCo simulator.

    .venv/Scripts/python tools/arm_view.py            # sliders: open the "Control" panel on the right of the
                                                       # window and drag any joint (shoulder, elbow, wrist, fingers)
    .venv/Scripts/python tools/arm_view.py --demo     # plays one reach -> turn wrist -> close hand, then holds;
                                                       # close the window to end (it does not loop)
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand.inmoov_sim import build_model  # noqa: E402

RIGHT_FINGERS = ("index", "majeure", "ringFinger", "ringfinger", "pinky", "thumb")


def targets(m, t):
    """Joint targets at time t (s): 0-2 raise arm forward, 2-3.5 bend elbow + turn wrist, 3.5-5 close fingers."""
    ease = lambda a, b: float(np.clip((t - a) / (b - a), 0, 1)) ** 2 * (3 - 2 * float(np.clip((t - a) / (b - a), 0, 1)))
    out = {}
    for i in range(m.nu):
        name = m.actuator(i).name
        lo, hi = m.actuator_ctrlrange[i]
        if name == "right_shoulder_x":
            out[name] = lo + (hi - lo) * 0.25 * ease(0, 2)
        elif name == "right_shoulder_y":
            out[name] = hi * 0.3 * ease(0, 2)
        elif name == "right_elbow_x":
            out[name] = hi * 0.7 * ease(2, 3.5)
        elif name == "right_wrist_z":
            out[name] = hi * 0.6 * ease(2, 3.5)
        elif name.startswith("rightHand_") and any(f in name for f in RIGHT_FINGERS):
            out[name] = hi * 0.85 * ease(3.5, 5)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    import mujoco
    import mujoco.viewer
    m = build_model()
    d = mujoco.MjData(m)
    if not a.demo:
        mujoco.viewer.launch(m, d)                # blocking; built-in sliders under Control
        return
    with mujoco.viewer.launch_passive(m, d) as v:
        v.cam.lookat[:] = (0.0, -0.05, 1.3)
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 1.6, 140, -12
        t0 = time.time()
        while v.is_running():
            t = time.time() - t0
            for name, val in targets(m, t).items():
                d.ctrl[m.actuator(name).id] = val
            mujoco.mj_step(m, d)
            v.sync()
            time.sleep(m.opt.timestep)


if __name__ == "__main__":
    main()
