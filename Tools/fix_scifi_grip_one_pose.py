import unreal
import json

log = []
GRAB_ROT = unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0)
KIT_PITCH = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
ZERO = unreal.Vector(0, 0, 0)
ZERO_ROT = unreal.Rotator(0, 0, 0)

TABLE = [
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol", "BP_XR_SciFi_Pistol", 5150.0, -785.0, 110.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1", "BP_XR_SciFi_AssaultRifle_1", 5150.0, -695.0, 110.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2", "BP_XR_SciFi_AssaultRifle_2", 5150.0, -605.0, 110.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun", "BP_XR_SciFi_MachineGun", 5150.0, -515.0, 110.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun", "BP_XR_SciFi_Shotgun", 5150.0, -425.0, 110.0),
    ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper", "BP_XR_SciFi_Sniper", 5150.0, -335.0, 110.0),
]

lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

KIT_BPS = [
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/BP_Rifle/BP_Assault_Rifle",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/BP_Rifle/BP_AssaultRifle",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/BP_MachineGun/BP_MachineGun",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/BP_Shotgun/BP_Shotgun",
    "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/BP_Sniper_Rifle/BP_Sniper_Rifle",
]


def find_kit_paths():
    found = []
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if "SciFi" not in a.get_class().get_name():
            continue
        for cac in a.get_components_by_class(unreal.ChildActorComponent):
            if cac.get_name() != "KitVisual":
                continue
            try:
                cls = cac.get_editor_property("child_actor_class")
                if cls:
                    found.append(cls.get_path_name().split(".")[0])
            except Exception:
                pass
    return sorted(set(found))


# 1) REVERT all kit BP skeletal mesh rotations to 0 (undo bake)
for kp in find_kit_paths() or KIT_BPS:
    if not unreal.EditorAssetLibrary.does_asset_exist(kp):
        # try search
        continue
    bp = unreal.load_asset(kp)
    if not bp:
        continue
    n = 0
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if not obj:
            continue
        if name.startswith("SK_") or "SkeletalMesh" in name:
            try:
                rot = obj.relative_rotation
                if abs(rot.pitch) > 1 or abs(rot.yaw) > 1 or abs(rot.roll) > 1:
                    obj.set_editor_property("relative_rotation", ZERO_ROT)
                    n += 1
            except Exception:
                pass
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(kp)
    log.append({"reverted_kit": kp.rsplit("/", 1)[-1], "reset": n})


def set_rel(comp, loc=None, rot=None):
    if not comp:
        return False
    ok = True
    if loc is not None:
        try:
            comp.set_editor_property("relative_location", loc)
        except Exception:
            ok = False
        try:
            comp.set_relative_location(loc, False, False)
        except Exception:
            pass
    if rot is not None:
        try:
            comp.set_editor_property("relative_rotation", rot)
        except Exception:
            ok = False
        try:
            comp.set_relative_rotation(rot, False, False)
        except Exception:
            pass
    return ok


def force_kit_pitch(cac):
    """Force KitVisual to local pitch 90 using several methods."""
    set_rel(cac, ZERO, KIT_PITCH)
    # Method: set world transform from parent * local
    try:
        parent = cac.get_attach_parent()
        if parent:
            # Build desired world rotator: parent quat * local quat
            local_q = KIT_PITCH.quaternion()
            parent_q = parent.get_world_transform().rotation
            # unreal.Quat multiply
            try:
                world_q = parent_q * local_q
                world_rot = world_q.rotator()
                cac.set_world_rotation(world_rot, False, False)
            except Exception as e:
                log.append(f"world_rot fail: {e}")
    except Exception as e:
        log.append(f"force_kit {e}")
    # read back
    return [
        round(cac.relative_rotation.pitch, 1),
        round(cac.relative_rotation.yaw, 1),
        round(cac.relative_rotation.roll, 1),
    ]


def socket_rel(actor, names):
    root = None
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            root = c
            break
    if not root:
        return None
    comps = []
    for cac in actor.get_components_by_class(unreal.ChildActorComponent):
        ch = cac.child_actor
        if ch:
            for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.skeletal_mesh:
                    comps.append(c)
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.skeletal_mesh:
            comps.append(c)
    for c in comps:
        try:
            socks = [str(s) for s in c.get_all_socket_names()]
        except Exception:
            continue
        for sn in names:
            if sn in socks:
                w = c.get_socket_location(sn)
                r = root.get_world_transform().inverse_transform_location(w)
                return unreal.Vector(float(r.x), float(r.y), float(r.z))
    return None


# 2) Destroy and respawn clean from BPs
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" in a.get_class().get_name():
        unreal.EditorLevelLibrary.destroy_actor(a)

results = []
for path, lab, x, y, z in TABLE:
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(x, y, z), unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0)
    )
    if not actor:
        log.append({"spawn_fail": lab})
        continue
    actor.set_actor_label(lab)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Pitch visual
    kit_rot_read = None
    for cac in actor.get_components_by_class(unreal.ChildActorComponent):
        if cac.get_name() == "KitVisual":
            kit_rot_read = force_kit_pitch(cac)
    if "Pistol" in lab:
        for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                set_rel(c, ZERO, KIT_PITCH)

    # Grab at trigger AFTER pitch; one SNAP pose
    trig = socket_rel(actor, ["trigger"])
    muz = socket_rel(actor, ["muzzle", "barrel", "flash"])
    grab_loc = trig if trig is not None else unreal.Vector(-3.09, 0.0, -9.0)

    for c in actor.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            set_rel(c, grab_loc, GRAB_ROT)
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz is not None:
                set_rel(c, muz, MUZZLE_ROT)
        elif n == "SM_Pistol":
            try:
                c.set_simulate_physics(False)
            except Exception:
                pass

    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Persist grab onto BP
    bp = unreal.load_asset(path)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if not obj:
            continue
        if n == "GrabComponentSnap":
            obj.set_editor_property("relative_location", grab_loc)
            obj.set_editor_property("relative_rotation", GRAB_ROT)
            try:
                obj.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "KitVisual":
            # keep trying to bake pitch on CAC
            obj.set_editor_property("relative_rotation", KIT_PITCH)
            obj.set_editor_property("relative_location", ZERO)
        elif n == "SkeletalMesh" and "Pistol" in lab:
            obj.set_editor_property("relative_rotation", KIT_PITCH)
            obj.set_editor_property("relative_location", ZERO)
        elif (n == "MuzzleLocation" or n.startswith("XRMuzzleTip")) and muz is not None:
            obj.set_editor_property("relative_location", muz)
            obj.set_editor_property("relative_rotation", MUZZLE_ROT)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)

    grab_info = None
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            grab_info = {
                "loc": [
                    round(c.relative_location.x, 2),
                    round(c.relative_location.y, 2),
                    round(c.relative_location.z, 2),
                ],
                "rot": [
                    round(c.relative_rotation.pitch, 1),
                    round(c.relative_rotation.yaw, 1),
                    round(c.relative_rotation.roll, 1),
                ],
            }
            try:
                grab_info["sim_drop"] = bool(c.get_editor_property("bSimulateOnDrop"))
            except Exception:
                pass
            try:
                grab_info["type"] = str(c.get_editor_property("GrabType"))
            except Exception:
                pass

    results.append(
        {
            "lab": lab,
            "kit_rot": kit_rot_read,
            "trig": [round(trig.x, 2), round(trig.y, 2), round(trig.z, 2)] if trig else None,
            "grab": grab_info,
            "pos": [
                round(actor.get_actor_location().x),
                round(actor.get_actor_location().y),
                round(actor.get_actor_location().z),
            ],
        }
    )

unreal.EditorLevelLibrary.save_current_level()
with open(
    r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_lock_v2.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump({"log": log, "results": results}, f, indent=2)

RESULT = {"results": results, "log": log}
