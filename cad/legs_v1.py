"""robotai legs v1: human-proportioned dynamic legs for the life-size InMoov upper body.

Run headless:  blender -b -P cad/legs_v1.py -- <out.glb>

Design intent (backflips, running, boxing footwork need light legs with strong hips/knees):
  * 7 joints per leg: hip yaw, hip roll, hip pitch, knee, ankle pitch, ankle roll, toe.
  * Big quasi-direct-drive actuator drums at the hip and knee; the ankle actuators sit high in the calf
    and drive the foot through two push rods (Atlas / Optimus / Unitree H1 style), which keeps the
    swinging mass near the knee and the foot light.
  * White printed shells shaped like thigh and calf muscle, a kneecap, and a heel + toe foot, to match
    the InMoov's look.
Units are metres, Blender Z-up, robot facing -Y (glTF export turns this into Y-up, facing +Z).
Every joint is an Empty named <side>_<joint>, parented in chain order, with identity rotation so its
local X/Y/Z axes are pitch / roll / yaw. Materials are named "shell" (white) and "drive" (dark).
"""
import math
import sys

import bpy
from mathutils import Vector

# ---- dimensions (1.8 m humanoid) ----
HIP_SPACING = 0.10      # half the distance between hip joints
HIP_DROP = 0.07         # pelvis centre down to the hip pitch axis
THIGH = 0.42            # hip pitch -> knee
SHIN = 0.42             # knee -> ankle
ANKLE_H = 0.07          # ankle axis -> sole
FOOT_BACK, FOOT_FRONT = 0.06, 0.16   # heel and ball of foot from the ankle, along -Y
TOE_LEN = 0.06
DRUM_R, DRUM_W = 0.055, 0.06          # hip/knee actuator drums

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


SHELL = material("shell", (0.93, 0.94, 0.95), 0.5)
DRIVE = material("drive", (0.08, 0.09, 0.11), 0.4)


def finish(obj, mat, bevel=0.006, subdiv=2, smooth=True):
    """Bevel + subdivide for a printed-part look, then apply so the export is plain mesh."""
    obj.data.materials.append(mat)
    if bevel:
        b = obj.modifiers.new("bevel", "BEVEL")
        b.width, b.segments, b.limit_method = bevel, 2, "ANGLE"
    if subdiv:
        s = obj.modifiers.new("subdiv", "SUBSURF")
        s.levels = s.render_levels = subdiv
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def joint(name, parent, head):
    """An Empty at a joint axis. `head` is in world space; the chain is built in the rest pose."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.03
    scene.collection.objects.link(e)
    e.location = head
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    bpy.context.view_layer.update()
    return e


def attach(obj, parent):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def drum(name, loc, axis, parent, r=DRUM_R, w=DRUM_W):
    """Actuator drum: dark cylinder with a lighter cap ring, axis 'X' | 'Y' | 'Z'."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=w, location=loc)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = {"X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0), "Z": (0, 0, 0)}[axis]
    finish(o, DRIVE, bevel=0.004, subdiv=0)
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.72, minor_radius=r * 0.08, location=loc)
    ring = bpy.context.object
    ring.name = name + "_ring"
    ring.rotation_euler = o.rotation_euler
    off = Vector({"X": (w / 2, 0, 0), "Y": (0, w / 2, 0), "Z": (0, 0, w / 2)}[axis])
    ring.location = Vector(loc) + off
    finish(ring, SHELL, bevel=0, subdiv=0)
    attach(o, parent)
    attach(ring, parent)
    return o


def muscle(name, top, length, r_top, r_bot, depth_scale, bulge, bulge_z, parent, bulge_back=False):
    """Tapered limb shell with a soft muscle bulge (front for thigh, back for calf)."""
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r_bot, radius2=r_top, depth=length,
                                    location=(top[0], top[1], top[2] - length / 2))
    o = bpy.context.object
    o.name = name
    o.scale = (1.0, depth_scale, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    # bulge: push vertices near bulge_z outward along -Y (front) or +Y (back)
    zc = top[2] - length * bulge_z
    sign = 1 if bulge_back else -1
    for v in o.data.vertices:
        wz = o.matrix_world @ v.co
        k = math.exp(-((wz.z - zc) / (length * 0.22)) ** 2)
        if (v.co.y * sign) > 0:
            v.co.y += sign * bulge * k
    finish(o, SHELL, bevel=0, subdiv=2)
    attach(o, parent)
    return o


def box(name, loc, size, parent, mat=SHELL, bevel=0.012, subdiv=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    finish(o, mat, bevel=bevel, subdiv=subdiv)
    attach(o, parent)
    return o


def rod(name, a, b, parent, r=0.006):
    a, b = Vector(a), Vector(b)
    mid, d = (a + b) / 2, b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=d.length, location=mid)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    finish(o, DRIVE, bevel=0, subdiv=0)
    attach(o, parent)
    return o


# ---- pelvis ----
root = joint("legs_root", None, (0, 0, 0))
box("pelvis_shell", (0, 0, -0.02), (0.30, 0.17, 0.10), root)
drum("pelvis_waist_drive", (0, 0, 0.035), "Z", root, r=0.06, w=0.035)

for side, sx in (("left", 1), ("right", -1)):
    x = sx * HIP_SPACING
    hy = joint(f"{side}_hip_yaw", root, (x, 0, -0.03))
    drum(f"{side}_hip_yaw_drive", (x, 0, -0.045), "Z", hy, r=0.045, w=0.03)

    hr = joint(f"{side}_hip_roll", hy, (x, 0, -HIP_DROP))
    drum(f"{side}_hip_roll_drive", (x, 0.045, -HIP_DROP), "Y", hr, r=0.048, w=0.05)

    hp = joint(f"{side}_hip_pitch", hr, (x, 0, -HIP_DROP))
    drum(f"{side}_hip_pitch_drive", (x + sx * 0.055, 0, -HIP_DROP), "X", hp)
    thigh_top = (x, 0, -HIP_DROP - 0.02)
    muscle(f"{side}_thigh_shell", thigh_top, THIGH - 0.05, 0.078, 0.058, 0.95, 0.018, 0.35, hp)

    kz = -HIP_DROP - THIGH
    kn = joint(f"{side}_knee", hp, (x, 0, kz))
    drum(f"{side}_knee_drive", (x + sx * 0.05, 0, kz), "X", kn, r=0.05, w=0.055)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.035, location=(x, -0.045, kz + 0.01))
    cap = bpy.context.object
    cap.name = f"{side}_kneecap"
    cap.scale = (1.0, 0.55, 1.15)
    bpy.ops.object.transform_apply(scale=True)
    finish(cap, SHELL, bevel=0, subdiv=1)
    attach(cap, kn)
    muscle(f"{side}_calf_shell", (x, 0.005, kz - 0.03), SHIN - 0.06, 0.06, 0.036, 1.0, 0.03, 0.3, kn, bulge_back=True)
    # ankle drives live high in the calf; two push rods run down to the foot
    drum(f"{side}_ankle_drive_a", (x + 0.022, 0.05, kz - 0.09), "X", kn, r=0.028, w=0.03)
    drum(f"{side}_ankle_drive_b", (x - 0.022, 0.05, kz - 0.09), "X", kn, r=0.028, w=0.03)
    az = kz - SHIN
    rod(f"{side}_ankle_rod_a", (x + 0.022, 0.068, kz - 0.09), (x + 0.022, 0.035, az + 0.005), kn)
    rod(f"{side}_ankle_rod_b", (x - 0.022, 0.068, kz - 0.09), (x - 0.022, 0.035, az + 0.005), kn)

    ap = joint(f"{side}_ankle_pitch", kn, (x, 0, az))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.028, location=(x, 0, az))
    ball = bpy.context.object
    ball.name = f"{side}_ankle_cross"
    finish(ball, DRIVE, bevel=0, subdiv=0)
    attach(ball, ap)

    ar = joint(f"{side}_ankle_roll", ap, (x, 0, az))
    sole_z = az - ANKLE_H
    foot_len = FOOT_BACK + FOOT_FRONT
    box(f"{side}_foot_shell", (x, (FOOT_BACK - FOOT_FRONT) / 2, sole_z + 0.035), (0.095, foot_len, 0.05), ar)
    box(f"{side}_sole", (x, (FOOT_BACK - FOOT_FRONT) / 2, sole_z + 0.007), (0.1, foot_len + 0.005, 0.014), ar, mat=DRIVE, bevel=0.005, subdiv=1)

    toe = joint(f"{side}_toe", ar, (x, -FOOT_FRONT, sole_z + 0.02))
    box(f"{side}_toe_shell", (x, -FOOT_FRONT - TOE_LEN / 2, sole_z + 0.022), (0.09, TOE_LEN, 0.036), toe)
    box(f"{side}_toe_sole", (x, -FOOT_FRONT - TOE_LEN / 2, sole_z + 0.006), (0.094, TOE_LEN + 0.004, 0.012), toe, mat=DRIVE, bevel=0.004, subdiv=1)

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "legs_v1.glb"
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_apply=True, export_yup=True)
print("exported", out, "objects:", len(bpy.data.objects))
