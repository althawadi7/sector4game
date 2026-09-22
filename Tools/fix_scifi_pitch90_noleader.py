"""
Fix Frankenstein guns:
1) Clear Leader Pose (kit accessories use DIFFERENT skeletons — leader pose warps them)
2) Body SkeletalMesh relative pitch = 90 (matches kit BPs)
3) Reparent all visual parts under SkeletalMesh
4) Hide empty/duplicate mag and bullet comps
"""
import unreal
import json

GUNS = [
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper",
]

# Correct sniper body mesh path (not AR2 SK_Rifle)
SNIPER_BODY = "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Rifle"
# probe actual
ar = unreal.AssetRegistryHelpers.get_asset_registry()
sniper_meshes = []
for a in ar.get_assets_by_path("/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle", recursive=True):
    if str(a.asset_class_path.asset_name) == "SkeletalMesh":
        sniper_meshes.append(str(a.package_name))

lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
log = {"sniper_meshes": sniper_meshes, "guns": []}

HIDE_NAME_SUBSTR = ("Bullet", "Empty", "Emty", "Unload", "SkeletalMesh1", "AmmoScreenMesh")


def gather(bp):
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


for path in GUNS:
    bp = unreal.load_asset(path)
    short = path.split("/")[-1]
    comps, handles = gather(bp)
    entry = {"bp": short, "actions": []}

    body = comps.get("SkeletalMesh")
    root = comps.get("SM_Pistol")

    # Fix sniper body mesh if wrong pack
    if short == "BP_XR_SciFi_Sniper" and body:
        # Prefer mesh named like sniper body from sniper folder
        chosen = None
        for p in sniper_meshes:
            name = p.split("/")[-1]
            if name in ("SK_Rifle", "SK_Sniper_Rifle", "SK_Sniper"):
                chosen = p
                break
        if not chosen:
            for p in sniper_meshes:
                if "Magazine" not in p and "Bullet" not in p and "Scope" not in p:
                    chosen = p
                    break
        if chosen:
            mesh = unreal.load_asset(chosen)
            if mesh:
                body.set_editor_property("skeletal_mesh", mesh)
                entry["actions"].append("sniper_body=" + chosen)

    if body:
        body.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
        body.set_editor_property("relative_rotation", unreal.Rotator(90, 0, 0))  # KIT MATCH
        body.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
        body.set_editor_property("hidden_in_game", False)
        try:
            body.set_editor_property("anim_class", None)
            body.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        except Exception as e:
            entry["actions"].append("anim_clear_err:" + str(e))
        entry["actions"].append("body_pitch_90")

    if root:
        root.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        root.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
        root.set_editor_property("hidden_in_game", True)

    # Clear leader pose + identity transforms on accessories; hide junk
    for n, obj in comps.items():
        if not isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            continue
        if n in ("SM_Pistol", "SkeletalMesh"):
            continue

        hide = any(s in n for s in HIDE_NAME_SUBSTR) or n == "SkeletalMesh1"
        if isinstance(obj, unreal.SkeletalMeshComponent):
            try:
                obj.set_editor_property("leader_pose_component", None)
            except Exception:
                pass
            try:
                obj.set_editor_property("anim_class", None)
            except Exception:
                pass
            if hide or not obj.skeletal_mesh:
                try:
                    if n == "SkeletalMesh1" or "Bullet" in n or "Empty" in n or "Emty" in n:
                        obj.set_editor_property("skeletal_mesh", None)
                except Exception:
                    pass
                obj.set_editor_property("hidden_in_game", True)
                entry["actions"].append("hide:" + n)
                continue
        if isinstance(obj, unreal.StaticMeshComponent):
            if hide or n == "AmmoScreenMesh":
                try:
                    obj.set_editor_property("static_mesh", None)
                except Exception:
                    pass
                obj.set_editor_property("hidden_in_game", True)
                entry["actions"].append("hide:" + n)
                continue
            # show kit SM parts
            if obj.static_mesh and n.startswith("SM_"):
                obj.set_editor_property("hidden_in_game", False)

        obj.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
        obj.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        obj.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))

        # Reparent under body via subsystem
        if body and n in handles and "SkeletalMesh" in handles:
            try:
                # attach_subobject(child, parent)
                sub.attach(handles[n], handles["SkeletalMesh"])
                entry["actions"].append("attach:" + n + "->SkeletalMesh")
            except Exception:
                try:
                    sub.attach_subobject(handles[n], handles["SkeletalMesh"])
                    entry["actions"].append("attach2:" + n)
                except Exception as e:
                    entry["actions"].append("attach_fail:" + n + ":" + str(e)[:80])

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    entry["saved"] = True
    log["guns"].append(entry)

# Destroy all kit refs + scifi, respawn XR clean
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    lab = a.get_actor_label()
    cn = a.get_class().get_name()
    if lab.startswith("KITREF_") or "SciFi" in cn:
        unreal.EditorLevelLibrary.destroy_actor(a)

# Also spawn one clean kit AR1 as reference at back
kit_cls = unreal.EditorAssetLibrary.load_blueprint_class(
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/BP_Rifle/BP_Assault_Rifle"
)
kit = unreal.EditorLevelLibrary.spawn_actor_from_class(
    kit_cls, unreal.Vector(5220.0, -695.0, 110.0), unreal.Rotator(0, 90, 0)
)
kit.set_actor_label("KITREF_AR1_CLEAN")
# DO NOT set leader pose on kit
for c in kit.get_components_by_class(unreal.SkeletalMeshComponent):
    try:
        c.set_leader_pose_component(None)
    except Exception:
        pass
    if "Bullet" in c.get_name() or "Emty" in c.get_name() or "Empty" in c.get_name():
        c.set_hidden_in_game(True)

ys = {
    "BP_XR_SciFi_Pistol": -785.0,
    "BP_XR_SciFi_AssaultRifle_1": -695.0,
    "BP_XR_SciFi_AssaultRifle_2": -605.0,
    "BP_XR_SciFi_MachineGun": -515.0,
    "BP_XR_SciFi_Shotgun": -425.0,
    "BP_XR_SciFi_Sniper": -335.0,
}
spawned = []
for path in GUNS:
    short = path.split("/")[-1]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(5150.0, ys[short], 110.0), unreal.Rotator(0, 90, 0)
    )
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    # Runtime enforce: no leaders, body pitch 90, reparent stragglers
    body = None
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() == "SkeletalMesh":
            body = c
            break
    if body:
        body.set_relative_rotation(unreal.Rotator(90, 0, 0), False, False)
        try:
            body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        except Exception:
            pass
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        try:
            c.set_leader_pose_component(None)
        except Exception:
            pass
        if any(s in c.get_name() for s in HIDE_NAME_SUBSTR):
            c.set_hidden_in_game(True)
            continue
        if body and c is not body and c.get_attach_parent() != body:
            try:
                c.attach_to_component(
                    body,
                    unreal.AttachmentTransformRules.KEEP_RELATIVE_TRANSFORM,
                    "",
                )
                c.set_relative_location(unreal.Vector(0, 0, 0), False, False)
                c.set_relative_rotation(unreal.Rotator(0, 0, 0), False, False)
            except Exception:
                pass
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            continue
        if "Ammo" in c.get_name():
            c.set_hidden_in_game(True)
            continue
        if body and c.static_mesh and c.get_attach_parent() != body:
            try:
                c.attach_to_component(
                    body,
                    unreal.AttachmentTransformRules.KEEP_RELATIVE_TRANSFORM,
                    "",
                )
                c.set_relative_location(unreal.Vector(0, 0, 0), False, False)
                c.set_relative_rotation(unreal.Rotator(0, 0, 0), False, False)
            except Exception:
                pass
    spawned.append(short)

unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    unreal.Vector(5020, -600, 145),
    unreal.Rotator(pitch=-18, yaw=15, roll=0),
)
unreal.EditorLevelLibrary.save_current_level()

path_out = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_fix_pitch90_noleader.json"
log["spawned"] = spawned
with open(path_out, "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2)
RESULT = {"wrote": path_out, "spawned": spawned, "gun_count": len(log["guns"])}
