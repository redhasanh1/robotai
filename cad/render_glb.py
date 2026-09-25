"""Preview a GLB: front, 3/4 and close-up renders with the workbench engine.
blender -b -P cad/render_glb.py -- <model.glb> <out_prefix>"""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
bpy.context.view_layer.update()
pts = []
for o in bpy.data.objects:
    if o.type == "MESH":
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (lo + hi) / 2
size = max(hi - lo)
print(f"bbox lo={tuple(round(v,2) for v in lo)} hi={tuple(round(v,2) for v in hi)}")

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1200, 1400
world = bpy.data.worlds.new("w")
scene.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"


def shot(name, direction, ortho, target=None):
    t = target or c
    d = Vector(direction).normalized()
    cam.location = t + d * 6
    cam.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    cam.data.ortho_scale = ortho
    scene.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)


shot("front", (0, -1, 0.05), size * 1.15)
shot("threeq", (0.8, -1, 0.25), size * 1.15)
shot("upper", (0.7, -1, 0.3), size * 0.5, Vector((0, 0, hi.z - size * 0.22)))
shot("side", (1, 0, 0.05), size * 1.15)
# posed check: if any shell holds pieces of two limbs, it shows up floating when the limbs move
pose = {"left_shoulder_pitch": (-1.3, 0, 0), "right_shoulder_roll": (0, 0, 0.9), "right_elbow": (-1.2, 0, 0),
        "left_hip_pitch": (-0.9, 0, 0), "left_knee": (1.2, 0, 0), "neck_yaw": (0, 0.6, 0)}
for n, r in pose.items():
    o = bpy.data.objects.get(n)
    if o:
        o.rotation_mode = "XYZ"
        o.rotation_euler = (o.rotation_euler.x + r[0], o.rotation_euler.y + r[2], o.rotation_euler.z + r[1])
bpy.context.view_layer.update()
shot("posed", (0.8, -1, 0.2), size * 1.2)
print("rendered")
