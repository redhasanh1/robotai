"""Render a banner: the InMoov right forearm+hand assembled (left) and exploded (right).

blender -b -P cad/render_hand_hero.py -- <hand_assembly.glb> <out.png>
hand_assembly.glb comes from cad/export_hand_assembly.py. Uses the same explode rule as site/hand3d.js.
"""
import sys

import bpy
from mathutils import Vector

GLB, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def load(offset_x, explode):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=GLB)
    objs = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    bpy.context.view_layer.update()
    centre = lambda o: sum((o.matrix_world @ Vector(c) for c in o.bound_box), Vector()) / 8
    cs = {o: centre(o) for o in objs}
    C = sum(cs.values(), Vector()) / len(cs)
    fore = [c for o, c in cs.items() if "Forearm" in o.name]
    hand = [c for o, c in cs.items() if not any(k in o.name for k in ("Forearm", "Wrist"))]
    axis = (sum(hand, Vector()) / len(hand) - sum(fore, Vector()) / len(fore)).normalized()
    for o, c in cs.items():
        d = c - C
        along = axis * d.dot(axis)
        side = d - along
        if explode:
            o.location += along * 1.1 * explode + side * (5 if "Forearm" in o.name else 2.2) * explode
        o.location.x += offset_x
        o.data.materials.clear()
        m = bpy.data.materials.new(o.name)
        m.diffuse_color = (0.95, 0.84, 0.76, 1) if not any(k in o.name for k in ("Forearm", "Wrist", "Palm")) else \
            ((0.74, 0.81, 0.89, 1) if any(k in o.name for k in ("Palm", "Wrist")) else (0.92, 0.93, 0.95, 1))
        o.data.materials.append(m)
    return objs


a = load(0.0, 0.0)
b = load(0.36, 0.5)
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in a + b for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
mid = (lo + hi) / 2

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.043, 0.051, 0.071)
scene.render.film_transparent = False
scene.render.resolution_x, scene.render.resolution_y = 1600, 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
d = Vector((0.12, -1, 0.08)).normalized()
cam.location = mid + d * 3
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
size = hi - lo
cam.data.ortho_scale = max(size.x * 1.15, size.z * 2.3)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
