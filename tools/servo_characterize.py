"""Measure each servo's real physics with the webcam (Monday, after servo_bench.py doa + range).

    .venv/Scripts/python tools/servo_characterize.py COM5 1        # channel 1 (index), camera 0
    .venv/Scripts/python tools/servo_characterize.py COM5 1 --cam 1
    .venv/Scripts/python tools/servo_characterize.py fake 1        # practice run, simulated servo + camera

Rig: glue marker id 20 (print it: tools/vision.py markers prints ids 0-4, 10; this script writes
logs/horn_marker.png for id 20) flat on a round horn, centred. Camera looking straight at it, 20-40 cm away,
good light. Horn only - no finger, no tendon (that is the "unloaded" curve; repeat later with the finger on for
the loaded one).

What it does: drives the channel through the excitation signal from hand/sysid.py for ~20 s (big jumps and
small steps, both directions), reads the horn angle from the marker every frame, converts angle -> flexion
units by regressing settled angles on commands, then fits v_max / tau / backlash with hand/sysid.fit and saves
them into hand_calibration.json for that channel. Prints before/after so you can see datasheet vs measured.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import config, protocol, sysid, vision  # noqa: E402
from hand.link import HandLink  # noqa: E402

HORN_ID = 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeCam:
    """Simulated camera looking at the fake servo's horn: angle = shaft position * 120 deg + noise, 30 fps."""

    def __init__(self, link, ch):
        self.link, self.ch, self.rng = link, ch, np.random.default_rng(0)

    def angle(self):
        return float(self.link.fake.plant.p[self.ch] * 120.0 + self.rng.normal(0, 0.8))


class RealCam:
    def __init__(self, index):
        import cv2
        self.cap = vision.open_camera(index)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def angle(self):
        img, self.t_frame, _ = vision.read_stamped(self.cap)     # frame time, not loop time
        return vision.marker_angle(img, HORN_ID) if img is not None else None


def run(port, ch, cam_index, seconds=20.0, dt=0.03, side="right"):
    fake = port in ("", "fake")
    link = HandLink.open(port="" if fake else port, side=side)
    cam = FakeCam(link, ch) if fake else RealCam(cam_index)
    n = int(seconds / dt)
    _, cmds = sysid.excite(n, dt, seed=ch)
    cmd = np.clip(cmds[:, ch], 0.05, 0.95)          # stay inside the calibrated range
    ts, cs, angs = [], [], []
    q = [0.0] * config.N
    link._send(protocol.slew(20000))        # lift the firmware slew limit: measure the SERVO, not our own limiter
    t0 = time.time()
    t0_mono = time.monotonic()
    try:
        for k in range(n):
            q[ch] = float(cmd[k])
            link.move(q)
            if fake:
                link.tick(dt)
                t = k * dt
            else:
                link.tick(0)
                while time.time() - t0 < (k + 1) * dt:
                    time.sleep(0.001)
                t = time.time() - t0
            a = cam.angle()
            if a is not None:
                ts.append(t if fake else cam.t_frame - t0_mono)
                cs.append(cmd[k])
                angs.append(a)
            if k % 100 == 0:
                print(f"\r  {k * dt:5.1f}/{seconds:.0f} s  marker seen {len(angs)}/{k + 1}", end="", flush=True)
    finally:
        link.estop()
        link._send(protocol.slew(1500))
    print()
    ts, cs, angs = np.array(ts), np.array(cs), np.unwrap(np.radians(angs)) * 180 / np.pi
    if len(ts) < 100:
        print("marker seen too rarely - check light, focus and that it is marker id 20")
        return None
    # angle -> flexion units: regress angle on command over settled samples
    v = np.gradient(angs, ts)
    settled = np.abs(v) < 15
    A = np.c_[cs[settled], np.ones(settled.sum())]
    slope, off = np.linalg.lstsq(A, angs[settled], rcond=None)[0]
    qm = (angs - off) / slope
    fit = sysid.fit(ts, cs, qm)
    return {"deg_per_unit": round(float(slope), 2), **(fit or {})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("channel", type=int)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--side", default="right", choices=("right", "left"))
    a = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    import cv2
    cv2.imwrite(os.path.join(ROOT, "logs", "horn_marker.png"), vision.marker_image(HORN_ID, 400))
    cfg = config.load(side=a.side)
    s = cfg.servos[a.channel]
    print(f"channel {a.channel} ({s.name}) datasheet: v_max {s.v_max}  tau {s.tau}  backlash {s.backlash}")
    r = run(a.port, a.channel, a.cam, a.seconds, side=a.side)
    if not r or "v_max" not in r:
        print("no fit")
        return
    print(f"measured: v_max {r['v_max']}  tau {r['tau']}  backlash {r['backlash']}  (fit rmse {r['rmse']}, "
          f"{r['deg_per_unit']} deg of horn per flexion unit)")
    if a.port not in ("", "fake"):
        s.v_max, s.tau, s.backlash = r["v_max"], r["tau"], r["backlash"]
        cfg.save()
        with open(os.path.join(ROOT, "logs", "servo_curves.jsonl"), "a") as f:
            f.write(json.dumps({"t": time.time(), "channel": a.channel, **r}) + "\n")
        print(f"saved to {config.cal_path(a.side)} (history in logs/servo_curves.jsonl for the drift plot)")


if __name__ == "__main__":
    main()
