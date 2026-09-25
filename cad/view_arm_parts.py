"""Lay out all InMoov arm STLs in labelled rows (one row per part folder) and save a .blend to open.
blender -b -P cad/view_arm_parts.py -- C:/Users/conno/Tools/inmoov_arm_cad
then open <folder>/inmoov_arm_parts.blend in Blender."""
import os
import sys

import bpy
from mathutils import Vector

ROOT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else r"C:\Users\conno\Tools\inmoov_arm_cad"
ROWS = ["hand_right/classic", "hand_left/classic", "forearm_right", "forearm_left", "wrist", "bicep",
        "shoulder", "omoplate", "torso_mounts", "_tools"]
MM = 0.001   # STLs are in millimetres; show them in metres

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
mat = bpy.data.materials.new("printed_white")
mat.diffuse_color = (0.92, 0.93, 0.95, 1)

y = 0.0
for row in ROWS:
    folder = os.path.join(ROOT, *row.split("/"))
    if not os.path.isdir(folder):
        continue
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".stl"))
    coll = bpy.data.collections.new(row.replace("/", " / "))
    scene.collection.children.link(coll)
    x, row_depth = 0.0, 0.0
    for f in files:
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=os.path.join(folder, f))
        for o in set(bpy.data.objects) - before:
            for c in o.users_collection:
                c.objects.unlink(o)
            coll.objects.link(o)
            o.scale = (MM, MM, MM)
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            o.location += Vector((x - lo.x, y - lo.y, -lo.z))   # sit on the floor, left-aligned in the row
            o.data.materials.append(mat)
            x += (hi.x - lo.x) + 0.02
            row_depth = max(row_depth, hi.y - lo.y)
    # row label
    bpy.ops.object.text_add(location=(-0.25, y + row_depth / 2, 0))
    t = bpy.context.object
    t.data.body = f"{row}  ({len(files)})"
    t.data.size = 0.04
    t.name = "label " + row
    for c in t.users_collection:
        c.objects.unlink(t)
    coll.objects.link(t)
    y += row_depth + 0.08

bpy.ops.object.light_add(type="SUN", location=(0, 0, 3))
out = os.path.join(ROOT, "inmoov_arm_parts.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("imported", len([o for o in bpy.data.objects if o.type == "MESH"]), "parts ->", out)
