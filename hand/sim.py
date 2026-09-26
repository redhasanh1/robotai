"""MuJoCo model of the right hand, simple on purpose: what the brain loop needs is "will this grasp hold?",
not a pretty render of every InMoov part.

    - palm facing UP, 4 fingers along +x, thumb on the -y side; flexion curls fingers up over the palm
    - each finger = 3 phalanges on hinges, coupled by equality constraints (one tendon drives the whole
      finger in the real hand, so it is 1 DOF here too) -> 5 finger DOF + 1 wrist DOF = the 6 servos
    - servos are position actuators whose targets move through the SAME rate-limited servo model as
      hand.plant, so sim and grey-box model agree by construction
    - test: the object rests in the open palm; the hand closes; then gravity is flipped (same as turning the
      hand palm-down) and shaken sideways; the grasp succeeded if the object is still in the hand 0.8 s later

Same MJCF runs on MuJoCo Warp (NVIDIA GPU, thousands of copies) later; nothing here is CPU-specific.
"""
import numpy as np
import mujoco

from . import config
from .plant import ServoPlant

FINGER_Y = {"index": 0.027, "middle": 0.009, "ring": -0.009, "pinky": -0.027}
FINGER_LEN = {"index": (0.042, 0.026, 0.020), "middle": (0.046, 0.029, 0.022),
              "ring": (0.043, 0.027, 0.020), "pinky": (0.035, 0.021, 0.017)}
FLEX_RAD = 1.6           # full flexion of the proximal joint
THUMB_RAD = 2.1
WRIST_RAD = 1.2

OBJECTS = {
    "ball":  '<geom type="sphere" size="0.024" mass="0.05" rgba="0.9 0.35 0.3 1"/>',
    "can":   '<geom type="cylinder" size="0.02 0.035" mass="0.06" rgba="0.3 0.6 0.9 1" euler="90 0 0"/>',
    "block": '<geom type="box" size="0.011 0.011 0.011" mass="0.02" rgba="0.95 0.8 0.2 1"/>',
    "bar":   '<geom type="capsule" size="0.009 0.05" mass="0.03" rgba="0.5 0.8 0.4 1" euler="90 0 0"/>',
}
OBJ_POS = {"ball": (0.03, 0.0, 0.137), "can": (0.02, 0.0, 0.133), "block": (0.03, 0.0, 0.124),
           "bar": (0.02, 0.0, 0.122)}


def _finger(name, y, lens):
    l1, l2, l3 = lens
    r = 0.0085
    return f"""
      <body name="{name}1" pos="0.045 {y} 0">
        <joint name="{name}_j1" type="hinge" axis="0 -1 0" range="0 1.7" damping="0.02"/>
        <geom type="capsule" fromto="0 0 0 {l1} 0 0" size="{r}"/>
        <body name="{name}2" pos="{l1} 0 0">
          <joint name="{name}_j2" type="hinge" axis="0 -1 0" range="0 1.7" damping="0.02"/>
          <geom type="capsule" fromto="0 0 0 {l2} 0 0" size="{r * 0.95}"/>
          <body name="{name}3" pos="{l2} 0 0">
            <joint name="{name}_j3" type="hinge" axis="0 -1 0" range="0 1.5" damping="0.02"/>
            <geom type="capsule" fromto="0 0 0 {l3} 0 0" size="{r * 0.9}"/>
            <site name="{name}_tip" pos="{l3} 0 0" size="0.004"/>
          </body>
        </body>
      </body>"""


def build_xml(obj="ball"):
    fingers = "".join(_finger(n, y, FINGER_LEN[n]) for n, y in FINGER_Y.items())
    eq = "".join(f'<joint joint1="{n}_j2" joint2="{n}_j1" polycoef="0 1.05 0 0 0"/>'
                 f'<joint joint1="{n}_j3" joint2="{n}_j1" polycoef="0 0.85 0 0 0"/>' for n in list(FINGER_Y) + ["thumb"])
    acts = "".join(f'<position name="{n}" joint="{n}_j1" kp="25" ctrlrange="0 {THUMB_RAD if n == "thumb" else FLEX_RAD}"/>'
                   for n in config.FINGERS)
    ox, oy, oz = OBJ_POS[obj]
    return f"""
<mujoco model="pinn_hand">
  <option timestep="0.002" gravity="0 0 -9.81" cone="elliptic" impratio="10"/>
  <default>
    <geom friction="1.2 0.02 0.001" condim="4" solref="0.005 1" rgba="0.92 0.9 0.86 1"/>
  </default>
  <visual><global offwidth="640" offheight="480"/></visual>
  <worldbody>
    <light pos="0.3 -0.3 0.6" dir="-0.5 0.5 -1"/>
    <geom type="plane" size="0.5 0.5 0.01" pos="0 0 -0.05" rgba="0.2 0.22 0.26 1" contype="0" conaffinity="0"/>
    <camera name="front" pos="0.3 -0.24 0.3" xyaxes="0.6 0.8 0 -0.4 0.3 0.87"/>
    <camera name="side" pos="0.02 -0.34 0.12" xyaxes="1 0 0 0 0 1"/>
    <body name="hand" pos="0 0 0.1">
      <joint name="wrist_j" type="hinge" axis="1 0 0" range="-{WRIST_RAD} {WRIST_RAD}" damping="0.5"/>
      <geom name="palm" type="box" size="0.045 0.042 0.012" pos="0 0 0" mass="0.2"/>
      <geom type="capsule" fromto="-0.06 0 0 -0.12 0 0" size="0.03" mass="0.3"/>
      {fingers}
      <body name="thumb1" pos="0.0 -0.046 0.004" euler="0 0 -20">
        <joint name="thumb_j1" type="hinge" axis="-1 0 0" range="0 2.2" damping="0.02"/>
        <geom type="capsule" fromto="0 0 0 0 -0.035 0" size="0.0095"/>
        <body name="thumb2" pos="0 -0.035 0">
          <joint name="thumb_j2" type="hinge" axis="-1 0 0" range="0 1.7" damping="0.02"/>
          <geom type="capsule" fromto="0 0 0 0 -0.028 0" size="0.009"/>
          <body name="thumb3" pos="0 -0.028 0">
            <joint name="thumb_j3" type="hinge" axis="-1 0 0" range="0 1.4" damping="0.02"/>
            <geom type="capsule" fromto="0 0 0 0 -0.022 0" size="0.0085"/>
            <site name="thumb_tip" pos="0 -0.022 0" size="0.004"/>
          </body>
        </body>
      </body>
    </body>
    <body name="object" pos="{ox} {oy} {oz}">
      <freejoint/>
      {OBJECTS[obj]}
    </body>
  </worldbody>
  <equality>{eq}</equality>
  <actuator>
    {acts}
    <position name="wrist" joint="wrist_j" kp="20" ctrlrange="-{WRIST_RAD} {WRIST_RAD}"/>
  </actuator>
</mujoco>"""


class SimHand:
    """Flexion-space wrapper: set_target(q) with q in config.JOINTS order, step(dt), grasp_test()."""

    def __init__(self, obj="ball", servos=None):
        self.obj = obj
        self.model = mujoco.MjModel.from_xml_string(build_xml(obj))
        self.data = mujoco.MjData(self.model)
        self.servo = ServoPlant(servos)          # the grey-box actuator model drives the sim targets
        self.q_cmd = np.zeros(config.N)
        self.act = [self.model.actuator(n).id for n in config.JOINTS]
        self._renderer = None
        mujoco.mj_forward(self.model, self.data)
        self._settle_object()

    def _settle_object(self):
        # let the object come to rest in the palm before anything moves
        for _ in range(100):
            mujoco.mj_step(self.model, self.data)

    def scale(self, q):
        q = np.asarray(q, float)
        s = np.array([THUMB_RAD] + [FLEX_RAD] * 4 + [WRIST_RAD])
        return q * s

    def set_target(self, q):
        self.q_cmd = np.clip(np.asarray(q, float), [0] * 5 + [-1], 1)

    def step(self, dt):
        n = max(1, int(round(dt / self.model.opt.timestep)))
        for _ in range(n):
            q = self.servo.step(self.q_cmd, self.model.opt.timestep)
            self.data.ctrl[self.act] = self.scale(q)
            mujoco.mj_step(self.model, self.data)

    def flexion(self):
        """Measured finger flexion from the sim joints (what vision will estimate on the real hand)."""
        j = [self.data.joint(f"{n}_j1").qpos[0] for n in config.FINGERS] + [self.data.joint("wrist_j").qpos[0]]
        return np.array(j) / np.array([THUMB_RAD] + [FLEX_RAD] * 4 + [WRIST_RAD])

    def object_pos(self):
        return self.data.body("object").xpos.copy()

    def palm_pos(self):
        return self.data.body("hand").xpos.copy()

    def contacts_with_object(self):
        oid = self.model.body("object").id
        hand_bodies = set()
        names = []
        for i in range(self.data.ncon):
            c = self.data.contact[i]
            b1, b2 = self.model.geom_bodyid[c.geom1], self.model.geom_bodyid[c.geom2]
            other = b2 if b1 == oid else b1 if b2 == oid else None
            if other is not None and self.model.body(other).name != "world":
                hand_bodies.add(self.model.body(other).name.rstrip("123"))
        return sorted(hand_bodies)

    def turn_over(self):
        """Flip gravity: identical physics to rotating the hand palm-down, without needing a 180 deg wrist."""
        self.model.opt.gravity[:] = (0, 0, 9.81)

    def grasp_test(self, q_grasp, close_s=0.8, hold_s=0.8):
        """Close to q_grasp, turn the hand over and shake it, report whether the object stayed in the hand."""
        self.set_target(q_grasp)
        self.step(close_s)
        touching = self.contacts_with_object()
        self.turn_over()
        for k in range(4):                       # sideways shake, +-3 m/s^2
            self.model.opt.gravity[1] = 3.0 if k % 2 == 0 else -3.0
            self.step(hold_s / 4)
        d = float(np.linalg.norm(self.object_pos() - self.palm_pos()))
        held = d < 0.075
        return {"held": bool(held), "dist": round(d, 4), "touching": touching,
                "flexion": np.round(self.flexion(), 3).tolist()}

    def render(self, camera="front", w=320, h=240):
        if self._renderer is None or self._renderer.width != w:
            self._renderer = mujoco.Renderer(self.model, h, w)
        self._renderer.update_scene(self.data, camera=camera)
        return self._renderer.render()


def evaluate(q_grasp, obj="ball"):
    """One fresh sim, one grasp. Deterministic, ~20 ms of CPU - cheap enough to run for every candidate."""
    return SimHand(obj).grasp_test(q_grasp)
