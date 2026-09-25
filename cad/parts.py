"""Shared Blender helpers for robotai's parametric robot (Blender Z-up, metres, robot faces -Y, its left is +X).

Conventions every body part follows:
  * Each joint is an Empty named <side>_<joint> (or a bare name for the spine/neck), created in the rest
    pose with identity rotation, so in three.js (after glTF's Y-up conversion) X = pitch, Z = roll, Y = yaw.
  * Materials: "shell" (white printed panels), "drive" (dark actuators/structure), "accent" (glowing blue).
"""
import math

import bpy
from mathutils import Vector


def material(name, rgb, rough, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


SHELL = DRIVE = ACCENT = None  # set by init_scene(); METAL too


def init_scene():
    global SHELL, DRIVE, ACCENT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SHELL = material("shell", (0.93, 0.94, 0.95), 0.5)
    DRIVE = material("drive", (0.08, 0.09, 0.11), 0.4)
    ACCENT = material("accent", (0.25, 0.55, 1.0), 0.3, emit=2.0)
    init_metal()


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


def attach(obj, parent):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def joint(name, parent, head):
    """An Empty at a joint axis, positioned in world space in the rest pose."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.03
    bpy.context.scene.collection.objects.link(e)
    e.location = head
    if parent:
        attach(e, parent)
    bpy.context.view_layer.update()
    return e


AXIS_ROT = {"X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0), "Z": (0, 0, 0)}
AXIS_VEC = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def drum(name, loc, axis, parent, r=0.055, w=0.06, ring=True):
    """Actuator drum: dark cylinder with a light cap ring, axis 'X' | 'Y' | 'Z'."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=w, location=loc)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = AXIS_ROT[axis]
    finish(o, DRIVE, bevel=0.004, subdiv=0)
    attach(o, parent)
    if ring:
        bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.72, minor_radius=r * 0.08,
                                         location=Vector(loc) + Vector(AXIS_VEC[axis]) * (w / 2))
        rg = bpy.context.object
        rg.name = name + "_ring"
        rg.rotation_euler = AXIS_ROT[axis]
        finish(rg, SHELL, bevel=0, subdiv=0)
        attach(rg, parent)
    return o


def limb(name, top, length, r_top, r_bot, depth_scale, bulge, bulge_z, parent, bulge_back=False, mat=None):
    """Tapered limb shell hanging down from `top`, with a soft muscle bulge (front, or back for calves)."""
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r_bot, radius2=r_top, depth=length,
                                    location=(top[0], top[1], top[2] - length / 2))
    o = bpy.context.object
    o.name = name
    o.scale = (1.0, depth_scale, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    zc = top[2] - length * bulge_z
    sign = 1 if bulge_back else -1
    for v in o.data.vertices:
        wz = o.matrix_world @ v.co
        k = math.exp(-((wz.z - zc) / (length * 0.22)) ** 2)
        if v.co.y * sign > 0:
            v.co.y += sign * bulge * k
    finish(o, mat or SHELL, bevel=0, subdiv=2)
    attach(o, parent)
    return o


def box(name, loc, size, parent, mat=None, bevel=0.012, subdiv=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    finish(o, mat or SHELL, bevel=bevel, subdiv=subdiv)
    attach(o, parent)
    return o


def blob(name, loc, radii, parent, mat=None, subdiv=1, segments=32):
    """Ellipsoid."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2, radius=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = radii
    bpy.ops.object.transform_apply(scale=True)
    finish(o, mat or SHELL, bevel=0, subdiv=subdiv)
    attach(o, parent)
    return o


def ring(name, loc, major, minor, axis, parent, mat=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = AXIS_ROT[axis]
    finish(o, mat or SHELL, bevel=0, subdiv=0)
    attach(o, parent)
    return o


def _prism(a, b, section):
    """Vertices/faces of a straight prism from a to b; section = list of (u, v) offsets in the plane normal to a->b.
    Built directly in world coordinates (no object rotation), which avoids transform surprises on export."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    helper = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    u = d.cross(helper).normalized()
    v = d.cross(u).normalized()
    ring_a = [a + u * su + v * sv for su, sv in section]
    ring_b = [b + u * su + v * sv for su, sv in section]
    n = len(section)
    verts = [tuple(p) for p in ring_a + ring_b]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    return verts, faces


def rod(name, a, b, parent, r=0.006, mat=None):
    sec = [(r * math.cos(2 * math.pi * k / 12), r * math.sin(2 * math.pi * k / 12)) for k in range(12)]
    verts, faces = _prism(a, b, sec)
    return mesh_obj(name, verts, faces, mat or DRIVE, parent, subdiv=0, smooth=True)


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True)
    print("exported", path, "objects:", len(bpy.data.objects))


# ---------------------------------------------------------------- detail helpers
METAL = None


def init_metal():
    global METAL
    METAL = material("metal", (0.62, 0.64, 0.68), 0.3)


def mesh_obj(name, verts, faces, mat, parent, subdiv=1, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    finish(o, mat, bevel=0, subdiv=subdiv, smooth=smooth)
    attach(o, parent)
    return o


def loft(name, top, length, profile, parent, rx=1.0, ry=1.0, front=None, back=None, side_shift=0.0,
         rings=28, segs=36, mat=None, subdiv=1):
    """Smooth organic limb shell hanging down from `top`.
    profile(t) -> radius at t (0 = top, 1 = bottom); front(t)/back(t) -> extra bulge on the -Y / +Y side;
    side_shift shifts the whole cross-section along X (e.g. lateral muscle)."""
    verts, faces = [], []
    for i in range(rings + 1):
        t = i / rings
        z = top[2] - t * length
        r = profile(t)
        fb = front(t) if front else 0.0
        bb = back(t) if back else 0.0
        for j in range(segs):
            a = 2 * math.pi * j / segs
            ca, sa = math.cos(a), math.sin(a)
            x = top[0] + side_shift + ca * r * rx
            y = top[1] + sa * r * ry - fb * max(0.0, -sa) ** 1.5 + bb * max(0.0, sa) ** 1.5
            verts.append((x, y, z))
    for i in range(rings):
        for j in range(segs):
            a, b = i * segs + j, i * segs + (j + 1) % segs
            faces.append((a, a + segs, b + segs, b))  # outward-facing winding
    top_c, bot_c = len(verts), len(verts) + 1
    verts += [(top[0] + side_shift, top[1], top[2]), (top[0] + side_shift, top[1], top[2] - length)]
    for j in range(segs):
        faces.append((top_c, j, (j + 1) % segs))
        faces.append((bot_c, rings * segs + (j + 1) % segs, rings * segs + j))
    return mesh_obj(name, verts, faces, mat or SHELL, parent, subdiv=subdiv)


def _orient(o, axis):
    o.rotation_euler = AXIS_ROT[axis]


def gear(name, loc, axis, r, teeth, width, parent, mat=None, hub=True):
    """Spur gear with real teeth, axis 'X' | 'Y' | 'Z'."""
    pts, n = [], teeth * 4
    ro, ri = r, r - max(0.003, r * 0.12)
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = ro if k % 4 in (1, 2) else ri
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    verts = [(x, y, -width / 2) for x, y in pts] + [(x, y, width / 2) for x, y in pts]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    o = mesh_obj(name, verts, faces, mat or METAL, parent, subdiv=0, smooth=False)
    o.location = loc
    _orient(o, axis)
    if hub:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * 0.35, depth=width * 1.4, location=loc)
        h = bpy.context.object
        h.name = name + "_hub"
        _orient(h, axis)
        finish(h, DRIVE, bevel=0, subdiv=0)
        attach(h, parent)
    return o


def bolts(prefix, center, axis, radius, n, parent, r=0.0035, h=0.004):
    """A circle of hex bolt heads on a face (axis = face normal)."""
    c = Vector(center)
    u, v = {"X": ((0, 1, 0), (0, 0, 1)), "Y": ((1, 0, 0), (0, 0, 1)), "Z": ((1, 0, 0), (0, 1, 0))}[axis]
    u, v = Vector(u), Vector(v)
    for k in range(n):
        a = 2 * math.pi * k / n
        p = c + (u * math.cos(a) + v * math.sin(a)) * radius
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=h, location=p)
        b = bpy.context.object
        b.name = f"{prefix}_bolt{k}"
        _orient(b, axis)
        finish(b, METAL, bevel=0, subdiv=0, smooth=False)
        attach(b, parent)


def actuator(name, loc, axis, parent, r=0.055, w=0.06, teeth=24, n_bolts=8):
    """A quasi-direct-drive actuator: dark drum, metal output gear on the outer face, bolt circle, cap ring."""
    drum(name, loc, axis, parent, r=r, w=w, ring=False)
    face = Vector(loc) + Vector(AXIS_VEC[axis]) * (w / 2 + 0.004)
    gear(name + "_gear", face, axis, r * 0.62, teeth, 0.008, parent)
    bolts(name, Vector(loc) + Vector(AXIS_VEC[axis]) * (w / 2), axis, r * 0.85, n_bolts, parent)
    ring(name + "_ring", Vector(loc) - Vector(AXIS_VEC[axis]) * (w / 2), r * 0.9, r * 0.07, axis, parent, mat=METAL)


def rail(name, a, b, parent, w=0.012, d=0.006):
    """Flat metal structural rail between two points (rectangular section)."""
    verts, faces = _prism(a, b, [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)])
    return mesh_obj(name, verts, faces, METAL, parent, subdiv=0, smooth=False)


def servo(name, loc, parent, pulley_axis="Y"):
    """Standard hobby servo with a tendon pulley (the forearm finger servos)."""
    box(name, loc, (0.02, 0.04, 0.038), parent, mat=DRIVE, bevel=0.002, subdiv=0)
    p = Vector(loc) + Vector({"Y": (0, -0.024, 0.008), "X": (0.014, 0, 0.008)}[pulley_axis])
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.012, depth=0.006, location=p)
    pl = bpy.context.object
    pl.name = name + "_pulley"
    _orient(pl, pulley_axis)
    finish(pl, METAL, bevel=0.001, subdiv=0)
    attach(pl, parent)
