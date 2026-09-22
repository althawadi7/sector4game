"""Restore SciFi guns: compile, KitVisual, one SNAP grip at trigger, kit pitch 90, no drop physics."""
import unreal
import json
import sys

sys.path.insert(
    0,
    r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python",
)
import cursor_unreal_bridge.blueprint_ops as bo

log = []
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

GRAB_ROT = unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0)
KIT_ROT = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
ZERO = unreal.Vector(0, 0, 0)
ZERO_ROT = unreal.Rotator(0, 0, 0)

KIT_BP = {
    "BP_XR_SciFi_AssaultRifle_1": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/BP_Rifle/BP_Assault_Rifle",
    "BP_XR_SciFi_AssaultRifle_2": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/BP_AssaultRifle/BP_AssaultRifle",
    "BP_XR_SciFi_MachineGun": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/BP_MachineGun/BP_MachineGun",
    "BP_XR_SciFi_Shotgun": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/BP_Shotgun/BP_Shotgun",
    "BP_XR_SciFi_Sniper": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/BP_Rifle/BP_Sniper_Rifle",
}

GUNS = [
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper",
]

TABLE = {
    "BP_XR_SciFi_Pistol": (5150.0, -785.0, 110.0),
    "BP_XR_SciFi_AssaultRifle_1": (5150.0, -695.0, 110.0),
    "BP_XR_SciFi_AssaultRifle_2": (5150.0, -605.0, 110.0),
    "BP_XR_SciFi_MachineGun": (5150.0, -515.0, 110.0),
    "BP_XR_SciFi_Shotgun": (5150.0, -425.0, 110.0),
    "BP_XR_SciFi_Sniper": (5150.0, -335.0, 110.0),
}


def gather(bp):
    comps, handles = {}, {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj is not None:
            comps[n] = obj
            handles[n] = (h, data)
    return comps, handles


def remove_bad_beginplay_nodes(asset_path):
    """Remove broken Set Relative Rotation / MakeRotator we added if they break compile."""
    bel = bo._bel()
    pl = bo._pinlib()
    bp = bo._load_bp(asset_path)
    editor, _ = bo._editor_for(bp, "")
    nodes = list(editor.list_all_nodes() or [])
    remove = []
    for n in nodes:
        t = bo._node_title(n)
        cls = n.get_class().get_name()
        # Keep Event BeginPlay; remove our Set Relative Rotation + MakeRotator if present
        if t in ("Set Relative Rotation", "MakeRotator") and "CallFunction" in cls:
            # Only remove if connected to Get KitVisual near beginplay area - safer: remove all MakeRotator+SetRelRot that reference KitVisual
            remove.append(n.get_name())
        if t == "Get KitVisual" and n.get_name() in ("K2Node_VariableGet_11",):
            remove.append(n.get_name())
    if remove:
        try:
            bo.remove_blueprint_nodes(asset_path, remove, graph_name="", compile=False, save=False)
            log.append({"removed": asset_path.rsplit("/", 1)[-1], "nodes": remove})
        except Exception as e:
            log.append({"remove_err": str(e), "path": asset_path})


def ensure_kitvisual(bp, short, kit_path):
    comps, handles = gather(bp)
    cac = None
    # Find existing CAC
    for n, obj in list(comps.items()):
        if isinstance(obj, unreal.ChildActorComponent) or "ChildActor" in obj.get_class().get_name():
            cac = obj
            h = handles[n][0]
            if n != "KitVisual":
                try:
                    sub.rename_subobject(h, "KitVisual")
                    log.append({"renamed": short, "from": n})
                except Exception as e:
                    log.append({"rename_err": str(e)})
            break
    if cac is None and kit_path:
        # create
        root_h = None
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            data = sub.k2_find_subobject_data_from_handle(h)
            try:
                if lib.is_root_component(data):
                    root_h = h
                    break
            except Exception:
                pass
        params = unreal.AddNewSubobjectParams()
        params.parent_handle = root_h
        params.new_class = unreal.ChildActorComponent.static_class()
        params.blueprint_context = bp
        new_h, reason = sub.add_new_subobject(params)
        try:
            sub.rename_subobject(new_h, "KitVisual")
        except Exception:
            pass
        data = sub.k2_find_subobject_data_from_handle(new_h)
        cac = lib.get_object(data)
        log.append({"created_kitvisual": short, "reason": str(reason)})

    if cac and kit_path:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(kit_path)
        if cls:
            cac.set_editor_property("child_actor_class", cls)
        cac.set_editor_property("relative_location", ZERO)
        cac.set_editor_property("relative_rotation", KIT_ROT)
    return cac


def hide_frankenstein(bp, short):
    comps, _ = gather(bp)
    keep = {
        "SM_Pistol",
        "GrabComponentSnap",
        "MuzzleLocation",
        "XRMuzzleTip",
        "XRMuzzleTip_0",
        "WeaponFireAudio",
        "WeaponMuzzleFXComp",
        "AmmoTextRender",
        "AmmoScreenMesh",
        "AmmoHUD",
        "Scene",
        "KitVisual",
        "SkeletalMesh",  # pistol body only; hide if rifle
    }
    hidden = []
    for n, obj in comps.items():
        if n in keep and not (n == "SkeletalMesh" and short != "BP_XR_SciFi_Pistol"):
            if n == "SkeletalMesh" and short == "BP_XR_SciFi_Pistol":
                obj.set_editor_property("relative_rotation", KIT_ROT)
                obj.set_editor_property("relative_location", ZERO)
                continue
            continue
        if isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            if n == "SM_Pistol":
                obj.set_editor_property("hidden_in_game", True)
                obj.set_editor_property("relative_location", ZERO)
                obj.set_editor_property("relative_rotation", ZERO_ROT)
                continue
            try:
                if isinstance(obj, unreal.SkeletalMeshComponent):
                    obj.set_editor_property("skeletal_mesh", None)
                obj.set_editor_property("hidden_in_game", True)
                try:
                    obj.set_editor_property("visible", False)
                except Exception:
                    pass
                hidden.append(n)
            except Exception:
                pass
    return hidden


def lock_grab_muzzle(bp, short):
    comps, _ = gather(bp)
    grab = comps.get("GrabComponentSnap")
    if grab:
        # provisional; live measure will refine
        grab.set_editor_property("relative_rotation", GRAB_ROT)
        try:
            grab.set_editor_property("bSimulateOnDrop", False)
        except Exception:
            pass


# --- Fix each BP ---
for path in GUNS:
    short = path.rsplit("/", 1)[-1]
    remove_bad_beginplay_nodes(path)
    bp = unreal.load_asset(path)
    kit = KIT_BP.get(short)
    if kit:
        ensure_kitvisual(bp, short, kit)
    hidden = hide_frankenstein(bp, short)
    lock_grab_muzzle(bp, short)
    ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log.append({"bp": short, "compiled": bool(ok), "hidden": hidden[:12]})

# --- Respawn ---
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" in a.get_class().get_name():
        unreal.EditorLevelLibrary.destroy_actor(a)

results = []
for path in GUNS:
    short = path.rsplit("/", 1)[-1]
    x, y, z = TABLE[short]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(x, y, z), unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0)
    )
    if not actor:
        log.append({"spawn_fail": short})
        continue
    actor.set_actor_label(short)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Force kit pitch
    for cac in actor.get_components_by_class(unreal.ChildActorComponent):
        cac.set_editor_property("relative_location", ZERO)
        cac.set_editor_property("relative_rotation", KIT_ROT)
        try:
            cac.set_relative_rotation(KIT_ROT, False, False)
        except Exception:
            pass

    if short == "BP_XR_SciFi_Pistol":
        for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("relative_rotation", KIT_ROT)

    # Measure trigger / muzzle
    root = None
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            root = c
            break

    def sock(names):
        if not root:
            return None
        bodies = []
        for cac in actor.get_components_by_class(unreal.ChildActorComponent):
            ch = cac.child_actor
            if ch:
                for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
                    if c.skeletal_mesh:
                        bodies.append(c)
        for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.skeletal_mesh:
                bodies.append(c)
        for c in bodies:
            socks = [str(s) for s in c.get_all_socket_names()]
            for sn in names:
                if sn in socks:
                    w = c.get_socket_location(sn)
                    r = root.get_world_transform().inverse_transform_location(w)
                    return unreal.Vector(float(r.x), float(r.y), float(r.z))
        return None

    trig = sock(["trigger"])
    muz = sock(["muzzle", "barrel", "flash"])
    grab_loc = trig if trig is not None else unreal.Vector(-3.09, 0.0, -9.0)

    ncomp = len(list(actor.get_components_by_class(unreal.ActorComponent)))
    for c in actor.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            c.set_editor_property("relative_location", grab_loc)
            c.set_editor_property("relative_rotation", GRAB_ROT)
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz is not None:
                c.set_editor_property("relative_location", muz)
                c.set_editor_property("relative_rotation", MUZZLE_ROT)
        elif n == "SM_Pistol":
            try:
                c.set_simulate_physics(False)
            except Exception:
                pass

    # Persist grab into BP
    bp = unreal.load_asset(path)
    comps, _ = gather(bp)
    if "GrabComponentSnap" in comps:
        comps["GrabComponentSnap"].set_editor_property("relative_location", grab_loc)
        comps["GrabComponentSnap"].set_editor_property("relative_rotation", GRAB_ROT)
        try:
            comps["GrabComponentSnap"].set_editor_property("bSimulateOnDrop", False)
        except Exception:
            pass
    if muz is not None:
        for kn in ("MuzzleLocation", "XRMuzzleTip", "XRMuzzleTip_0"):
            if kn in comps:
                comps[kn].set_editor_property("relative_location", muz)
                comps[kn].set_editor_property("relative_rotation", MUZZLE_ROT)
    if "KitVisual" in comps:
        comps["KitVisual"].set_editor_property("relative_rotation", KIT_ROT)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)

    grab_i = None
    kit_i = None
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            grab_i = {
                "loc": [
                    round(c.relative_location.x, 1),
                    round(c.relative_location.y, 1),
                    round(c.relative_location.z, 1),
                ],
                "rot": [
                    round(c.relative_rotation.pitch, 1),
                    round(c.relative_rotation.yaw, 1),
                    round(c.relative_rotation.roll, 1),
                ],
            }
            try:
                grab_i["sim_drop"] = bool(c.get_editor_property("bSimulateOnDrop"))
            except Exception:
                pass
            try:
                grab_i["type"] = str(c.get_editor_property("GrabType"))
            except Exception:
                pass
        if c.get_name() == "KitVisual":
            kit_i = {
                "rot": [
                    round(c.relative_rotation.pitch, 1),
                    round(c.relative_rotation.yaw, 1),
                    round(c.relative_rotation.roll, 1),
                ],
                "has_child": bool(c.child_actor) if hasattr(c, "child_actor") else None,
            }
    results.append(
        {
            "lab": short,
            "ncomp": ncomp,
            "trig": [round(trig.x, 1), round(trig.y, 1), round(trig.z, 1)] if trig else None,
            "grab": grab_i,
            "kit": kit_i,
        }
    )

unreal.EditorLevelLibrary.save_current_level()
with open(
    r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_restore.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump({"log": log, "results": results}, f, indent=2)

RESULT = {"log": log, "results": results}
