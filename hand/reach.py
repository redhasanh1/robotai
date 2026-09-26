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
