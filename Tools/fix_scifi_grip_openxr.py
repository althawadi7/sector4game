"""Nuclear grip fix: OpenXR grip forward is -Z.
KitVisual pitch 90 puts barrel on root -Z.
GrabComponentSnap must be Identity rotation so snap aligns barrel with controller forward.
Location = each gun's own trigger socket (unique).
"""
import unreal
import json

log = []
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

KIT_ROT = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
# CRITICAL: identity — do NOT use (85,90,0) or (90,0,0) with pitched kit
GRAB_ROT = unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
ZERO = unreal.Vector(0, 0, 0)

# Restore parent rifle grab to original XR defaults (children override)
PARENT_GRAB_LOC = unreal.Vector(-3.09, 0.0, -9.0)
PARENT_GRAB_ROT = unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0)

GUNS = {
    "BP_XR_SciFi_Pistol": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol",
    "BP_XR_SciFi_AssaultRifle_1": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1",
    "BP_XR_SciFi_AssaultRifle_2": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2",
    "BP_XR_SciFi_MachineGun": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun",
    "BP_XR_SciFi_Shotgun": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun",
    "BP_XR_SciFi_Sniper": "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper",
}
TABLE = {
    "BP_XR_SciFi_Pistol": (5150.0, -785.0, 110.0),
    "BP_XR_SciFi_AssaultRifle_1": (5150.0, -695.0, 110.0),
    "BP_XR_SciFi_AssaultRifle_2": (5150.0, -605.0, 110.0),
    "BP_XR_SciFi_MachineGun": (5150.0, -515.0, 110.0),
    "BP_XR_SciFi_Shotgun": (5150.0, -425.0, 110.0),
    "BP_XR_SciFi_Sniper": (5150.0, -335.0, 110.0),
}


def gather(bp):
    comps = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj:
            comps[n] = obj
    return comps


def measure_trigger_muzzle(a):
    root = None
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            root = c
            break
    if not root:
        return None, None

    # Force kit orientation before measure
    for cac in a.get_components_by_class(unreal.ChildActorComponent):
        if cac.get_name() == "KitVisual":
            cac.set_editor_property("relative_location", ZERO)
            cac.set_editor_property("relative_rotation", KIT_ROT)
            try:
                cac.set_relative_rotation(KIT_ROT, False, False)
                cac.set_relative_location(ZERO, False, False)
            except Exception:
                pass
    if "Pistol" in a.get_actor_label():
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("relative_location", ZERO)
                c.set_editor_property("relative_rotation", KIT_ROT)

    bodies = []
    for cac in a.get_components_by_class(unreal.ChildActorComponent):
        ch = cac.child_actor
        if ch:
            for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.skeletal_mesh:
                    bodies.append(c)
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.skeletal_mesh and c.get_name() == "SkeletalMesh":
            bodies.append(c)

    rtm = root.get_world_transform()
    trig = muz = None
    for c in bodies:
        socks = [str(s) for s in c.get_all_socket_names()]
        if trig is None and "trigger" in socks:
            w = c.get_socket_location("trigger")
            r = rtm.inverse_transform_location(w)
            trig = unreal.Vector(float(r.x), float(r.y), float(r.z))
        if muz is None:
            for sn in ("muzzle", "barrel", "flash"):
                if sn in socks:
                    w = c.get_socket_location(sn)
                    r = rtm.inverse_transform_location(w)
                    muz = unreal.Vector(float(r.x), float(r.y), float(r.z))
                    break
    return trig, muz


# Restore parent BP_Rifle grab (stop poisoning children)
rbp = unreal.load_asset("/Game/XRFramework/Blueprints/BP_Rifle")
rc = gather(rbp)
if "GrabComponentSnap" in rc:
    rc["GrabComponentSnap"].set_editor_property("relative_location", PARENT_GRAB_LOC)
    rc["GrabComponentSnap"].set_editor_property("relative_rotation", PARENT_GRAB_ROT)
unreal.BlueprintEditorLibrary.compile_blueprint(rbp)
unreal.EditorAssetLibrary.save_asset("/Game/XRFramework/Blueprints/BP_Rifle")
log.append("restored BP_Rifle grab defaults")

results = []
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" not in a.get_class().get_name():
        continue
    lab = a.get_actor_label()
    trig, muz = measure_trigger_muzzle(a)
    if trig is None:
        trig = unreal.Vector(-5.0, 0.0, -7.0)
        log.append({"lab": lab, "warn": "fallback trigger"})

    # Grab AT trigger, IDENTITY rotation (OpenXR -Z forward = barrel -Z)
    grab_loc = trig

    for c in a.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            c.set_editor_property("relative_location", grab_loc)
            c.set_editor_property("relative_rotation", GRAB_ROT)
            try:
                c.set_relative_location(grab_loc, False, False)
                c.set_relative_rotation(GRAB_ROT, False, False)
            except Exception:
                pass
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "KitVisual":
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", KIT_ROT)
        elif n == "SkeletalMesh" and "Pistol" in lab:
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", KIT_ROT)
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz is not None:
                c.set_editor_property("relative_location", muz)
                c.set_editor_property("relative_rotation", MUZZLE_ROT)
        elif n == "SM_Pistol":
            try:
                c.set_simulate_physics(False)
            except Exception:
                pass

    if lab in TABLE:
        x, y, z = TABLE[lab]
        a.set_actor_location(unreal.Vector(x, y, z), False, False)
        a.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Write UNIQUE overrides onto each child BP (not shared parent values)
    path = GUNS.get(lab)
    if path:
        bp = unreal.load_asset(path)
        comps = gather(bp)
        if "GrabComponentSnap" in comps:
            comps["GrabComponentSnap"].set_editor_property("relative_location", grab_loc)
            comps["GrabComponentSnap"].set_editor_property("relative_rotation", GRAB_ROT)
            try:
                comps["GrabComponentSnap"].set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        if "KitVisual" in comps:
            comps["KitVisual"].set_editor_property("relative_location", ZERO)
            comps["KitVisual"].set_editor_property("relative_rotation", KIT_ROT)
        if "SkeletalMesh" in comps and "Pistol" in lab:
            comps["SkeletalMesh"].set_editor_property("relative_rotation", KIT_ROT)
        if muz is not None:
            for kn in ("MuzzleLocation", "XRMuzzleTip", "XRMuzzleTip_0"):
                if kn in comps:
                    comps[kn].set_editor_property("relative_location", muz)
                    comps[kn].set_editor_property("relative_rotation", MUZZLE_ROT)
        ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(path)
        log.append({"saved": lab, "ok": bool(ok), "grab": [round(grab_loc.x, 2), round(grab_loc.y, 2), round(grab_loc.z, 2)]})

    # verify readback
    g = None
    k = None
    for c in a.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            g = {
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
        if c.get_name() == "KitVisual":
            k = [
                round(c.relative_rotation.pitch, 1),
                round(c.relative_rotation.yaw, 1),
                round(c.relative_rotation.roll, 1),
            ]
    results.append({"lab": lab, "grab": g, "kit": k, "trig": [round(trig.x, 2), round(trig.y, 2), round(trig.z, 2)]})

# Destroy+respawn so PIE can't use stale duplicated instances
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" in a.get_class().get_name():
        unreal.EditorLevelLibrary.destroy_actor(a)

spawned = []
for lab, path in GUNS.items():
    x, y, z = TABLE[lab]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(x, y, z), unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0)
    )
    if not actor:
        continue
    actor.set_actor_label(lab)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Re-apply on instance (CAC overrides flaky)
    trig, muz = measure_trigger_muzzle(actor)
    if trig is None:
        trig = unreal.Vector(-5.0, 0.0, -7.0)
    for c in actor.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            c.set_editor_property("relative_location", trig)
            c.set_editor_property("relative_rotation", GRAB_ROT)
            try:
                c.set_relative_location(trig, False, False)
                c.set_relative_rotation(GRAB_ROT, False, False)
            except Exception:
                pass
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "KitVisual":
            c.set_editor_property("relative_rotation", KIT_ROT)
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz is not None:
                c.set_editor_property("relative_location", muz)
                c.set_editor_property("relative_rotation", MUZZLE_ROT)
        elif n == "SkeletalMesh" and "Pistol" in lab:
            c.set_editor_property("relative_rotation", KIT_ROT)

    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    g = k = None
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            g = {
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
                g["type"] = str(c.get_editor_property("GrabType"))
            except Exception:
                pass
        if c.get_name() == "KitVisual":
            k = [
                round(c.relative_rotation.pitch, 1),
                round(c.relative_rotation.yaw, 1),
                round(c.relative_rotation.roll, 1),
            ]
    spawned.append({"lab": lab, "grab": g, "kit": k})

unreal.EditorLevelLibrary.save_current_level()
with open(
    r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_openxr_identity.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump({"log": log, "results": results, "spawned": spawned}, f, indent=2)

RESULT = {"log": log, "spawned": spawned}
