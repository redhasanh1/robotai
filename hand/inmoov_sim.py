"""The whole InMoov upper body in MuJoCo, built from the same URDF the website uses (Sentience Robotics, GPL-3.0).

The URDF's ~290 Collada meshes can't be loaded by MuJoCo, and a simulator doesn't need them: every link becomes a
capsule from its joint to each child joint (the skeleton), with the URDF's real joint positions, axes and limits.
Every movable joint gets a position actuator, so the MuJoCo viewer's Control panel shows one slider per joint -
drag the shoulder, elbow, wrist and fingers yourself.

    model = build_model()                 # mujoco.MjModel
    tools/arm_view.py                     # interactive window with sliders
    tools/arm_view.py --demo              # scripted reach -> rotate wrist -> close hand
"""
import os
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
URDF = os.path.join(os.path.dirname(HERE), "site", "models", "inmoov.urdf")
MESH_DIR = os.path.join(os.path.dirname(HERE), "logs", "inmoov_meshes")


def mesh_file(url):
    """Local STL path for a mesh URL (tools/fetch_inmoov_meshes.py fills the cache)."""
    return os.path.join(MESH_DIR, os.path.basename(url).replace(".dae", ".stl"))


SKIP = ("stand_link",)            # the display pole: no geometry, but everything mounted on it stays


def _rpy_to_quat(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r / 2), np.sin(r / 2), np.cos(p / 2), np.sin(p / 2), np.cos(y / 2), np.sin(y / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy)


def _short(name):
    return name.replace("i01.", "").replace("_link_joint", "").replace("_link", "").replace(".", "_")


def build_xml(urdf=URDF, meshes=None, extra=""):
    """meshes=None: use the real printed shapes if tools/fetch_inmoov_meshes.py has cached them, else skeleton."""
    root = ET.parse(urdf).getroot()
    links = {l.get("name"): l for l in root.findall("link")}
    if meshes is None:
        meshes = os.path.isdir(MESH_DIR) and len(os.listdir(MESH_DIR)) > 200
    assets = []
    joints = root.findall("joint")
    kids = {}
    for j in joints:
        kids.setdefault(j.find("parent").get("link"), []).append(j)
    parents = {j.find("child").get("link") for j in joints}
    base = next(l.get("name") for l in root.findall("link") if l.get("name") not in parents)
    acts, n_geom = [], [0]

    def origin(j):
        o = j.find("origin")
        xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
        rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
        return xyz, rpy

    def body(link, depth):
        out = []
        for j in kids.get(link, []) if link not in SKIP else []:
            xyz, _ = origin(j)
            if np.linalg.norm(xyz) > 1e-4:
                r = 0.018 if "Hand" not in link and "hand" not in link else 0.006
                grp = ' group="3"' if meshes else ""          # skeleton hidden when the real shapes are shown
                out.append(f'<geom type="capsule" fromto="0 0 0 {xyz[0]:.5f} {xyz[1]:.5f} {xyz[2]:.5f}" size="{r}"{grp}/>')
                n_geom[0] += 1
        for v in (links[link].findall("visual") if meshes and link in links else []):
            m = v.find("geometry/mesh")
            if m is None or "stand" in m.get("filename", ""):
                continue
            f = mesh_file(m.get("filename"))
            if not os.path.exists(f):
                continue
            o = v.find("origin")
            vx = [float(a) for a in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
            vq = _rpy_to_quat(*[float(a) for a in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()])
            name = f"m{len(assets)}"
            assets.append(f'<mesh name="{name}" file="{os.path.basename(f)}" scale="{m.get("scale", "1 1 1")}" inertia="shell"/>')
            out.append(f'<geom type="mesh" mesh="{name}" pos="{vx[0]:.5f} {vx[1]:.5f} {vx[2]:.5f}" '
                       f'quat="{vq[0]:.6f} {vq[1]:.6f} {vq[2]:.6f} {vq[3]:.6f}" group="1"/>')
        if not kids.get(link):
            out.append('<geom type="sphere" size="0.008"/>')
        for j in kids.get(link, []):
            child = j.find("child").get("link")
            xyz, rpy = origin(j)
            q = _rpy_to_quat(*rpy)
            inner = []
            if j.get("type") in ("revolute", "continuous"):
                ax = j.find("axis").get("xyz") if j.find("axis") is not None else "0 0 1"
                lim = j.find("limit")
                lo, hi = (float(lim.get("lower", 0)), float(lim.get("upper", 0))) if lim is not None else (0, 0)
                name = _short(j.get("name"))
                rng = f'range="{lo} {hi}"' if hi > lo else ""
                if hi > lo:                           # a joint with no range has no motor: weld it, or it spins free
                    inner.append(f'<joint name="{name}" type="hinge" axis="{ax}" {rng} damping="2" armature="0.02"/>')
                    acts.append(f'<position name="{name}" joint="{name}" kp="30" ctrlrange="{lo} {hi}"/>')
            inner.append('<inertial pos="0 0 0" mass="0.2" diaginertia="2e-3 2e-3 2e-3"/>')   # posing model: mass is nominal
            inner += body(child, depth + 1)
            out.append(f'<body name="{_short(child)}" pos="{xyz[0]:.5f} {xyz[1]:.5f} {xyz[2]:.5f}" '
                       f'quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}">' + "".join(inner) + "</body>")
        return out

    tree = "".join(body(base, 0))
    meshdir = MESH_DIR.replace(chr(92), "/")
    return f"""<mujoco model="inmoov_skeleton">
  <compiler angle="radian" meshdir="{meshdir}" inertiafromgeom="false"/>
  <asset>{"".join(assets)}</asset>
  <option timestep="0.002" gravity="0 0 0"/>
  <default><geom rgba="0.9 0.88 0.84 1" contype="0" conaffinity="0" mass="0.05"/></default>
  <visual><global offwidth="800" offheight="600"/></visual>
  <worldbody>
    <light pos="0 -1 2" dir="0 0.5 -1"/>
    <geom type="plane" size="2 2 0.01" pos="0 0 0" rgba="0.2 0.22 0.26 1"/>
    <body name="{_short(base)}" pos="0 0 0">{tree}</body>
    {extra}
  </worldbody>
  <actuator>{"".join(acts)}</actuator>
</mujoco>"""


def build_model(urdf=URDF, meshes=None, extra=""):
    import mujoco
    return mujoco.MjModel.from_xml_string(build_xml(urdf, meshes, extra))
