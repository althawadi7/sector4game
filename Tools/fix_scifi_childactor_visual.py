"""
Nuclear visual fix: hide all hand-assembled kit meshes on XR SciFi guns,
attach the official kit BP as a ChildActorComponent for correct visuals.
Keep XR grab/fire/audio/muzzle on the parent.
"""
import unreal
import json

KIT_BP = {
    "BP_XR_SciFi_Pistol": None,  # filled below
    "BP_XR_SciFi_AssaultRifle_1": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/BP_Rifle/BP_Assault_Rifle",
    "BP_XR_SciFi_AssaultRifle_2": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/BP_AssaultRifle/BP_AssaultRifle",
    "BP_XR_SciFi_MachineGun": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/BP_MachineGun/BP_MachineGun",
    "BP_XR_SciFi_Shotgun": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/BP_Shotgun/BP_Shotgun",
    "BP_XR_SciFi_Sniper": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/BP_Rifle/BP_Sniper_Rifle",
}

ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/Sci-Fi_Weapon_Starter_Pack", recursive=True):
    n = str(a.asset_name)
    if n.startswith("BP_") and "Pistol" in n and "Child" not in n:
        KIT_BP["BP_XR_SciFi_Pistol"] = str(a.package_name)
        break

GUN_PATHS = [
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper",
]

lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
factory = unreal.SubobjectDataFactory  # may not exist

log = []


def get_comps(bp):
    comps = {}
    handles = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj is not None:
            comps[n] = obj
            handles[n] = h
    return comps, handles


def ensure_child_actor(bp, name, kit_path):
    comps, handles = get_comps(bp)
    # Prefer reusing existing
    existing = comps.get(name)
    if existing is None:
        # add via SCS editor subsystem
        try:
            root_handle = None
            for h in sub.k2_gather_subobject_data_for_blueprint(bp):
                data = sub.k2_find_subobject_data_from_handle(h)
                if lib.is_root_component(data):
                    root_handle = h
                    break
            params = unreal.AddNewSubobjectParams()
            params.parent_handle = root_handle
            params.new_class = unreal.ChildActorComponent
            params.blueprint_context = bp
            new_handle, fail_reason = sub.add_new_subobject(params)
            if fail_reason:
                return None, "add_fail:" + str(fail_reason)
            # rename
            try:
                sub.rename_subobject(new_handle, name)
            except Exception:
                pass
            data = sub.k2_find_subobject_data_from_handle(new_handle)
            existing = lib.get_object(data)
        except Exception as e:
            return None, "exc:" + str(e)

    kit_cls = unreal.EditorAssetLibrary.load_blueprint_class(kit_path)
    if existing and kit_cls:
        try:
            existing.set_editor_property("child_actor_class", kit_cls)
        except Exception as e:
            return existing, "set_class_fail:" + str(e)
        try:
            existing.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
            existing.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
            existing.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
        except Exception:
            pass
    return existing, "ok"


for path in GUN_PATHS:
    bp = unreal.load_asset(path)
    short = path.split("/")[-1]
    kit = KIT_BP.get(short)
    entry = {"bp": short, "kit": kit}
    if not kit or not unreal.EditorAssetLibrary.does_asset_exist(kit):
        entry["error"] = "missing kit"
        log.append(entry)
        continue

    comps, _ = get_comps(bp)

    # Reset root transform defaults (critical: no pitch 90, no weird scale)
    root = comps.get("SM_Pistol")
    if root:
        try:
            root.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
            root.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
            root.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
            # keep cube for collision root but invisible
            root.set_editor_property("hidden_in_game", True)
            try:
                root.set_editor_property("static_mesh", unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube"))
            except Exception:
                pass
        except Exception as e:
            entry["root_err"] = str(e)

    # Hide ALL visual SK/SM kit parts (we'll show kit child actor instead)
    keep_visible_names = {
        "WeaponPhysicsBox",
        "MuzzleLocation",
        "GrabComponent",
        "WeaponFireAudio",
        "WeaponMuzzleFXComp",
        "AmmoTextRender",
    }
    hidden = []
    for n, obj in comps.items():
        if isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            if n == "SM_Pistol":
                continue  # root handled
            if n in keep_visible_names:
                continue
            # Clear meshes so they can't ghost
            try:
                if isinstance(obj, unreal.SkeletalMeshComponent):
                    obj.set_editor_property("skeletal_mesh", None)
                else:
                    # don't clear physics box mesh if any
                    if "Physics" in n:
                        continue
                    obj.set_editor_property("static_mesh", None)
            except Exception:
                pass
            try:
                obj.set_editor_property("hidden_in_game", True)
                hidden.append(n)
            except Exception:
                pass

    child, status = ensure_child_actor(bp, "KitVisual", kit)
    entry["child"] = status
    entry["hidden"] = hidden

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    entry["compiled"] = True
    log.append(entry)

# Respawn XR only (clean)
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    lab = a.get_actor_label()
    cn = a.get_class().get_name()
    if lab.startswith("KITREF_") or "SciFi" in cn:
        unreal.EditorLevelLibrary.destroy_actor(a)

ys = {
    "BP_XR_SciFi_Pistol": -785.0,
    "BP_XR_SciFi_AssaultRifle_1": -695.0,
    "BP_XR_SciFi_AssaultRifle_2": -605.0,
    "BP_XR_SciFi_MachineGun": -515.0,
    "BP_XR_SciFi_Shotgun": -425.0,
    "BP_XR_SciFi_Sniper": -335.0,
}
spawned = []
for path in GUN_PATHS:
    short = path.split("/")[-1]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(5150.0, ys[short], 110.0), unreal.Rotator(0, 90, 0)
    )
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    # Ensure root rotation clean on instance
    if actor.root_component:
        actor.root_component.set_relative_rotation(unreal.Rotator(0, 0, 0), False, False)
    # Fix child actor leaders if needed
    for cac in actor.get_components_by_class(unreal.ChildActorComponent):
        child = cac.child_actor
        if not child:
            continue
        sks = child.get_components_by_class(unreal.SkeletalMeshComponent)
        body = None
        for c in sks:
            mn = c.skeletal_mesh.get_name() if c.skeletal_mesh else ""
            if mn in (
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
        if not body:
            for c in sks:
                if c.skeletal_mesh and "Bullet" not in (c.skeletal_mesh.get_name() or ""):
                    body = c
                    break
        if body:
            for c in sks:
                if c is body or not c.skeletal_mesh:
                    continue
                if "Bullet" in c.get_name() or "Empty" in c.get_name():
                    c.set_hidden_in_game(True)
                    continue
                try:
                    c.set_leader_pose_component(body)
                except Exception:
                    pass
    spawned.append(short)

unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    unreal.Vector(5020, -600, 145),
    unreal.Rotator(pitch=-20, yaw=20, roll=0),
)
unreal.EditorLevelLibrary.save_current_level()

out = {"log": log, "spawned": spawned, "kits": KIT_BP}
path_out = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_childactor_fix.json"
with open(path_out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
RESULT = out
