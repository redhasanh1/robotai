"""Webcam fingertip tracking.

    .venv/Scripts/python tools/vision.py markers              # writes logs/markers_a4.png - print it at 100%
    .venv/Scripts/python tools/vision.py live [camera_index]  # live view: boxes on markers, flexion per finger
                                                               # keys: o = calibrate OPEN, c = calibrate CLOSED, q = quit
Works with the laptop camera (index 0) or a phone used as a webcam. Glue a 10 mm marker on each fingertip
(ids 0-4 = thumb..pinky) and one on the back of the palm (id 10).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import vision  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def live(cam=0):
    import cv2
    import numpy as np
    cap = vision.open_camera(cam)
    tr = vision.FingerTracker(os.path.join(ROOT, "vision_calibration.json"))
    names = ["thumb", "index", "middle", "ring", "pinky"]
    while True:
        ok, img = cap.read()
        if not ok:
            print("camera not readable - try another index: tools/vision.py live 1")
            break
        seen = vision.detect(img)
        for mid, (c, s) in seen.items():
            cv2.circle(img, tuple(int(v) for v in c), int(s / 2), (0, 255, 0), 2)
            cv2.putText(img, str(mid), tuple(int(v) for v in c), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        f = tr.flexion(img)
        for k, n in enumerate(names):
            txt = f"{n:6s} {'--' if np.isnan(f[k]) else f'{f[k]:.2f}'}"
            cv2.putText(img, txt, (10, 25 + 22 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("PINN hand vision (o=open c=closed q=quit)", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k in (ord("o"), ord("c")):
            print("calibrated", "open" if k == ord("o") else "closed", tr.calibrate("open" if k == ord("o") else "closed", img))
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "markers":
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        print("wrote", vision.marker_sheet(os.path.join(ROOT, "logs", "markers_a4.png")))
    elif cmd == "live":
        live(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    else:
        print(__doc__)
