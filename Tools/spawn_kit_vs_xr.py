import unreal
import json

# Destroy old kit refs + scifi, spawn kit demos as ground truth next to XR guns
KIT = {
    "AR1": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/BP_Rifle/BP_Assault_Rifle",
    "AR2": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/BP_AssaultRifle/BP_AssaultRifle",
    "MG": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/BP_MachineGun/BP_MachineGun",
    "SG": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/BP_Shotgun/BP_Shotgun",
    "SN": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/BP_Rifle/BP_Sniper_Rifle",
}

# find pistol kit
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/Sci-Fi_Weapon_Starter_Pack", recursive=True):
    n = str(a.asset_name)
    if n.startswith("BP_") and "Pistol" in n and "XR" not in n:
        KIT["Pistol"] = str(a.package_name)
        break

# Clear previous test actors
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    lab = a.get_actor_label()
    cn = a.get_class().get_name()
    if lab.startswith("KITREF_") or "SciFi" in cn:
        unreal.EditorLevelLibrary.destroy_actor(a)

spawned = []
# Kit refs on table (front row)
ys = {"Pistol": -785.0, "AR1": -695.0, "AR2": -605.0, "MG": -515.0, "SG": -425.0, "SN": -335.0}
for key, path in KIT.items():
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        spawned.append({"key": key, "missing": path})
        continue
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    y = ys.get(key, -500.0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(5150.0, y, 110.0), unreal.Rotator(0, 90, 0)
    )
    actor.set_actor_label("KITREF_" + key)
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    # Apply leader pose like kit construction often does
    sks = actor.get_components_by_class(unreal.SkeletalMeshComponent)
    body = None
    for c in sks:
        # prefer main body naming
        nm = c.get_name()
        if any(x in nm for x in ("Assault_Rifle", "SK_Rifle", "SK_Shotgun", "SK_Machine", "SK_Pistol", "Sniper")) and "Magazine" not in nm and "Bullet" not in nm:
            if c.skeletal_mesh:
                body = c
                break
    if body is None:
        for c in sks:
            if c.skeletal_mesh and "Bullet" not in c.get_name() and "Magazine" not in c.get_name():
                # largest / first non-accessory heuristic: body often named without SK_ prefix parts
                body = c
                break
    # Better: use component that matches primary mesh names
    for c in sks:
        mesh_name = c.skeletal_mesh.get_name() if c.skeletal_mesh else ""
        if mesh_name in (
            "SK_Rifle_Assault_Rifle",
            "SK_Rifle",
            "SK_Shotgun",
            "SK_MachineGun",
            "SK_Pistol",
            "SK_Sniper_Rifle",
            "SK_Sniper",
        ):
            body = c
            break
    leaders = 0
    if body:
        for c in sks:
            if c is body or not c.skeletal_mesh:
                continue
            if "Bullet" in c.get_name() or "Empty" in c.get_name():
                # hide ammo extras for clean ref
                c.set_hidden_in_game(True)
                continue
            try:
                c.set_leader_pose_component(body)
                leaders += 1
            except Exception:
                pass
    spawned.append({"key": key, "path": path, "body": body.get_name() if body else None, "leaders": leaders, "label": actor.get_actor_label()})

# Also spawn XR guns behind kit refs for comparison
XR = [
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol", -785.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1", -695.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2", -605.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun", -515.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun", -425.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper", -335.0),
]
xr_spawned = []
for path, y in XR:
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(5080.0, y, 110.0), unreal.Rotator(0, 90, 0)
    )
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    # Fix root pitch if baked wrong
    root = actor.root_component
    if root:
        try:
            root.set_relative_rotation(unreal.Rotator(0, 0, 0), False, False)
        except Exception:
            pass
    body = None
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() == "SkeletalMesh" and c.skeletal_mesh:
            body = c
            break
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() == "SkeletalMesh1" or not c.skeletal_mesh:
            try:
                c.set_skeletal_mesh(None)
            except Exception:
                pass
            c.set_hidden_in_game(True)
            continue
        if c is not body and body:
            try:
                c.set_leader_pose_component(body)
            except Exception:
                pass
    xr_spawned.append(actor.get_actor_label())

unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    unreal.Vector(4980, -600, 160),
    unreal.Rotator(pitch=-25, yaw=20, roll=0),
)

out = {"kit": spawned, "xr": xr_spawned, "kit_paths": KIT}
path_out = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_kit_vs_xr_spawn.json"
with open(path_out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
RESULT = out
