"""List objects in a .blend: blender -b <file.blend> -P cad/list_blend.py"""
import bpy

for o in bpy.data.objects:
    d = o.dimensions
    extra = ""
    if o.type == "MESH":
        extra = f"verts={len(o.data.vertices)} vgroups={len(o.vertex_groups)} mods={[m.type for m in o.modifiers]}"
    print(f"{o.type:8s} {o.name:40s} dims=({d.x:.2f},{d.y:.2f},{d.z:.2f}) loc=({o.location.x:.2f},{o.location.y:.2f},{o.location.z:.2f}) parent={o.parent.name if o.parent else '-'} {extra}")
for c in bpy.data.collections:
    print("COLLECTION", c.name, [o.name for o in c.objects][:12])
