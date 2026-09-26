"""Record every attempt as a reusable episode, from day 1 (Kimi round 6, candidate a).

    rec = Recorder("logs/episodes")
    ep = rec.start("pick up the ball", "ball", source="real")
    ep.step(t, q_cmd, q_est, image=frame)          # call at the control rate; frames are kept every `every` steps
    ep.end(success=True, family="power", s=0.85, t_thumb=0.9, cause="")

On disk, one folder per episode - plain files, no framework:
    logs/episodes/000123/meta.json     task, object, source, grasp, outcome, fps, joint names
    logs/episodes/000123/steps.npz     t (T,), action = q_cmd (T, 6), state = q_est (T, 6)
    logs/episodes/000123/frames/000045.jpg ...
tools/export_lerobot.py turns the folder into a LeRobot dataset (on a machine where lerobot is installed - it
downgrades torch, so it does not go in this venv). Nothing here needs a GPU.
"""
import json
import os
import time

import numpy as np

from . import config


class Episode:
    def __init__(self, path, meta, every):
        self.path, self.meta, self.every = path, meta, every
        self.t, self.act, self.state = [], [], []
        os.makedirs(os.path.join(path, "frames"), exist_ok=True)

    def step(self, t, q_cmd, q_est, image=None):
        k = len(self.t)
        self.t.append(float(t))
        self.act.append(np.asarray(q_cmd, np.float32))
        self.state.append(np.asarray(q_est, np.float32))
        if image is not None and k % self.every == 0:
            import cv2
            cv2.imwrite(os.path.join(self.path, "frames", f"{k:06d}.jpg"), np.asarray(image)[:, :, ::-1],
                        [cv2.IMWRITE_JPEG_QUALITY, 85])

    def end(self, success, family="", s=None, t_thumb=None, cause=""):
        np.savez_compressed(os.path.join(self.path, "steps.npz"), t=np.array(self.t, np.float64),
                            action=np.array(self.act).reshape(-1, config.N), state=np.array(self.state).reshape(-1, config.N))
        dur = self.t[-1] - self.t[0] if len(self.t) > 1 else 0.0
        self.meta.update({"success": bool(success), "family": family, "s": s, "t_thumb": t_thumb, "cause": cause,
                          "steps": len(self.t), "fps": round((len(self.t) - 1) / dur, 2) if dur else None,
                          "ended": time.strftime("%Y-%m-%dT%H:%M:%S")})
        with open(os.path.join(self.path, "meta.json"), "w") as f:
            json.dump(self.meta, f, indent=1)
        return self.path


class Recorder:
    def __init__(self, root, every=3):
        self.root, self.every = root, every
        os.makedirs(root, exist_ok=True)

    def start(self, task, obj, source="sim"):
        n = len([d for d in os.listdir(self.root) if d.isdigit()])
        path = os.path.join(self.root, f"{n:06d}")
        meta = {"task": task, "object": obj, "source": source, "joints": config.JOINTS,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        return Episode(path, meta, self.every)

    def episodes(self):
        out = []
        for d in sorted(os.listdir(self.root)):
            m = os.path.join(self.root, d, "meta.json")
            if d.isdigit() and os.path.exists(m):
                out.append((os.path.join(self.root, d), json.load(open(m))))
        return out
