"""Download the InMoov URDF's 290 Collada meshes (Sentience Robotics, GPL-3.0) and convert them to STL for
MuJoCo. Cached in logs/inmoov_meshes/ - not committed (license + size). Safe to re-run: skips what exists.

    .venv/Scripts/python tools/fetch_inmoov_meshes.py          # ~2 min, 8 downloads at a time
Then tools/arm_view.py shows the real printed shapes instead of the stick skeleton.
"""
import io
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand.inmoov_sim import MESH_DIR, URDF, mesh_file  # noqa: E402


def fetch(url):
    out = mesh_file(url)
    if os.path.exists(out):
        return "cached"
    import trimesh
    data = urllib.request.urlopen(url, timeout=60).read()
    m = trimesh.load(io.BytesIO(data), file_type="dae", force="mesh")
    if m.is_empty or len(m.faces) == 0:
        open(out + ".empty", "w").close()
        return "empty"
    m.export(out)
    return "ok"


def main():
    os.makedirs(MESH_DIR, exist_ok=True)
    urls = sorted(set(re.findall(r'filename="(https://[^"]+\.dae)"', open(URDF).read())))
    done = {"ok": 0, "cached": 0, "empty": 0, "fail": 0}
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(fetch, u): u for u in urls}
        for i, f in enumerate(futs):
            try:
                done[f.result()] += 1
            except Exception as e:
                done["fail"] += 1
                print("fail", futs[f][-40:], e)
            if i % 25 == 0:
                print(f"{i}/{len(urls)} {done}", flush=True)
    print("done", done)


if __name__ == "__main__":
    main()
