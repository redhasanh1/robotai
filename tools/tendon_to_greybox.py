"""Does the fast grey-box plant (hand/plant.py) capture a tendon-driven finger? Fit it on the tendon model.

    .venv/Scripts/python tools/tendon_to_greybox.py

The tendon-level finger (hand/tendon_sim.py) stands in for the real one: the servo shaft follows the command
through the plant's own rate/lag model, the horn winds the lines, the finger does whatever the strings make it do.
We record 20 s of excitation (hand/sysid.excite), then:
  1. RMSE of the datasheet plant vs the tendon finger
  2. sysid.fit on the recording -> RMSE of the fitted plant on NEW commands
The gap between 1 and 2 is what calibration buys; what is left in 2 is what the learned residual has to cover.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hand import sysid, tendon_sim as T  # noqa: E402
from hand.config import HandConfig  # noqa: E402
from hand.plant import ServoPlant  # noqa: E402

DT = 0.01
HORN_FULL = 2.3          # rad of horn at flexion command 1.0 (results/tendon.md: 90% closure, below stall)


def tendon_run(cmd, finger=None):
    """cmd: (T,) flexion command 0..1 -> finger flexion (T,) from the tendon model."""
    import mujoco
    f = finger or T.Finger()
    m = mujoco.MjModel.from_xml_string(T.build_xml(f))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    fl, ex = m.tendon("flexor").id, m.tendon("extensor").id
    Lf0, Le0 = float(d.ten_length[fl]), float(d.ten_length[ex])
    shaft = ServoPlant(HandConfig().servos[1:2])          # the servo itself (index channel), no tendon slack
    shaft.b[:] = 0.0
    sub = int(round(DT / m.opt.timestep))
    out = []
    for c in cmd:
        shaft.step([c], DT)
        th = float(shaft.p[0]) * HORN_FULL
        m.tendon_range[fl] = (0, Lf0 + f.slack - T.HORN_R * th)
        m.tendon_range[ex] = (0, Le0 + f.slack + T.HORN_R * th)
        for _ in range(sub):
            mujoco.mj_step(m, d)
        out.append(float(d.qpos[:3].sum() / (1.6 + 1.7 + 1.5)) / 0.936)     # normalised to the finger's 94% max
    return np.array(out)


def plant_run(cmd, servo):
    p = ServoPlant([servo])
    return np.array([p.step([c], DT)[0] for c in cmd])


def main():
    t, train = sysid.excite(2000, DT, seed=11, n_joints=1)
    _, test = sysid.excite(1500, DT, seed=12, n_joints=1)
    train, test = np.clip(train[:, 0], 0, 1), np.clip(test[:, 0], 0, 1)
    q_train, q_test = tendon_run(train), tendon_run(test)
    sheet = HandConfig().servos[1]
    rm = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    e_sheet = rm(plant_run(test, sheet), q_test)
    f = sysid.fit(t, train, q_train)
    fitted = HandConfig().servos[1]
    fitted.v_max, fitted.tau, fitted.backlash = f["v_max"], f["tau"], f["backlash"]
    e_fit = rm(plant_run(test, fitted), q_test)
    print(f"datasheet plant vs tendon finger (new commands): RMSE {e_sheet:.4f} (~{e_sheet * 90:.1f} deg)")
    print(f"fitted params: v_max {f['v_max']}  tau {f['tau']}  backlash {f['backlash']}")
    print(f"fitted plant vs tendon finger (new commands):    RMSE {e_fit:.4f} (~{e_fit * 90:.1f} deg)")
    # 3. the learned residual (hand/estimator.py Residual) on top of the fitted plant: open-loop features -> offset
    from hand.estimator import Residual
    def feats(cmd):
        p = ServoPlant([fitted])
        X, qs = [], []
        for c in cmd:
            p.step([c], DT)
            X.append(Residual.features(p.q, p.p, np.array([c])))
            qs.append(p.q[0])
        return np.concatenate(X), np.array(qs)
    Xtr, qtr = feats(train)
    res = Residual()
    res.fit(Xtr, q_train - qtr, epochs=300)
    Xte, qte = feats(test)
    off, _ = res(Xte)
    e_res = rm(qte + off, q_test)
    print(f"fitted plant + learned residual (new commands):  RMSE {e_res:.4f} (~{e_res * 90:.1f} deg)")
    return e_sheet, e_fit, e_res, f


if __name__ == "__main__":
    main()
