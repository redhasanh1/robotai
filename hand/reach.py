"""Reach skill for the full InMoov body: move the right arm so the palm arrives at a 3D point.

Damped least-squares inverse kinematics on the 5 right-arm joints (shoulder y/x/z, elbow, wrist rotation) using
MuJoCo's own Jacobian, clamped to the URDF joint limits. No training - the same "physics/geometry does the
numbers, the brain picks the goal" split as the grasp loop.

    q = solve(model, target_xyz)          # joint angles (dict), or None if the point is out of reach
    traj = trajectory(model, q, seconds)  # smooth joint targets to play on the actuators
"""
import numpy as np

ARM = ("right_shoulder_y", "right_shoulder_x", "right_shoulder_z", "right_elbow_x", "right_wrist_z")
PALM = "rightHand_majeure"             # base of the middle finger ~ centre of the palm


def arm(side="right"):
    return tuple(n.replace("right_", f"{side}_") for n in ARM)


def palm(side="right"):
    return PALM.replace("right", side)


def solve(m, target, iters=300, damping=0.05, tol=0.01, seed_q=None, side="right", base=None):
    """base=(x, y, yaw) of the wheeled base when the model is mobile; target is in world coordinates."""
    import mujoco
    d = mujoco.MjData(m)
    names = arm(side)
    jid = [m.joint(n).id for n in names]
    adr = [m.jnt_qposadr[j] for j in jid]
    dof = [m.jnt_dofadr[j] for j in jid]
    lo, hi = m.jnt_range[jid, 0], m.jnt_range[jid, 1]
    if seed_q is not None:
        d.qpos[adr] = seed_q
    if base is not None:
        for n, v in zip(("base_x", "base_y", "base_yaw"), base):
            d.qpos[m.jnt_qposadr[m.joint(n).id]] = v
    body = m.body(palm(side)).id
    target = np.asarray(target, float)
    jacp = np.zeros((3, m.nv))
    err = None
    for _ in range(iters):
        mujoco.mj_forward(m, d)
        err = target - d.xpos[body]
        if np.linalg.norm(err) < tol:
            break
        mujoco.mj_jacBody(m, d, jacp, None, body)
        J = jacp[:, dof]
        dq = J.T @ np.linalg.solve(J @ J.T + damping ** 2 * np.eye(3), err)
        d.qpos[adr] = np.clip(d.qpos[adr] + np.clip(dq, -0.2, 0.2), lo, hi)
    ok = np.linalg.norm(err) < 3 * tol
    return ({n: float(d.qpos[a]) for n, a in zip(names, adr)} if ok else None), float(np.linalg.norm(err))


TIPS = ("Hand_thumb3", "Hand_index3", "Hand_majeure3")      # where the closed fingers meet = the grasp point


def wrist_flex(side="right"):
    return f"{side}Hand_wrist_001"


def grasp_frame(m, d, side):
    """(grasp point, approach axis) for the pose in d. The InMoov's closed fingertips curl back up into a fist, so
    the object is held BETWEEN the palm and the curled fingers: the grasp point is halfway from the palm to where the
    closed fingertips meet. Approach axis: wrist -> palm."""
    tips = np.mean([d.xpos[m.body(side + t).id] for t in TIPS], axis=0)
    p = d.xpos[m.body(palm(side)).id]
    h = p - d.xpos[m.body(wrist_flex(side)).id]
    return 0.5 * (p + tips), h / (np.linalg.norm(h) + 1e-9)


def solve_grasp(m, target, approach, side="right", base=None, closed=None, iters=120, w=0.08, seed_q=None,
                accept=(0.012, 0.35)):
    """Put the GRASP POINT (where the closed fingers meet) on target, hand pointing along approach.

    The palm-only solve() left the fingers wherever they fell: closed fingertips ended 12-19 cm above every object.
    Here 6 joints (5 arm + the wrist bend) solve 6 equations: grasp point position (3) + hand axis = approach (3,
    weighted w metres per unit). Finite-difference Jacobian: MuJoCo has no Jacobian for a tip centroid, and 6 extra
    forwards per step is cheap. closed = {finger joint: angle} of the closed hand (the grasp point depends on it).
    -> (q dict incl. the wrist bend, position error m, axis error rad), q None if not reached."""
    import mujoco
    d = mujoco.MjData(m)
    names = list(arm(side)) + [wrist_flex(side)]
    jid = [m.joint(n).id for n in names]
    adr = [m.jnt_qposadr[j] for j in jid]
    lo, hi = m.jnt_range[jid, 0], m.jnt_range[jid, 1]
    if base is not None:
        for n, v in zip(("base_x", "base_y", "base_yaw"), base):
            d.qpos[m.jnt_qposadr[m.joint(n).id]] = v
    for n, v in (closed or {}).items():
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
        if j >= 0:
            d.qpos[m.jnt_qposadr[j]] = v
    if seed_q is not None:
        for n, a in zip(names, adr):
            d.qpos[a] = seed_q.get(n, d.qpos[a])
    target, approach = np.asarray(target, float), np.asarray(approach, float) / np.linalg.norm(approach)

    def resid():
        mujoco.mj_forward(m, d)
        g, h = grasp_frame(m, d, side)
        return np.concatenate([target - g, w * (approach - h)])

    r = resid()
    best, stall = np.inf, 0
    for _ in range(iters):
        if np.linalg.norm(r[:3]) < 0.004 and np.linalg.norm(r[3:]) / w < 0.1:
            break
        e = float(np.linalg.norm(r))
        best, stall = (e, 0) if e < best - 1e-4 else (best, stall + 1)
        if stall > 12:                                     # stuck (joint limit / out of reach): stop early
            break
        J = np.zeros((6, len(adr)))
        q0 = d.qpos[adr].copy()
        for k, a in enumerate(adr):
            d.qpos[a] = q0[k] + 1e-4
            J[:, k] = (r - resid()) / 1e-4                 # d(target - f)/dq = -df/dq, so dq = pinv(J) r
            d.qpos[a] = q0[k]
        dq = J.T @ np.linalg.solve(J @ J.T + 0.02 ** 2 * np.eye(6), r)
        d.qpos[adr] = np.clip(q0 + np.clip(dq, -0.2, 0.2), lo, hi)
        r = resid()
    pos_err, ang_err = float(np.linalg.norm(r[:3])), float(np.linalg.norm(r[3:]) / w)
    q = {n: float(d.qpos[a]) for n, a in zip(names, adr)}
    return (q if pos_err < accept[0] and ang_err < accept[1] else None), pos_err, ang_err


def trajectory(q_goal, seconds=2.0, dt=0.02, q_start=None):
    """Smooth-step joint targets from q_start (default 0) to q_goal."""
    steps = max(1, int(seconds / dt))
    q0 = q_start or {k: 0.0 for k in q_goal}
    out = []
    for k in range(steps + 1):
        a = k / steps
        a = a * a * (3 - 2 * a)
        out.append({n: q0[n] + (q_goal[n] - q0[n]) * a for n in q_goal})
    return out
