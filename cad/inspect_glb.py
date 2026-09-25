"""Debug helper: import a GLB and list objects whose world bounding box is suspiciously long.
blender -b -P cad/inspect_glb.py -- site/models/robot_v1.glb 0.25"""
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
path, limit = args[0], float(args[1]) if len(args) > 1 else 0.25
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = hi - lo
    if max(size) > limit:
        print(f"{o.name:40s} size=({size.x:.3f},{size.y:.3f},{size.z:.3f}) lo=({lo.x:.2f},{lo.y:.2f},{lo.z:.2f}) hi=({hi.x:.2f},{hi.y:.2f},{hi.z:.2f})")
