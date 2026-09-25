"""Probe the CC0 human base mesh: landmarks + a front/side preview render.
blender -b -P cad/probe_body.py -- <bundle.blend> <out.png>"""
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
BUNDLE, OUT = args[0], args[1]
NAME = "GEO-body_male_realistic"

bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith(NAME)]
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
body = bpy.data.objects[NAME]
print("mods", [(m.type, getattr(m, "total_levels", None), getattr(m, "levels", None)) for m in body.modifiers])
body.location = (0, 0, 0)
bpy.context.view_layer.update()
vs = [body.matrix_world @ v.co for v in body.data.vertices]
xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
H = max(zs) - min(zs)
print(f"verts={len(vs)} bbox x[{min(xs):.3f},{max(xs):.3f}] y[{min(ys):.3f},{max(ys):.3f}] z[{min(zs):.3f},{max(zs):.3f}] H={H:.3f}")
arm = [v for v in vs if abs(v.x) > 0.17 * 1.0 and v.z > 0.2]
tip = min(arm, key=lambda v: v.z)
wide = max(vs, key=lambda v: abs(v.x))
print(f"fingertip (min z, |x|>0.17): {tuple(round(c,3) for c in tip)}   widest: {tuple(round(c,3) for c in wide)}")
mid = [v for v in vs if abs(v.x) < 0.012 and 0.3 < v.z < 1.2]
crotch = min(mid, key=lambda v: v.z)
print(f"crotch approx: {tuple(round(c,3) for c in crotch)}")
for frac in (0.95, 0.9, 0.87, 0.82, 0.78, 0.72, 0.65, 0.6, 0.55, 0.5, 0.45, 0.3, 0.1, 0.05):
    z = min(zs) + frac * H
    band = [v for v in vs if abs(v.z - z) < 0.01]
    if band:
        print(f"z={z:.2f} ({frac:.2f}H): x[{min(v.x for v in band):.2f},{max(v.x for v in band):.2f}] y[{min(v.y for v in band):.2f},{max(v.y for v in band):.2f}] n={len(band)}")

# preview render: front + side using the workbench engine
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
scene.render.film_transparent = False
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.1
cam.location = (0.0, -6, H / 2)
cam.rotation_euler = (1.5708, 0, 0)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
cam.location = (6, 0, H / 2)
cam.rotation_euler = (1.5708, 0, 1.5708)
scene.render.filepath = OUT.replace(".png", "_side.png")
bpy.ops.render.render(write_still=True)
print("rendered")
