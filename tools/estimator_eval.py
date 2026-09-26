"""Graph 5: does the physics-informed estimator beat the camera alone and the physics alone?

    .venv/Scripts/python tools/estimator_eval.py

A "real" hand whose servos differ from the datasheet AND that has effects the grey-box model does not contain
(nonlinear tendon routing, friction that grows as the finger closes) follows an excitation signal. The camera
sees fingers 1 frame in 3, with 3% noise, hidden about half the time in bursts. Flexion RMSE of:
  camera only (hold last) | physics only (datasheet) | physics + camera (datasheet) |
  physics + camera (sysid-fitted) | + learned residual (fitted on the same 20 s calibration run)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import sysid  # noqa: E402
from hand.config import HandConfig  # noqa: E402
from hand.estimator import Estimator, Residual, vision_stream  # noqa: E402
from hand.plant import ServoPlant  # noqa: E402

DT = 0.01


class RealHand(ServoPlant):
    """ServoPlant plus two things the model does not know about."""

    def __init__(self, servos, bend=0.08, drag=0.35):
        super().__init__(servos)
        self.bend, self.drag = bend, drag
        self.v_nom = self.v_max.copy()

    def step(self, p_cmd, dt, load=0.0, stop=None):
        self.v_max = self.v_nom * (1 - self.drag * np.clip(self.q, 0, 1))      # stiffer as the finger closes
        q = super().step(p_cmd, dt, load, stop)
        out = q + self.bend * np.sin(np.pi * np.clip(q, 0, 1))                  # tendon routing nonlinearity
        out[5] = q[5]
        return np.clip(out, self.lo, 1)


def real_servos(seed):
    rng = np.random.default_rng(seed)
    servos = HandConfig().servos
    for s in servos:
        s.v_max *= rng.uniform(0.6, 1.2)
        s.tau *= rng.uniform(0.8, 2.0)
        s.backlash = rng.uniform(0.02, 0.08)
    return servos


def track(servos_model, cmd, z, residual=None, fuse=True):
    est = Estimator(servos_model, residual)
    out = []
    for k, c in enumerate(cmd):
        est.predict(c, DT)
        if fuse:
            est.update(z[k])
        out.append(est.q)
    return np.array(out)


def rmse(a, b):
    return float(np.sqrt(np.mean((a[:, :5] - b[:, :5]) ** 2)))


def main(seed=3):
    rng = np.random.default_rng(seed)
    truth_servos = real_servos(seed)

    # calibration session (Monday bench: marker disk, good light, 20 s of excitation)
    t, cal_cmd = sysid.excite(2000, DT, seed=seed + 1)
    real = RealHand(truth_servos)
    cal = np.array([real.step(c, DT) for c in cal_cmd]) + rng.normal(0, 0.01, (len(cal_cmd), 6))
    fitted = HandConfig().servos
    for j, s in enumerate(fitted):
        f = sysid.fit(t, cal_cmd[:, j], cal[:, j])
        if f:
            s.v_max, s.tau, s.backlash = f["v_max"], f["tau"], f["backlash"]
    model = ServoPlant(fitted)
    X, y = [], []
    for k, c in enumerate(cal_cmd):
        model.step(c, DT)
        X.append(Residual.features(model.q, model.p, c))
        y.append(cal[k] - model.q)
    res = Residual()
    res.fit(np.concatenate(X), np.concatenate(y), epochs=300)

    # test: new commands, occluded camera
    _, cmd = sysid.excite(3000, DT, seed=seed + 2)
    real = RealHand(truth_servos)
    qt = np.array([real.step(c, DT) for c in cmd])
    z = vision_stream(qt, rng)
    held = z.copy()
    for k in range(1, len(held)):
        held[k] = np.where(np.isnan(held[k]), held[k - 1], held[k])
    rows = [("camera only (hold last seen)", rmse(qt, np.nan_to_num(held))),
            ("physics only, datasheet params", rmse(qt, track(HandConfig().servos, cmd, z, fuse=False))),
            ("physics + camera, datasheet params", rmse(qt, track(HandConfig().servos, cmd, z))),
            ("physics + camera, sysid params", rmse(qt, track(fitted, cmd, z))),
            ("physics + camera, sysid + residual", rmse(qt, track(fitted, cmd, z, residual=res)))]
    print(f"camera sees {np.mean(~np.isnan(z[:, :5])):.0%} of finger samples")
    for name, e in rows:
        print(f"{name:38s} RMSE {e:.4f}  (~{e * 90:.1f} deg of finger)")
    return rows


if __name__ == "__main__":
    main()
