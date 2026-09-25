"""robotai upper body: original design for a 1.8 m humanoid, built up from the hip root.
Inspired by the general feel of open printed humanoids (white panels, a humanlike face, exposed mechanics) but
every shape here is our own parametric geometry.
  * Spine: waist yaw + spine pitch, segmented flexible abdomen with side rails, lofted chest with pectoral panels,
    a glowing chest ring, a dark back pack with vents.
  * Head: humanlike face (brow, camera eyes with glowing irises, nose, mouth line, jaw) on a skull shell;
    neck yaw + pitch with exposed tendon rods.
  * Arms (6 joints each): shoulder pitch / roll / yaw, elbow, wrist yaw / pitch; actuators with exposed gears.
    The forearm has an open service window showing the five finger servos and their tendon pulleys (3 over 2).
  * Hands: 4 fingers x 3 segments + a 3-segment thumb, metal knuckle pins, dark fingertip pads, palm facing
    forward in the rest pose.
"""
import math

import parts as P

SHOULDER_X, SHOULDER_Z = 0.22, 0.47   # shoulder joint, relative to the hip root
UPPER_ARM, FOREARM = 0.28, 0.24
NECK_Z, HEAD_Z = 0.56, 0.71

FINGERS = {  # lateral offset from the hand centre (towards the thumb), segment lengths
    "index": (0.028, (0.038, 0.024, 0.020)),
    "middle": (0.009, (0.042, 0.026, 0.021)),
    "ring": (-0.010, (0.039, 0.024, 0.020)),
    "pinky": (-0.028, (0.030, 0.020, 0.017)),
}
THUMB = (0.030, 0.025, 0.020)


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def build_head(parent):
    hz = HEAD_Z
    P.blob("skull_shell", (0, 0.012, hz + 0.01), (0.083, 0.1, 0.112), parent, subdiv=2)
    P.blob("face_plate", (0, -0.03, hz - 0.012), (0.074, 0.075, 0.1), parent, subdiv=2)
    P.blob("jaw", (0, -0.035, hz - 0.075), (0.056, 0.058, 0.04), parent, subdiv=2)
    P.blob("brow", (0, -0.088, hz + 0.028), (0.06, 0.018, 0.014), parent, subdiv=2)
    P.box("nose", (0, -0.1, hz - 0.012), (0.016, 0.022, 0.036), parent, bevel=0.007)
    P.box("mouth_line", (0, -0.098, hz - 0.05), (0.034, 0.004, 0.004), parent, mat=P.DRIVE, bevel=0.0015, subdiv=0)
    for side, sx in (("left", 1), ("right", -1)):
        ex = sx * 0.029
        P.blob(f"{side}_eye_socket", (ex, -0.086, hz + 0.008), (0.019, 0.012, 0.014), parent, mat=P.DRIVE, subdiv=1)
        P.ring(f"{side}_eye_lens", (ex, -0.097, hz + 0.008), 0.009, 0.0022, "Y", parent, mat=P.METAL)
        P.blob(f"{side}_eye_iris", (ex, -0.096, hz + 0.008), (0.006, 0.003, 0.006), parent, mat=P.ACCENT, subdiv=0, segments=16)
        P.drum(f"{side}_ear", (sx * 0.083, 0.012, hz + 0.0), "X", parent, r=0.028, w=0.018)
        P.ring(f"{side}_ear_light", (sx * 0.093, 0.012, hz), 0.017, 0.0025, "X", parent, mat=P.ACCENT)
    for i in range(5):  # skull vent fins
        P.box(f"skull_fin_{i}", (0, 0.03 + 0.018 * i, hz + 0.118 - 0.012 * i), (0.05, 0.006, 0.01), parent,
              mat=P.DRIVE, bevel=0.002, subdiv=0)


def build(root):
    # ---- spine ----
    wy = P.joint("waist_yaw", root, (0, 0, 0.03))
    P.actuator("waist_drive", (0, 0, 0.05), "Z", wy, r=0.07, w=0.03, teeth=30, n_bolts=10)
    sp = P.joint("spine", wy, (0, 0, 0.10))
    for i, z in enumerate((0.105, 0.15, 0.195, 0.24)):
        P.drum(f"abdomen_ring_{i}", (0, 0, z), "Z", sp, r=0.1 - 0.003 * i, w=0.034, ring=False)
    for sx in (1, -1):
        P.rail(f"abdomen_rail_{'l' if sx > 0 else 'r'}", (sx * 0.085, -0.02, 0.09), (sx * 0.09, -0.02, 0.27), sp)
    P.box("abdomen_plate", (0, -0.092, 0.17), (0.12, 0.022, 0.15), sp, bevel=0.012)
    for i in range(3):
        P.box(f"abdomen_groove_{i}", (0, -0.104, 0.125 + 0.045 * i), (0.1, 0.003, 0.004), sp, mat=P.DRIVE, bevel=0.001, subdiv=0)

    # chest: lofted torso shell, broad at the shoulders, tapering to the waist, with pectoral panels
    P.loft("chest_shell", (0, 0.0, 0.55), 0.29,
           lambda t: 0.105 + 0.02 * bump(t, 0.35, 0.3) - 0.02 * t, sp, rx=1.62, ry=1.0,
           front=lambda t: 0.012 * bump(t, 0.35, 0.2), back=lambda t: 0.01 * bump(t, 0.4, 0.3), subdiv=1)
    for sx in (1, -1):
        P.blob(f"pec_{'l' if sx > 0 else 'r'}", (sx * 0.068, -0.1, 0.44), (0.07, 0.022, 0.058), sp, subdiv=2)
    P.box("sternum_seam", (0, -0.121, 0.42), (0.006, 0.004, 0.14), sp, mat=P.DRIVE, bevel=0.001, subdiv=0)
    P.ring("chest_light", (0, -0.121, 0.36), 0.028, 0.006, "Y", sp, mat=P.ACCENT)
    P.box("back_pack", (0, 0.11, 0.39), (0.22, 0.05, 0.22), sp, mat=P.DRIVE, bevel=0.02, subdiv=1)
    for i in range(5):
        P.box(f"back_vent_{i}", (0, 0.137, 0.32 + 0.032 * i), (0.16, 0.004, 0.012), sp, mat=P.METAL, bevel=0.001, subdiv=0)
    P.box("shoulder_yoke", (0, 0, 0.525), (0.38, 0.12, 0.05), sp, bevel=0.022, subdiv=2)

    # ---- neck + head ----
    P.actuator("neck_drive", (0, 0, NECK_Z), "Z", sp, r=0.04, w=0.025, teeth=18, n_bolts=6)
    ny = P.joint("neck_yaw", sp, (0, 0, NECK_Z))
    P.drum("neck_column", (0, 0, NECK_Z + 0.035), "Z", ny, r=0.028, w=0.055, ring=False)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        P.rod(f"neck_tendon_{k}", (0.04 * math.cos(a), 0.04 * math.sin(a), NECK_Z + 0.012),
              (0.03 * math.cos(a), 0.03 * math.sin(a), NECK_Z + 0.07), ny, r=0.0035, mat=P.METAL)
    npch = P.joint("neck_pitch", ny, (0, 0, NECK_Z + 0.065))
    build_head(npch)

    # ---- arms ----
    for side, sx in (("left", 1), ("right", -1)):
        x = sx * (SHOULDER_X + 0.015)
        spt = P.joint(f"{side}_shoulder_pitch", sp, (x, 0, SHOULDER_Z))
        P.actuator(f"{side}_shoulder_pitch_drive", (sx * 0.2, 0, SHOULDER_Z), "X", spt, r=0.056, w=0.045, teeth=30, n_bolts=10)
        P.blob(f"{side}_shoulder_cap", (x + sx * 0.02, 0, SHOULDER_Z + 0.012), (0.062, 0.064, 0.058), spt, subdiv=2)
        srl = P.joint(f"{side}_shoulder_roll", spt, (x, 0, SHOULDER_Z))
        P.actuator(f"{side}_shoulder_roll_drive", (x, 0.045, SHOULDER_Z - 0.045), "Y", srl, r=0.034, w=0.026, teeth=16, n_bolts=6)
        syw = P.joint(f"{side}_shoulder_yaw", srl, (x, 0, SHOULDER_Z - 0.05))
        ua_top, ual = SHOULDER_Z - 0.055, UPPER_ARM - 0.075
        P.loft(f"{side}_upper_arm_shell", (x, 0, ua_top), ual,
               lambda t: 0.047 - 0.01 * t, syw, ry=0.95,
               front=lambda t: 0.012 * bump(t, 0.45, 0.25), back=lambda t: 0.008 * bump(t, 0.35, 0.3))
        P.rail(f"{side}_upper_arm_rail", (x + sx * 0.044, 0, ua_top), (x + sx * 0.038, 0, ua_top - ual), syw, w=0.009)

        ez = SHOULDER_Z - UPPER_ARM
        el = P.joint(f"{side}_elbow", syw, (x, 0, ez))
        P.actuator(f"{side}_elbow_drive", (x + sx * 0.012, 0, ez), "X", el, r=0.038, w=0.06, teeth=20, n_bolts=6)
        fa_top, fal = ez - 0.03, FOREARM - 0.045
        P.loft(f"{side}_forearm_shell", (x, 0.006, fa_top), fal,
               lambda t: 0.045 - 0.014 * t + 0.004 * bump(t, 0.2, 0.2), el, ry=0.92,
               front=lambda t: 0.003)
        # open service window on the front of the forearm: the five finger servos, 3 over 2, with pulleys
        P.box(f"{side}_forearm_window", (x, -0.037, fa_top - 0.085), (0.07, 0.012, 0.13), el, mat=P.DRIVE, bevel=0.006, subdiv=1)
        for k, (dx, dz) in enumerate([(-0.022, 0), (0, 0), (0.022, 0), (-0.011, -0.05), (0.011, -0.05)]):
            P.servo(f"{side}_finger_servo_{k}", (x + dx, -0.03, fa_top - 0.05 + dz), el)
        for k in range(5):  # tendons from the servo pulleys down to the wrist
            dx = (-0.02, -0.01, 0.0, 0.01, 0.02)[k]
            P.rod(f"{side}_tendon_{k}", (x + dx, -0.052, fa_top - 0.14), (x + dx * 0.8, -0.03, ez - FOREARM + 0.01), el, r=0.0012, mat=P.METAL)

        wz = ez - FOREARM
        wyj = P.joint(f"{side}_wrist_yaw", el, (x, 0, wz))
        P.actuator(f"{side}_wrist_drive", (x, 0, wz + 0.004), "Z", wyj, r=0.029, w=0.016, teeth=14, n_bolts=5)
        wp = P.joint(f"{side}_wrist_pitch", wyj, (x, 0, wz - 0.012))
        P.box(f"{side}_palm_shell", (x, 0.002, wz - 0.06), (0.086, 0.032, 0.088), wp, bevel=0.014, subdiv=2)
        P.box(f"{side}_palm_pad", (x, -0.015, wz - 0.066), (0.07, 0.004, 0.06), wp, mat=P.DRIVE, bevel=0.003, subdiv=1)
        P.ring(f"{side}_palm_light", (x, 0.019, wz - 0.058), 0.012, 0.0025, "Y", wp, mat=P.ACCENT)

        top = wz - 0.105
        P.rod(f"{side}_knuckle_pin", (x - 0.042, 0, top), (x + 0.042, 0, top), wp, r=0.004, mat=P.METAL)
        for name, (off, lens) in FINGERS.items():
            fx = x + sx * off
            parent, z = wp, top
            for k, ln in enumerate(lens, 1):
                j = P.joint(f"{side}_{name}_{k}", parent, (fx, 0, z))
                P.box(f"{side}_{name}_{k}_shell", (fx, 0, z - ln / 2 - 0.001), (0.017, 0.02, ln - 0.002), j,
                      mat=P.SHELL if k < 3 else P.DRIVE, bevel=0.0065, subdiv=1)
                if k < 3:
                    P.rod(f"{side}_{name}_{k}_pin", (fx - 0.01, 0, z - ln), (fx + 0.01, 0, z - ln), j, r=0.0028, mat=P.METAL)
                parent, z = j, z - ln
        tx, tz = x + sx * 0.052, wz - 0.07
        parent = wp
        for k, ln in enumerate(THUMB, 1):
            j = P.joint(f"{side}_thumb_{k}", parent, (tx, -0.012, tz))
            P.box(f"{side}_thumb_{k}_shell", (tx, -0.012, tz - ln / 2 - 0.001), (0.019, 0.02, ln - 0.002), j,
                  mat=P.SHELL if k < 3 else P.DRIVE, bevel=0.0065, subdiv=1)
            parent, tz = j, tz - ln
