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
    """ServoPlant plus effects the model does not contain. `kind` picks WHICH unmodelled physics:
    "bend"  the development case (the estimator was built while looking at this one)
    "quad", "stick", "asym"  HELD OUT - never looked at while designing the estimator (Kimi round 4: test
    against physics we did not tune on, not against our own assumptions)."""

    def __init__(self, servos, kind="bend"):
        super().__init__(servos)
        self.kind = kind
        self.v_nom = self.v_max.copy()
        self.db_nom = self.db.copy()

    def step(self, p_cmd, dt, load=0.0, stop=None):
        qc = np.clip(self.q, 0, 1)
        if self.kind == "bend":
            self.v_max = self.v_nom * (1 - 0.35 * qc)                              # stiffer as it closes
        elif self.kind == "stick":
            self.db = self.db_nom + 0.04                                          # stiction: needs a bigger push
        elif self.kind == "asym":
            opening = np.asarray(p_cmd) < self.p
            self.v_max = np.where(opening, self.v_nom * 1.5, self.v_nom * 0.7)    # return spring helps opening
        q = super().step(p_cmd, dt, load, stop)
        if self.kind == "bend":
            out = q + 0.08 * np.sin(np.pi * np.clip(q, 0, 1))                     # tendon routing
        elif self.kind == "quad":
            out = np.clip(q, 0, 1) ** 1.6                                         # pulley radius changes
        else:
            out = q.copy()
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


def main(seed=3, kind="bend", quiet=False):
    rng = np.random.default_rng(seed)
    truth_servos = real_servos(seed)

    # calibration session (Monday bench: marker disk, good light, 20 s of excitation)
    t, cal_cmd = sysid.excite(2000, DT, seed=seed + 1)
    real = RealHand(truth_servos, kind)
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
    real = RealHand(truth_servos, kind)
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
    if not quiet:
        print(f"[{kind}] camera sees {np.mean(~np.isnan(z[:, :5])):.0%} of finger samples")
        for name, e in rows:
            print(f"  {name:38s} RMSE {e:.4f}  (~{e * 90:.1f} deg of finger)")
    return rows


if __name__ == "__main__":
    table = {}
    for kind in ("bend", "quad", "stick", "asym"):
        errs = np.array([[e for _, e in main(seed, kind, quiet=True)] for seed in (3, 4, 5)])
        table[kind] = errs.mean(0)
    names = ["camera only", "physics only", "+camera", "+sysid", "+residual"]
    print("finger error in degrees, mean of 3 seeds (bend = development case, others HELD OUT)")
    print(f"{'unmodelled physics':20s}" + "".join(f"{n:>14s}" for n in names))
    for kind, e in table.items():
        print(f"{kind + (' (dev)' if kind == 'bend' else ' (held out)'):20s}" + "".join(f"{v * 90:14.1f}" for v in e))
