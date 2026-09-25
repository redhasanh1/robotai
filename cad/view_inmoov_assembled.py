"""Assemble the InMoov upper body in Blender from site/models/inmoov.urdf (the same model the website shows),
with the right arm highlighted, and save it as a .blend you can orbit.

blender -b -P cad/view_inmoov_assembled.py -- <inmoov.urdf> <mesh_cache_dir> <out.blend> [preview.png]
Meshes (Collada) are downloaded once into mesh_cache_dir from Sentience-Robotics/inmoov_urdf (GPL-3.0).
InMoov design by Gael Langevin (CC BY-NC).
"""
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

import bpy
from mathutils import Euler, Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
URDF, CACHE, OUT = args[0], args[1], args[2]
PREVIEW = args[3] if len(args) > 3 else None
os.makedirs(CACHE, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
white = bpy.data.materials.new("printed_white"); white.diffuse_color = (0.92, 0.93, 0.95, 1)
dark = bpy.data.materials.new("dark"); dark.diffuse_color = (0.12, 0.13, 0.15, 1)
arm = bpy.data.materials.new("right_arm"); arm.diffuse_color = (0.30, 0.55, 1.0, 1)


def tf(el):
    o = el.find("origin")
    xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
    rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
    return Matrix.Translation(Vector(xyz)) @ Euler(rpy, "XYZ").to_matrix().to_4x4()


robot = ET.parse(URDF).getroot()
links = {l.get("name"): l for l in robot.findall("link")}
children = {}
for j in robot.findall("joint"):
    children.setdefault(j.find("parent").get("link"), []).append((j.find("child").get("link"), tf(j)))
child_links = {c for lst in children.values() for c, _ in lst}
roots = [n for n in links if n not in child_links]

world = {}
stack = [(r, Matrix.Identity(4)) for r in roots]
while stack:
    name, M = stack.pop()
    world[name] = M
    for c, T in children.get(name, []):
        stack.append((c, M @ T))

ARM_PREFIXES = ("right_shoulder", "right_elbow", "right_wrist", "i01.rightHand")
count = 0
for name, link in links.items():
    if name == "base_node":
        continue                                   # the pole stand
    for vis in link.findall("visual"):
        mesh = vis.find("geometry/mesh")
        if mesh is None:
            continue
        url = mesh.get("filename")
        local = os.path.join(CACHE, url.split("/")[-1])
        if not os.path.exists(local):
            urllib.request.urlretrieve(url, local)
        s = [float(v) for v in mesh.get("scale", "1 1 1").split()]
        before = set(bpy.data.objects)
        bpy.ops.wm.collada_import(filepath=local)
        new = set(bpy.data.objects) - before
        M = world[name] @ tf(vis) @ Matrix.Diagonal((*s, 1))
        mat = arm if name.startswith(ARM_PREFIXES) else None
        for o in new:
            if o.parent is None:
                o.matrix_world = M @ o.matrix_world
            if o.type == "MESH":
                src = o.active_material.diffuse_color if o.active_material else (1, 1, 1, 1)
                o.data.materials.clear()
                o.data.materials.append(mat or (dark if sum(src[:3]) < 0.9 else white))
                count += 1

print("imported", count, "meshes")
bpy.ops.object.light_add(type="SUN", location=(1, -2, 3))
# open framed on the robot (front three-quarter view), nothing selected, solid shading with the part colours
bpy.context.view_layer.update()
for o in bpy.data.objects:
    o.select_set(False)
pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == "MESH" for c in o.bound_box]
centre = sum(pts, Vector()) / len(pts)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type = "SOLID"
            sp.shading.color_type = "MATERIAL"
            sp.clip_start, sp.clip_end = 0.01, 100
            r3d = sp.region_3d
            r3d.view_location = centre
            r3d.view_distance = 2.4
            r3d.view_perspective = "PERSP"
            r3d.view_rotation = Euler((1.35, 0, 0.45), "XYZ").to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=OUT)

if PREVIEW:
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("bbox", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1200
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    c = (lo + hi) / 2
    cam.data.ortho_scale = max(hi - lo) * 1.1
    d = Vector((0.5, -1, 0.15)).normalized()
    cam.location = c + d * 5
    cam.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print("preview", PREVIEW)
