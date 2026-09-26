import numpy as np

from hand import vision


def scene(tip_offsets, palm=(150, 650), size=40):
    """White canvas with the palm marker and finger markers at given offsets (px) from the palm."""
    img = np.full((720, 960), 255, np.uint8)

    def put(mid, cx, cy):
        m = vision.marker_image(mid, size)
        pad = np.full((size + 16, size + 16), 255, np.uint8)
        pad[8:-8, 8:-8] = m
        y, x = int(cy - pad.shape[0] / 2), int(cx - pad.shape[1] / 2)
        img[y:y + pad.shape[0], x:x + pad.shape[1]] = pad

    put(vision.PALM_ID, *palm)
    for k, off in enumerate(tip_offsets):
        if off is not None:
            put(vision.FINGER_IDS[k], palm[0] + off, 70 + 110 * k)
    return img


def test_detects_all_markers():
    seen = vision.detect(scene([200, 220, 240, 220, 200]))
    assert set(seen) == {0, 1, 2, 3, 4, 10}


def test_flexion_calibration_and_occlusion():
    tr = vision.FingerTracker()
    tr.calibrate("open", scene([300, 300, 300, 300, 300]))
    tr.calibrate("closed", scene([100, 100, 100, 100, 100]))
    f = tr.flexion(scene([200, 300, 100, None, 250]))
    assert abs(f[1]) < 0.05 and abs(f[2] - 1) < 0.05
    assert 0.2 < f[0] < 0.8 and 0.05 < f[4] < 0.5
    assert np.isnan(f[3])                       # hidden finger -> NaN for the estimator
