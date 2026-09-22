import unreal
import json

out = []
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    cn = a.get_class().get_name()
    if "SciFi" not in cn:
        continue
    sca = a.get_actor_scale3d()
    item = {
        "actor": str(a.get_actor_label()),
        "class": cn,
        "scale": [round(sca.x, 3), round(sca.y, 3), round(sca.z, 3)],
        "meshes": [],
    }
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        sm = c.skeletal_mesh.get_name() if c.skeletal_mesh else None
        lead = None
        try:
            lp = c.get_editor_property("leader_pose_component")
            lead = lp.get_name() if lp else None
        except Exception:
            lead = None
        loc = c.relative_location
        rot = c.relative_rotation
        sc = c.relative_scale3d
        item["meshes"].append(
            {
                "name": c.get_name(),
                "kind": "SK",
                "mesh": sm,
                "leader": lead,
                "visible": bool(c.is_visible()),
                "loc": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                "rot": [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)],
                "scale": [round(sc.x, 3), round(sc.y, 3), round(sc.z, 3)],
            }
        )
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh.get_name() if c.static_mesh else None
        name = c.get_name()
        keep = bool(sm) or name in ("SM_Pistol", "AmmoScreenMesh") or name.startswith("SM_")
        if not keep:
            continue
        loc = c.relative_location
        rot = c.relative_rotation
        sc = c.relative_scale3d
        item["meshes"].append(
            {
                "name": name,
                "kind": "SM",
                "mesh": sm,
                "visible": bool(c.is_visible()),
                "loc": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                "rot": [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)],
                "scale": [round(sc.x, 3), round(sc.y, 3), round(sc.z, 3)],
            }
        )
    out.append(item)

path = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_live_scifi_meshes.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

RESULT = {"wrote": path, "count": len(out)}
