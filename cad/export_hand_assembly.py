"""Export the assembled InMoov right forearm + wrist + hand (from the URDF) as one GLB, one node per part,
so a viewer can pull the parts apart (exploded view).

blender -b -P cad/export_hand_assembly.py -- <inmoov.urdf> <mesh_cache_dir> <out.glb>
Meshes come from Sentience-Robotics/inmoov_urdf (GPL-3.0); InMoov design by Gael Langevin (CC BY-NC).
"""
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

import bpy
from mathutils import Euler, Matrix, Vector

URDF, CACHE, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
KEEP = ("right_elbow_x_link", "right_wrist", "i01.rightHand")
NICE = {"right_elbow_x_link": "Forearm", "right_wrist_z_link": "Wrist rotation", "i01.rightHand.wrist.001_link": "Palm",
        "thumb": "Thumb", "index": "Index finger", "majeure": "Middle finger", "ring": "Ring finger", "pinky": "Pinky"}

bpy.ops.wm.read_factory_settings(use_empty=True)


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
world, stack = {}, [(r, Matrix.Identity(4)) for r in links if r not in child_links]
while stack:
    name, M = stack.pop()
    world[name] = M
    for c, T in children.get(name, []):
        stack.append((c, M @ T))


def label(link):
    if link in NICE:
        return NICE[link]
    low = link.lower()
    for k, v in NICE.items():
        if k in low and not k.startswith(("right", "i01")):
            seg = "".join(ch for ch in link.split(".")[-1].replace("_link", "") if ch.isdigit())
            return v + (f" – segment {seg}" if seg and seg != "0" else (" – base" if seg == "0" else " – segment 1"))
    return link


n = 0
for name, link in links.items():
    if not name.startswith(KEEP):
        continue
    for i, vis in enumerate(link.findall("visual")):
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
        new = [o for o in set(bpy.data.objects) - before]
        M = world[name] @ tf(vis) @ Matrix.Diagonal((*s, 1))
        meshes = [o for o in new if o.type == "MESH"]
        for o in new:
            if o.parent is None:
                o.matrix_world = M @ o.matrix_world
        bpy.context.view_layer.update()
        for o in meshes:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            nm = label(name) + (f" · part {i + 1}" if name == "right_elbow_x_link" else "")
            o.name = f"{nm}|{n}"
            n += 1
        for o in new:
            if o.type != "MESH":
                bpy.data.objects.remove(o, do_unlink=True)

# apply transforms so every node's geometry is in world space; exploded offsets are then computed from centers
for o in bpy.data.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=False, export_apply=True, export_yup=True)
print("exported", n, "parts ->", OUT)
