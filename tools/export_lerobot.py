"""Turn recorded episodes (hand/recorder.py -> logs/episodes/) into a LeRobot dataset, for post-training
GR00T / SmolVLA / ACT later on a rented GPU (Kimi round 6: record from day 1, train when there's an arm).

LeRobot pins an older CPU torch, so it lives in its own venv - never in .venv:
    python -m uv venv --python 3.12 .venv-lerobot
    python -m uv pip install --python .venv-lerobot/Scripts/python.exe "lerobot[dataset]"   # brings opencv-python-headless;
                                                    # adding opencv-python too breaks cv2 (circular import)
    .venv-lerobot/Scripts/python tools/export_lerobot.py                       # -> logs/lerobot/pinn_hand
    .venv-lerobot/Scripts/python tools/export_lerobot.py --only-success        # train on successes only

Per frame: observation.state (6 finger/wrist flexions), action (6 commanded), observation.images.front (camera,
repeated between saved frames), task (the sentence). --only-success follows Kimi's warning about training on
your own failures amplifying them.
"""
import argparse
import json
import os
import shutil

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOINTS = ["thumb", "index", "middle", "ring", "pinky", "wrist"]


def load(ep_dir):
    meta = json.load(open(os.path.join(ep_dir, "meta.json")))
    d = np.load(os.path.join(ep_dir, "steps.npz"))
    fdir = os.path.join(ep_dir, "frames")
    frames = {int(f[:-4]): os.path.join(fdir, f) for f in os.listdir(fdir)} if os.path.isdir(fdir) else {}
    return meta, d, frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "logs", "episodes"))
    ap.add_argument("--out", default=os.path.join(ROOT, "logs", "lerobot", "pinn_hand"))
    ap.add_argument("--fps", type=int, default=50)
    ap.add_argument("--size", type=int, nargs=2, default=(240, 320), metavar=("H", "W"))
    ap.add_argument("--only-success", action="store_true")
    a = ap.parse_args()
    import cv2
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    h, w = a.size
    features = {
        "observation.state": {"dtype": "float32", "shape": (6,), "names": JOINTS},
        "action": {"dtype": "float32", "shape": (6,), "names": JOINTS},
        "observation.images.front": {"dtype": "image", "shape": (h, w, 3), "names": ["height", "width", "channels"]},
    }
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    ds = LeRobotDataset.create(repo_id="pinn/pinn_hand", fps=a.fps, features=features, root=a.out,
                               robot_type="inmoov_hand", use_videos=False)
    eps = sorted(e for e in os.listdir(a.src) if e.isdigit())
    kept = 0
    for e in eps:
        meta, d, frames = load(os.path.join(a.src, e))
        if a.only_success and not meta.get("success"):
            continue
        img = np.zeros((h, w, 3), np.uint8)
        for k in range(len(d["t"])):
            if k in frames:
                img = cv2.resize(cv2.imread(frames[k])[:, :, ::-1], (w, h))
            ds.add_frame({"observation.state": d["state"][k].astype(np.float32),
                          "action": d["action"][k].astype(np.float32),
                          "observation.images.front": img, "task": meta["task"]})
        ds.save_episode()
        kept += 1
    if hasattr(ds, "finalize"):
        ds.finalize()
    print(f"exported {kept}/{len(eps)} episodes, {ds.num_frames} frames -> {a.out}")


if __name__ == "__main__":
    main()
