"""robotai legs: human-proportioned dynamic legs (backflips, running, boxing footwork need light legs with
strong hips and knees). Original design.
  * 7 joints per leg: hip yaw, hip roll, hip pitch, knee, ankle pitch, ankle roll, toe.
  * Quasi-direct-drive actuators (dark drum + metal output gear + bolt circle) at the hip and knee; the two
    ankle actuators sit high in the calf and drive the foot through push rods with ball-joint rod ends
    (Atlas / Optimus / Unitree H1 style), keeping the swinging mass near the knee.
  * Smooth lofted thigh / calf shells over a visible metal frame (side rails, cable runs).
The legs hang from the root Empty at the hip (world origin); the soles end LEG_LENGTH below it.
"""
import math

import parts as P

HIP_SPACING = 0.10      # half the distance between hip joints
HIP_DROP = 0.07         # pelvis centre down to the hip pitch axis
THIGH = 0.42            # hip pitch -> knee
SHIN = 0.42             # knee -> ankle
ANKLE_H = 0.07          # ankle axis -> sole
FOOT_BACK, FOOT_FRONT = 0.06, 0.16
TOE_LEN = 0.06
LEG_LENGTH = HIP_DROP + THIGH + SHIN + ANKLE_H


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def build(root):
    # pelvis: rounded shell with a dark hip bridge and vents
    P.box("pelvis_shell", (0, 0, -0.005), (0.30, 0.18, 0.09), root, bevel=0.03)
    P.box("pelvis_bridge", (0, 0.01, -0.06), (0.26, 0.12, 0.03), root, mat=P.DRIVE, bevel=0.008, subdiv=1)
    for i in range(4):
        P.box(f"pelvis_vent_{i}", (-0.045 + 0.03 * i, -0.091, 0.0), (0.018, 0.004, 0.035), root, mat=P.DRIVE, bevel=0.002, subdiv=0)

    for side, sx in (("left", 1), ("right", -1)):
        x = sx * HIP_SPACING
        hy = P.joint(f"{side}_hip_yaw", root, (x, 0, -0.03))
        P.actuator(f"{side}_hip_yaw_drive", (x, 0.0, -0.05), "Z", hy, r=0.045, w=0.028, teeth=20, n_bolts=6)

        hr = P.joint(f"{side}_hip_roll", hy, (x, 0, -HIP_DROP))
        P.actuator(f"{side}_hip_roll_drive", (x, 0.05, -HIP_DROP), "Y", hr, r=0.048, w=0.045, teeth=22)

        hp = P.joint(f"{side}_hip_pitch", hr, (x, 0, -HIP_DROP))
        P.actuator(f"{side}_hip_pitch_drive", (x + sx * 0.058, 0, -HIP_DROP), "X" if sx > 0 else "X", hp, r=0.058, w=0.055, teeth=28, n_bolts=10)

        # thigh: frame rails + lofted muscle shell (quads bulge at the front, slight taper to the knee)
        top_z = -HIP_DROP - 0.03
        tl = THIGH - 0.075
        P.rail(f"{side}_thigh_rail_out", (x + sx * 0.062, 0, top_z), (x + sx * 0.055, 0, top_z - tl), hp)
        P.rail(f"{side}_thigh_rail_in", (x - sx * 0.05, 0, top_z), (x - sx * 0.045, 0, top_z - tl), hp)
        P.loft(f"{side}_thigh_shell", (x, 0, top_z), tl,
               lambda t: 0.068 - 0.02 * t + 0.006 * bump(t, 0.3, 0.3), hp, rx=1.0, ry=0.95,
               front=lambda t: 0.016 * bump(t, 0.4, 0.25) + 0.008 * bump(t, 0.8, 0.12),
               back=lambda t: 0.008 * bump(t, 0.25, 0.3))
        P.rod(f"{side}_thigh_cable", (x - sx * 0.02, 0.058, top_z), (x - sx * 0.02, 0.05, top_z - tl), hp, r=0.005)

        # knee: big actuator with an exposed gear stack on the outside, kneecap guard
        kz = -HIP_DROP - THIGH
        kn = P.joint(f"{side}_knee", hp, (x, 0, kz))
        P.actuator(f"{side}_knee_drive", (x + sx * 0.052, 0, kz), "X", kn, r=0.05, w=0.05, teeth=26)
        P.gear(f"{side}_knee_idler", (x + sx * 0.085, 0.035, kz + 0.035), "X", 0.018, 12, 0.006, kn)
        P.blob(f"{side}_kneecap", (x, -0.052, kz + 0.012), (0.038, 0.022, 0.045), kn, subdiv=2)

        # calf: lofted shell with the calf muscle at the back, shin guard at the front, frame rails
        ctop = kz - 0.035
        cl = SHIN - 0.07
        P.rail(f"{side}_shin_rail_out", (x + sx * 0.05, 0, ctop), (x + sx * 0.034, 0, ctop - cl), kn)
        P.rail(f"{side}_shin_rail_in", (x - sx * 0.045, 0, ctop), (x - sx * 0.03, 0, ctop - cl), kn)
        P.loft(f"{side}_calf_shell", (x, 0.004, ctop), cl,
               lambda t: 0.05 - 0.022 * t, kn, rx=0.95, ry=0.9,
               back=lambda t: 0.034 * bump(t, 0.28, 0.22),
               front=lambda t: 0.004)
        P.box(f"{side}_shin_guard", (x, -0.05, ctop - cl * 0.45), (0.05, 0.012, cl * 0.75), kn, bevel=0.006)
        # ankle actuators high in the calf, push rods down to the foot with ball-joint rod ends
        az = kz - SHIN
        for tag, dx in (("a", 0.024), ("b", -0.024)):
            P.actuator(f"{side}_ankle_drive_{tag}", (x + dx, 0.07, kz - 0.09), "X", kn, r=0.026, w=0.026, teeth=14, n_bolts=5)
            top_end, bot_end = (x + dx, 0.09, kz - 0.1), (x + dx, 0.05, az + 0.01)
            P.rod(f"{side}_ankle_rod_{tag}", top_end, bot_end, kn, r=0.0055, mat=P.METAL)
            P.blob(f"{side}_ankle_rodend_{tag}", bot_end, (0.009, 0.009, 0.009), kn, mat=P.METAL, subdiv=0, segments=16)

        ap = P.joint(f"{side}_ankle_pitch", kn, (x, 0, az))
        P.blob(f"{side}_ankle_cross", (x, 0, az), (0.026, 0.026, 0.026), ap, mat=P.DRIVE, subdiv=0, segments=24)
        P.bolts(f"{side}_ankle_pin", (x + sx * 0.03, 0, az), "X", 0.0, 1, ap, r=0.009, h=0.01)

        ar = P.joint(f"{side}_ankle_roll", ap, (x, 0, az))
        sole_z = az - ANKLE_H
        foot_len = FOOT_BACK + FOOT_FRONT
        fy = (FOOT_BACK - FOOT_FRONT) / 2
        P.box(f"{side}_ankle_yoke", (x, 0, az - 0.025), (0.06, 0.05, 0.04), ar, mat=P.DRIVE, bevel=0.008, subdiv=1)
        P.box(f"{side}_foot_shell", (x, fy, sole_z + 0.035), (0.095, foot_len, 0.05), ar, bevel=0.018)
        P.box(f"{side}_heel_pad", (x, FOOT_BACK - 0.02, sole_z + 0.03), (0.09, 0.04, 0.045), ar, mat=P.DRIVE, bevel=0.012)
        P.box(f"{side}_sole", (x, fy, sole_z + 0.007), (0.1, foot_len + 0.005, 0.014), ar, mat=P.DRIVE, bevel=0.005, subdiv=1)
        for i in range(6):
            P.box(f"{side}_tread_{i}", (x, fy - foot_len / 2 + 0.02 + i * 0.037, sole_z + 0.001), (0.1, 0.012, 0.004), ar,
                  mat=P.METAL, bevel=0.001, subdiv=0)

        toe = P.joint(f"{side}_toe", ar, (x, -FOOT_FRONT, sole_z + 0.02))
        P.rod(f"{side}_toe_hinge", (x - 0.045, -FOOT_FRONT, sole_z + 0.02), (x + 0.045, -FOOT_FRONT, sole_z + 0.02), toe, r=0.006, mat=P.METAL)
        P.box(f"{side}_toe_shell", (x, -FOOT_FRONT - TOE_LEN / 2, sole_z + 0.022), (0.09, TOE_LEN, 0.036), toe, bevel=0.014)
        P.box(f"{side}_toe_sole", (x, -FOOT_FRONT - TOE_LEN / 2, sole_z + 0.006), (0.094, TOE_LEN + 0.004, 0.012), toe,
              mat=P.DRIVE, bevel=0.004, subdiv=1)
