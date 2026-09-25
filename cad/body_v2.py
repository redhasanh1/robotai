"""robotai body v2: armour shells cut from a real human body.

Starting point: Blender Studio's Human Base Meshes (CC0 / public domain), the realistic male body. That gives
true human proportions and surface anatomy, which is what makes InMoov look right. The body is scaled to
1.80 m, split into ARM / BODY regions by a plane running along each arm (so no shell can contain pieces of two
limbs), cut into segments at the joints like InMoov's printed shells, smoothed into armour, given a printed-shell
thickness, and dark mechanical cores sit in the joint gaps. Joint names match the site viewer: each joint is an
Empty named <side>_<joint>, identity rotation, x = pitch, z = roll, y = yaw.

Run:  blender -b -P cad/body_v2.py -- <human_base_meshes_bundle.blend> <out.glb>
"""
import math
import sys

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
BUNDLE, OUT = args[0], args[1]
BODY = "GEO-body_male_realistic"
HEIGHT = 1.80          # metres
SHELL = 0.0045         # printed shell thickness
GAP = 0.012            # joint gap between neighbouring shells

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


# ---------------------------------------------------------------- materials
def material(name, rgb, rough, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


M_SHELL = material("shell", (0.93, 0.94, 0.95), 0.45)
M_DRIVE = material("drive", (0.09, 0.10, 0.12), 0.4, metal=0.2)
M_ACCENT = material("accent", (0.25, 0.55, 1.0), 0.3, emit=2.0)

# ---------------------------------------------------------------- load the body at base resolution, scale to 1.8 m
with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
    dst.objects = [BODY]
body = dst.objects[0]
scene.collection.objects.link(body)
for m in list(body.modifiers):
    body.modifiers.remove(m)           # base cage only: smooth armour, not skin detail
me0 = body.data
co = [v.co.copy() for v in me0.vertices]
raw_h = max(c.z for c in co) - min(c.z for c in co)
S = HEIGHT / raw_h
zmin = min(c.z for c in co)
for v in me0.vertices:
    v.co = Vector((v.co.x * S, v.co.y * S, (v.co.z - zmin) * S))
body.location = (0, 0, 0)
body.rotation_euler = (0, 0, 0)
body.scale = (1, 1, 1)
H = HEIGHT

# ---------------------------------------------------------------- landmarks (fractions of height, measured on the mesh)
HIP_Z = 0.50 * H
CROTCH_Z, KNEE_Z, ANKLE_Z = 0.43 * H, 0.278 * H, 0.05 * H
PELVIS_TOP, ABD_TOP, CHEST_TOP, NECK_TOP = 0.555 * H, 0.665 * H, 0.835 * H, 0.87 * H
ARMPIT_Z = 0.745 * H
HIP_X = 0.053 * H
EYE = lambda sx: Vector((sx * 0.035 * S, -0.12 * S - 0.004, (1.57 - zmin) * S))


def shoulder(sx):
    return Vector((sx * 0.10 * H, 0.0, 0.805 * H))


def arm_axis(sx):
    tip = Vector((sx * 0.26 * H, -0.02 * H, 0.426 * H))
    d = tip - shoulder(sx)
    return d.normalized(), d.length


def arm_out_normal(sx):
    """Normal of the plane that runs along the arm through the armpit, pointing away from the body."""
    d, _ = arm_axis(sx)
    a, b = abs(d.x), -d.z
    return Vector((sx * b, 0, a)).normalized()


ARMPIT = lambda sx: Vector((sx * 0.106 * H, 0, ARMPIT_Z))


def centre(sx, z, band=0.012):
    """Centroid of the leg cross-section on one side at height z (arms excluded by the arm plane)."""
    n = arm_out_normal(sx)
    pts = [v.co for v in body.data.vertices
           if abs(v.co.z - z) < band and v.co.x * sx > 0.01 and (v.co - ARMPIT(sx)).dot(n) < 0]
    return sum(pts, Vector()) / len(pts)


# ---------------------------------------------------------------- cutting
def plane(co, no, gap=GAP / 2):
    """Keep-plane (point, normal) pushed half a joint gap into the kept side so neighbours don't touch."""
    n = Vector(no).normalized()
    return (Vector(co) + n * gap, n)


def arm_side(sx):
    return plane(ARMPIT(sx), arm_out_normal(sx), GAP / 2)


def body_side(sx):
    return plane(ARMPIT(sx), -arm_out_normal(sx), GAP / 2)


def cut_piece(planes):
    me = body.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    for c, n in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=c, plane_no=n, dist=1e-6, clear_inner=True)
    bm.to_mesh(me)
    bm.free()
    return me


def link(o, parent):
    scene.collection.objects.link(o) if o.name not in scene.collection.objects else None
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()


def segment(name, pieces, parent, smooth=8, thickness=SHELL, subdiv=1, mat=M_SHELL, hull=False):
    """Union of cut pieces, softened into armour (smooth, with the cut edges pinned so seams stay thin),
    subdivided, then solidified into a printed shell. hull=True wraps the piece in a smooth closed shell (boots)."""
    bm = bmesh.new()
    for planes in pieces:
        me = cut_piece(planes)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if hull:
        ret = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        bmesh.ops.delete(bm, geom=list(set(ret["geom_interior"] + ret["geom_unused"])), context="VERTS")
        thickness = 0
    me = bpy.data.meshes.new(name)
    bm.verts.ensure_lookup_table()
    inner = [v.index for v in bm.verts if not v.is_boundary]
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    if smooth:
        vg = o.vertex_groups.new(name="inner")
        vg.add(inner, 1.0, "REPLACE")
        s = o.modifiers.new("soften", "SMOOTH")
        s.factor, s.iterations, s.vertex_group = 0.5, smooth, "inner"
    if hull:
        d = o.modifiers.new("round", "SUBSURF")
        d.levels = d.render_levels = 2
    if subdiv:
        d = o.modifiers.new("subdiv", "SUBSURF")
        d.levels = d.render_levels = subdiv
    if thickness:
        t = o.modifiers.new("shell", "SOLIDIFY")
        t.thickness, t.offset, t.use_even_offset, t.use_rim = thickness, -1, True, True
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


# ---------------------------------------------------------------- joints + mechanical cores (built in world space, no object transforms)
def joint(name, parent, at):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.02
    scene.collection.objects.link(e)
    e.location = at
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    bpy.context.view_layer.update()
    return e


def mesh_obj(name, verts, faces, mat, parent, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def cyl(name, a, b, r, parent, mat=M_DRIVE, n=28):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    u = d.cross(X if abs(d.x) < 0.9 else Y).normalized()
    v = d.cross(u)
    ring = [u * math.cos(2 * math.pi * k / n) * r + v * math.sin(2 * math.pi * k / n) * r for k in range(n)]
    verts = [a + p for p in ring] + [b + p for p in ring] + [a, b]
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    faces += [(2 * n, (k + 1) % n, k) for k in range(n)] + [(2 * n + 1, n + k, n + (k + 1) % n) for k in range(n)]
    return mesh_obj(name, verts, faces, mat, parent)


def sphere(name, c, r, parent, mat=M_DRIVE, squash=(1, 1, 1), rings=12, segs=24):
    c = Vector(c)
    verts = [c + Vector((0, 0, r * squash[2]))]
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            verts.append(c + Vector((r * squash[0] * math.sin(th) * math.cos(ph), r * squash[1] * math.sin(th) * math.sin(ph), r * squash[2] * math.cos(th))))
    verts.append(c - Vector((0, 0, r * squash[2])))
    faces = [(0, 1 + j, 1 + (j + 1) % segs) for j in range(segs)]
    for i in range(rings - 2):
        o0, o1 = 1 + i * segs, 1 + (i + 1) * segs
        faces += [(o0 + j, o1 + j, o1 + (j + 1) % segs, o0 + (j + 1) % segs) for j in range(segs)]
    last, base = len(verts) - 1, 1 + (rings - 2) * segs
    faces += [(last, base + (j + 1) % segs, base + j) for j in range(segs)]
    return mesh_obj(name, verts, faces, mat, parent)


def ring_disc(name, c, axis, r_out, r_in, width, parent, mat):
    """A flat annulus (bearing ring / chest light) facing along `axis`."""
    c, axis = Vector(c), Vector(axis).normalized()
    u = axis.cross(X if abs(axis.x) < 0.9 else Y).normalized()
    v = axis.cross(u)
    n = 40
    outer = [u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n) for k in range(n)]
    verts = [c + p * r_out for p in outer] + [c + p * r_in for p in outer]
    verts += [c + axis * width + p * r_out for p in outer] + [c + axis * width + p * r_in for p in outer]
    f = []
    for k in range(n):
        k1 = (k + 1) % n
        f += [(2 * n + k, 2 * n + k1, 3 * n + k1, 3 * n + k), (k, n + k, n + k1, k1),
              (k, k1, 2 * n + k1, 2 * n + k), (n + k, 3 * n + k, 3 * n + k1, n + k1)]
    return mesh_obj(name, verts, f, mat, parent)


root = joint("robot_root", None, (0, 0, HIP_Z))
LB, RB = body_side(1), body_side(-1)    # keep-planes: stay on the body side of each arm

# ---- torso ----
waist = joint("waist_yaw", root, (0, 0, PELVIS_TOP))
spine = joint("spine", waist, (0, 0, ABD_TOP))
segment("pelvis_shell", [[plane((0, 0, CROTCH_Z - 0.02), Z), plane((0, 0, PELVIS_TOP), -Z), LB, RB]], root, smooth=30)
segment("abdomen_shell", [[plane((0, 0, PELVIS_TOP), Z), plane((0, 0, ABD_TOP), -Z), LB, RB]], waist, smooth=14)
segment("chest_shell", [[plane((0, 0, ABD_TOP), Z), plane((0, 0, CHEST_TOP), -Z), LB, RB]], spine, smooth=10)
cyl("spine_core", (0, 0.02, PELVIS_TOP - 0.035), (0, 0.02, ABD_TOP + 0.035), 0.06, waist)
cyl("waist_core", (0, 0.02, CROTCH_Z + 0.03), (0, 0.02, PELVIS_TOP + 0.02), 0.07, root)
ring_disc("chest_light", (0, -0.113, 0.775 * H), (0, -1, 0), 0.022, 0.016, 0.004, spine, M_ACCENT)

# ---- neck + head (above the arms, no arm planes needed) ----
neck_n = Vector((0, -0.35, 1)).normalized()   # low at the chin, high at the back of the skull
neck_yaw = joint("neck_yaw", spine, (0, 0, CHEST_TOP))
neck_pitch = joint("neck_pitch", neck_yaw, (0, 0, NECK_TOP))
segment("neck_shell", [[plane((0, 0, CHEST_TOP), Z), plane((0, 0, NECK_TOP), -neck_n)]], neck_yaw, smooth=10, thickness=0)
cyl("neck_core", (0, 0.01, CHEST_TOP - 0.025), (0, 0.01, NECK_TOP + 0.02), 0.03, neck_yaw)
cap_n = Vector((0, 0.3, 1)).normalized()
cap_at = (0, 0.01, 0.945 * H)
segment("face_shell", [[plane((0, 0, NECK_TOP), neck_n), plane(cap_at, -cap_n)]], neck_pitch, smooth=12)
segment("skull_shell", [[plane(cap_at, cap_n)]], neck_pitch, smooth=10)
for side, sx in (("left", 1), ("right", -1)):
    e = EYE(sx)
    sphere(f"{side}_eye", e, 0.013, neck_pitch)
    ring_disc(f"{side}_eye_iris", e + Vector((0, -0.012, 0)), (0, -1, 0), 0.006, 0.0025, 0.0015, neck_pitch, M_ACCENT)

# ---- arms ----
for side, sx in (("left", 1), ("right", -1)):
    d, L = arm_axis(sx)
    sh = shoulder(sx)
    elbow = sh + d * (0.42 * L)
    wrist = sh + d * (0.76 * L)
    A = arm_side(sx)
    s_pitch = joint(f"{side}_shoulder_pitch", spine, sh)
    s_roll = joint(f"{side}_shoulder_roll", s_pitch, sh)
    s_yaw = joint(f"{side}_shoulder_yaw", s_roll, sh)
    segment(f"{side}_upper_arm_shell", [[A, plane(elbow, -d), plane((0, 0, CHEST_TOP), -Z)]], s_yaw, smooth=10)
    sphere(f"{side}_shoulder_core", sh + Vector((sx * 0.012, 0.005, -0.012)), 0.05, s_pitch)
    ring_disc(f"{side}_shoulder_bearing", sh + Vector((sx * 0.05, 0, -0.01)), (sx, 0, 0), 0.042, 0.03, 0.006, s_pitch, M_DRIVE)
    el = joint(f"{side}_elbow", s_yaw, elbow)
    segment(f"{side}_forearm_shell", [[A, plane(elbow, d), plane(wrist, -d)]], el, smooth=8)
    perp = arm_out_normal(sx).cross(d).normalized()        # elbow hinge axis (front-back of the arm)
    hinge = d.cross(perp).normalized()
    cyl(f"{side}_elbow_core", elbow - hinge * 0.045, elbow + hinge * 0.045, 0.028, el)
    w_yaw = joint(f"{side}_wrist_yaw", el, wrist)
    w_pitch = joint(f"{side}_wrist_pitch", w_yaw, wrist)
    segment(f"{side}_hand_shell", [[A, plane(wrist, d)]], w_pitch, smooth=3, thickness=0.003)
    cyl(f"{side}_wrist_core", wrist - d * 0.018, wrist + d * 0.018, 0.024, w_yaw)

# ---- legs (body side of the arms, split left/right at the midline) ----
for side, sx in (("left", 1), ("right", -1)):
    hip = Vector((sx * HIP_X, 0, HIP_Z))
    knee = centre(sx, KNEE_Z)
    ankle = centre(sx, ANKLE_Z + 0.025)
    print(side, "knee", tuple(round(c, 3) for c in knee), "ankle", tuple(round(c, 3) for c in ankle))
    mid = plane((0, 0, 0), (sx, 0, 0), 0)
    h_yaw = joint(f"{side}_hip_yaw", root, hip)
    h_roll = joint(f"{side}_hip_roll", h_yaw, hip)
    h_pitch = joint(f"{side}_hip_pitch", h_roll, hip)
    segment(f"{side}_thigh_shell", [[plane((0, 0, CROTCH_Z - 0.02), -Z), plane((0, 0, KNEE_Z), Z), mid, LB, RB]], h_pitch, smooth=12)
    sphere(f"{side}_hip_core", hip, 0.05, h_yaw)
    kn = joint(f"{side}_knee", h_pitch, knee)
    segment(f"{side}_shin_shell", [[plane((0, 0, KNEE_Z), -Z), plane((0, 0, ANKLE_Z), Z), mid]], kn, smooth=10)
    cyl(f"{side}_knee_core", knee - X * 0.045, knee + X * 0.045, 0.03, kn)
    a_pitch = joint(f"{side}_ankle_pitch", kn, ankle)
    a_roll = joint(f"{side}_ankle_roll", a_pitch, ankle)
    segment(f"{side}_foot_shell", [[plane((0, 0, ANKLE_Z), -Z), mid]], a_roll, smooth=6, hull=True)
    sphere(f"{side}_ankle_core", ankle, 0.026, a_pitch)

bpy.data.objects.remove(body)

# move everything so the hip root is the world origin (the viewer's convention)
bpy.context.view_layer.update()
root.location = (0, 0, 0)
bpy.context.view_layer.update()
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True)
print("exported", OUT, "objects:", len(bpy.data.objects))
