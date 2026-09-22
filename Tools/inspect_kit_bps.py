import unreal
import json

# Find kit demo BPs and inspect their components
ar = unreal.AssetRegistryHelpers.get_asset_registry()
paths = [
    "/Game/Sci-Fi_Weapon_Starter_Pack",
    "/Game/SciFi_Weapon_Starter_Pack",
    "/Game",
]
found = []
for base in ["/Game/Sci-Fi_Weapon_Starter_Pack", "/Game"]:
    try:
        assets = ar.get_assets_by_path(base, recursive=True)
    except Exception:
        continue
    for a in assets:
        name = str(a.asset_name)
        if "BP_" in name and any(k in name for k in ("Assault", "Rifle", "Sniper", "Shotgun", "Machine", "Pistol", "Gun")):
            found.append(str(a.package_name))

found = sorted(set(found))[:80]

# Prefer known kit BP names
want = []
for p in found:
    low = p.lower()
    if "sci" in low or "weapon" in low or "starter" in low:
        want.append(p)

out = {"all_candidates": found[:40], "kitish": want[:40], "inspect": []}

# Inspect a few known / found BPs
inspect_paths = []
for p in found:
    n = p.split("/")[-1]
    if n in (
        "BP_Assault_Rifle",
        "BP_AssaultRifle",
        "BP_Rifle_Assault",
        "BP_Machine_Gun",
        "BP_Shotgun",
        "BP_Sniper",
        "BP_Pistol",
        "BP_Assault_Rifle_1",
        "BP_Assault_Rifle_2",
    ) or ("Assault" in n and "XR" not in n):
        inspect_paths.append(p)

# Also try direct loads
direct = [
    "/Game/Sci-Fi_Weapon_Starter_Pack/Blueprints/BP_Assault_Rifle",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Blueprints/Weapons/BP_Assault_Rifle",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Blueprints/BP_AssaultRifle",
]
for d in direct:
    if unreal.EditorAssetLibrary.does_asset_exist(d):
        inspect_paths.append(d)

inspect_paths = sorted(set(inspect_paths))[:12]

lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

for path in inspect_paths:
    bp = unreal.load_asset(path)
    if not bp:
        continue
    comps = []
    try:
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    except Exception as e:
        out["inspect"].append({"path": path, "error": str(e)})
        continue
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj is None:
            continue
        entry = {"name": n, "class": obj.get_class().get_name()}
        if isinstance(obj, unreal.SkeletalMeshComponent):
            entry["mesh"] = obj.skeletal_mesh.get_name() if obj.skeletal_mesh else None
            try:
                lp = obj.get_editor_property("leader_pose_component")
                entry["leader"] = lp.get_name() if lp else None
            except Exception:
                entry["leader"] = None
            loc = obj.relative_location
            rot = obj.relative_rotation
            entry["loc"] = [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)]
            entry["rot"] = [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)]
        elif isinstance(obj, unreal.StaticMeshComponent):
            entry["mesh"] = obj.static_mesh.get_name() if obj.static_mesh else None
            loc = obj.relative_location
            rot = obj.relative_rotation
            entry["loc"] = [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)]
            entry["rot"] = [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)]
        else:
            continue
        comps.append(entry)
    out["inspect"].append({"path": path, "comps": comps})

path_out = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_kit_bp_inspect.json"
with open(path_out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
RESULT = {"wrote": path_out, "n_inspect": len(out["inspect"]), "n_found": len(found)}
