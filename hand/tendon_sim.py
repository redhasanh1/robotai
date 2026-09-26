"""Tendon-level InMoov finger in MuJoCo (Kimi round 7: every failure of the real hand lives in the tendons).

One finger = 3 phalanges on free hinges. Two lines run from the servo horn through guide points on every
phalanx: the FLEXOR on the palm side, the EXTENSOR on the back. Turning the horn by theta shortens the flexor by
r*theta and lets the extensor out by r*theta. Each line is a MuJoCo spatial tendon used as a real string: it can
only pull (a length limit that moves with the horn), it stretches a little (limit softness), it has slack, and it
drags (tendon frictionloss = the braid sliding in the PTFE tube). Hinges can be tight (joint frictionloss = a
printed hinge that binds).

    r = sweep(Finger(ptfe_friction=2.0))        # horn 0 -> max -> 0
    r["flex"], r["tension_flexor"], r["servo_torque_pct"], r["hysteresis"]

What it answers before the hand exists: does the finger close fully, how wide is the open/close hysteresis (that
feeds the grey-box plant's backlash), how hard does each line pull, what share of MG996R stall torque does it cost,
and which variant (tight hinge, more PTFE drag, more slack) breaks it.
"""
from dataclasses import dataclass, field

import numpy as np

MG996R_STALL_NM = 1.08          # 11 kg*cm at 6 V
HORN_R = 0.012                  # m, line wraps on a 12 mm radius
LINKS = (0.045, 0.028, 0.022)   # InMoov index phalanges, m
ARM = 0.006                     # tendon moment arm at each joint (guide hole offset from the hinge), m


@dataclass
class Finger:
    ptfe_friction: float = 0.5          # N of drag per line (tendon frictionloss)
    hinge_friction: tuple = (0.002, 0.002, 0.002)   # N*m per joint; a binding hinge is ~0.03+
    slack: float = 0.001                # m of free line before it pulls
    stretch: float = 0.002              # limit solref time constant, s: 200 lb PE braid barely stretches
    joint_spring: float = 0.004         # N*m/rad, printed-hinge / skin return
    obstacle: float = None              # flexion (0..1) where an object blocks the middle phalanx, None = free
    extra: dict = field(default_factory=dict)


def build_xml(f: Finger):
    L1, L2, L3 = LINKS
    fr = f.hinge_friction
    def sites(side):                     # guide points: palm side z<0 (flexor), back side z>0 (extensor)
        z = -ARM if side == "f" else ARM
        return z
    zf, ze = sites("f"), sites("e")
    obstacle = ""
    if f.obstacle is not None:
        a = f.obstacle * 1.6            # proximal joint angle where the object is met
        # a block under the proximal phalanx: the finger's tip swings down (-z) and rests on it
        ox, oz = 0.03 * np.cos(a) + 0.0, -0.03 * np.sin(a) - 0.012
        obstacle = f'<geom name="obj" type="box" size="0.01 0.02 0.004" pos="{ox:.4f} 0 {oz:.4f}" euler="0 {-np.degrees(a):.1f} 0" rgba="0.8 0.3 0.3 1"/>'
    return f"""
<mujoco model="tendon_finger">
  <option timestep="0.0005" gravity="0 0 -9.81"/>
  <default><geom contype="1" conaffinity="1" friction="0.8 0.01 0.001"/></default>
  <worldbody>
    <geom name="palm" type="box" size="0.03 0.02 0.006" pos="-0.03 0 0" rgba="0.8 0.8 0.8 1" contype="0" conaffinity="0"/>
    <site name="f0" pos="-0.25 0 {zf}"/><site name="e0" pos="-0.25 0 {ze}"/>
    <site name="fp" pos="-0.005 0 {zf}"/><site name="ep" pos="-0.005 0 {ze}"/>
    {obstacle}
    <body name="p1">
      <joint name="j1" type="hinge" axis="0 1 0" range="0 1.6" frictionloss="{fr[0]}" stiffness="{f.joint_spring}" damping="0.002"/>
      <geom type="capsule" fromto="0 0 0 {L1} 0 0" size="0.008" mass="0.008" contype="2" conaffinity="1"/>
      <site name="f1a" pos="0.006 0 {zf}"/><site name="f1b" pos="{L1 - 0.004} 0 {zf}"/>
      <site name="e1a" pos="0.006 0 {ze}"/><site name="e1b" pos="{L1 - 0.004} 0 {ze}"/>
      <body name="p2" pos="{L1} 0 0">
        <joint name="j2" type="hinge" axis="0 1 0" range="0 1.7" frictionloss="{fr[1]}" stiffness="{f.joint_spring}" damping="0.002"/>
        <geom type="capsule" fromto="0 0 0 {L2} 0 0" size="0.0075" mass="0.005" contype="2" conaffinity="1"/>
        <site name="f2a" pos="0.005 0 {zf}"/><site name="f2b" pos="{L2 - 0.004} 0 {zf}"/>
        <site name="e2a" pos="0.005 0 {ze}"/><site name="e2b" pos="{L2 - 0.004} 0 {ze}"/>
        <body name="p3" pos="{L2} 0 0">
          <joint name="j3" type="hinge" axis="0 1 0" range="0 1.5" frictionloss="{fr[2]}" stiffness="{f.joint_spring}" damping="0.002"/>
          <geom type="capsule" fromto="0 0 0 {L3} 0 0" size="0.007" mass="0.004" contype="2" conaffinity="1"/>
          <site name="f3" pos="{L3 - 0.003} 0 {zf}"/><site name="e3" pos="{L3 - 0.003} 0 {ze}"/>
        </body>
      </body>
    </body>
  </worldbody>
  <tendon>
    <spatial name="flexor" limited="true" range="0 1" frictionloss="{f.ptfe_friction}" solreflimit="{f.stretch} 1" width="0.0008" rgba="0.9 0.2 0.2 1">
      <site site="f0"/><site site="fp"/><site site="f1a"/><site site="f1b"/><site site="f2a"/><site site="f2b"/><site site="f3"/>
    </spatial>
    <spatial name="extensor" limited="true" range="0 1" frictionloss="{f.ptfe_friction}" solreflimit="{f.stretch} 1" width="0.0008" rgba="0.2 0.4 0.9 1">
      <site site="e0"/><site site="ep"/><site site="e1a"/><site site="e1b"/><site site="e2a"/><site site="e2b"/><site site="e3"/>
    </spatial>
  </tendon>
</mujoco>"""


def _tension(m, d, tid):
    """Force the tendon limit constraint is carrying (N) - the line tension."""
    import mujoco
    t = 0.0
    for i in range(d.nefc):
        if d.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON and d.efc_id[i] == tid:
            t += abs(d.efc_force[i])
    return t


def sweep(f: Finger, theta_max=2.6, steps=260, settle=80):
    """Horn 0 -> theta_max -> 0. Returns per-step horn angle, finger flexion (0..1 of full), both tensions,
    servo torque (% of MG996R stall) and summary numbers."""
    import mujoco
    m = mujoco.MjModel.from_xml_string(build_xml(f))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    fl, ex = m.tendon("flexor").id, m.tendon("extensor").id
    Lf0, Le0 = float(d.ten_length[fl]), float(d.ten_length[ex])
    full = 1.6 + 1.7 + 1.5
    thetas = np.r_[np.linspace(0, theta_max, steps // 2), np.linspace(theta_max, 0, steps // 2)]
    rows = []
    for th in thetas:
        m.tendon_range[fl] = (0, Lf0 + f.slack - HORN_R * th)       # horn wound in: flexor must be shorter
        m.tendon_range[ex] = (0, Le0 + f.slack + HORN_R * th)       # extensor paid out
        for _ in range(settle):
            mujoco.mj_step(m, d)
        q = d.qpos[:3].copy()
        tf, te = _tension(m, d, fl), _tension(m, d, ex)
        rows.append((th, float(q.sum() / full), tf, te, (tf - te) * HORN_R / MG996R_STALL_NM * 100))
    a = np.array(rows)
    up, down = a[: steps // 2], a[steps // 2:][::-1]
    hyst = float(np.max(np.abs(np.interp(up[:, 0], down[:, 0], down[:, 1]) - up[:, 1])))
    return {"theta": a[:, 0], "flex": a[:, 1], "tension_flexor": a[:, 2], "tension_extensor": a[:, 3],
            "servo_torque_pct": a[:, 4],
            "closes_to": round(float(a[:, 1].max()), 3), "hysteresis": round(hyst, 3),
            "peak_tension_n": round(float(a[:, 2].max()), 2),
            "peak_torque_pct": round(float(np.abs(a[:, 4]).max()), 1),
            "horn_for_90pct": (round(float(up[np.argmax(up[:, 1] >= 0.9 * up[:, 1].max()), 0]), 2)),
            # a real MG996R cannot exceed stall: past this horn angle it just stops (and heats up)
            "stall_horn_rad": (round(float(up[np.argmax(np.abs(up[:, 4]) >= 100), 0]), 2)
                               if np.any(np.abs(up[:, 4]) >= 100) else None),
            "flex_at_stall": (round(float(up[np.argmax(np.abs(up[:, 4]) >= 100), 1]), 2)
                              if np.any(np.abs(up[:, 4]) >= 100) else None),
            "torque_pct_at_90pct": round(float(np.abs(up[np.argmax(up[:, 1] >= 0.9 * up[:, 1].max()), 4])), 1)}


VARIANTS = {
    "nominal": Finger(),
    "PTFE drag x4": Finger(ptfe_friction=2.0),
    "tight middle hinge": Finger(hinge_friction=(0.002, 0.03, 0.002)),
    "5 mm slack": Finger(slack=0.005),
    "stretchy line (mono, not braid)": Finger(stretch=0.02),
    "closing on an object": Finger(obstacle=0.45),
}
