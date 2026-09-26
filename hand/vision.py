"""Fingertip tracking from any webcam, no training: printed ArUco markers.

    marker id 0..4 -> thumb, index, middle, ring, pinky fingertips (10 mm squares, tools/vision.py markers)
    marker id 10   -> back of the palm (the reference)

Flexion per finger = how far its tip marker has moved from the "open" distance toward the "closed" distance,
relative to the palm marker, in units of the palm marker's own size (so it works at any camera distance).
Two snapshots calibrate it: hand fully open, hand fully closed. A marker that is not seen gives NaN - exactly
what the estimator expects during occlusion.
"""
import json
import os

import numpy as np

FINGER_IDS = [0, 1, 2, 3, 4]
PALM_ID = 10
DICT = "DICT_4X4_50"


def _aruco():
    import cv2
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
    p = cv2.aruco.DetectorParameters()
    return cv2, cv2.aruco.ArucoDetector(d, p), d


def marker_image(marker_id, px=200):
    cv2, _, d = _aruco()
    return cv2.aruco.generateImageMarker(d, marker_id, px)


def marker_sheet(path, mm=10, dpi=300):
    """Printable A4 sheet with every marker at `mm` size, 3 copies each (spares). Print at 100% scale."""
    cv2, _, _ = _aruco()
    px = int(mm / 25.4 * dpi)
    page = np.full((int(297 / 25.4 * dpi), int(210 / 25.4 * dpi)), 255, np.uint8)
    ids = FINGER_IDS + [PALM_ID]
    x0, y0, gap = 120, 160, px + 90
    for r, mid in enumerate(ids):
        for c in range(3):
            y, x = y0 + r * gap, x0 + c * gap
            page[y:y + px, x:x + px] = marker_image(mid, px)
        label = ["thumb", "index", "middle", "ring", "pinky", "palm"][r]
        cv2.putText(page, f"id {mid} {label}", (x0 + 3 * gap, y0 + r * gap + px // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, 0, 2)
    cv2.putText(page, f"PINN Humanoid fingertip markers - print at 100%, each square {mm} mm", (x0, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, 0, 2)
    cv2.imwrite(path, page)
    return path


def detect(img):
    """-> {id: (center_xy, side_px)} for every marker seen."""
    cv2, det, _ = _aruco()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    corners, ids, _ = det.detectMarkers(gray)
    out = {}
    if ids is not None:
        for c, i in zip(corners, ids.ravel()):
            pts = c.reshape(4, 2)
            side = float(np.mean(np.linalg.norm(pts - np.roll(pts, 1, 0), axis=1)))
            out[int(i)] = (pts.mean(0), side)
    return out


class FingerTracker:
    """Marker detections -> flexion 0..1 per finger (NaN when unseen)."""

    def __init__(self, cal_path=None):
        self.open_d = np.full(5, np.nan)
        self.closed_d = np.full(5, np.nan)
        self.cal_path = cal_path
        if cal_path and os.path.exists(cal_path):
            d = json.load(open(cal_path))
            self.open_d, self.closed_d = np.array(d["open"], float), np.array(d["closed"], float)

    @staticmethod
    def distances(seen):
        """Tip-to-palm distance per finger in palm-marker sizes (scale-free)."""
        d = np.full(5, np.nan)
        if PALM_ID not in seen:
            return d
        pc, ps = seen[PALM_ID]
        for k, mid in enumerate(FINGER_IDS):
            if mid in seen:
                d[k] = np.linalg.norm(seen[mid][0] - pc) / ps
        return d

    def calibrate(self, which, img):
        d = self.distances(detect(img))
        if which == "open":
            self.open_d = np.where(np.isnan(d), self.open_d, d)
        else:
            self.closed_d = np.where(np.isnan(d), self.closed_d, d)
        if self.cal_path:
            json.dump({"open": self.open_d.tolist(), "closed": self.closed_d.tolist()}, open(self.cal_path, "w"))
        return d

    def flexion(self, img):
        d = self.distances(detect(img))
        f = (self.open_d - d) / (self.open_d - self.closed_d)
        return np.clip(f, -0.1, 1.1)          # NaN stays NaN (unseen or uncalibrated)


def marker_angle(img, marker_id):
    """Rotation of one marker in the image plane, degrees (for the servo-horn disk). None if not seen."""
    cv2, det, _ = _aruco()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    corners, ids, _ = det.detectMarkers(gray)
    if ids is None:
        return None
    for c, i in zip(corners, ids.ravel()):
        if int(i) == marker_id:
            p = c.reshape(4, 2)
            v = p[1] - p[0]
            return float(np.degrees(np.arctan2(v[1], v[0])))
    return None
