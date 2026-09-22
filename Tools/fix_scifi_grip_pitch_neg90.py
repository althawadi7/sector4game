"""Fix SciFi grip: Unreal MotionController forward = +X.
Kit pitch 90 puts barrel on root -Z, so Grab RelRot must be Pitch -90
(so Grab.X aligns with root -Z). Location = each gun trigger.
"""
import unreal
import json

log = []
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

KIT_ROT = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
# Pitch -90: Grab forward (X) = parent -Z = barrel direction
GRAB_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
ZERO = unreal.Vector(0, 0, 0)

# Fallback grabs when sockets collapse (pistol/sniper editor quirk)
FALLBACK = {
    "BP_XR_SciFi_Pistol": unreal.Vector(-5.64, 0.0, -6.49),
    "BP_XR_SciFi_Sniper": unreal.Vector(-5.02, 0.0, -8.67),
}

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


def measure(a, lab):
    root = None
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            root = c
            break
    if not root:
        return FALLBACK.get(lab, unreal.Vector(-5.0, 0.0, -7.0)), None

    for cac in a.get_components_by_class(unreal.ChildActorComponent):
        if cac.get_name() == "KitVisual":
            cac.set_editor_property("relative_location", ZERO)
            cac.set_editor_property("relative_rotation", KIT_ROT)
    if "Pistol" in lab:
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
    root_w = root.get_world_location()
    trig = muz = None
    for c in bodies:
        socks = [str(s) for s in c.get_all_socket_names()]
        if trig is None and "trigger" in socks:
            w = c.get_socket_location("trigger")
            # reject collapsed sockets (same as actor origin)
            if (abs(w.x - root_w.x) + abs(w.y - root_w.y) + abs(w.z - root_w.z)) > 0.5:
                r = rtm.inverse_transform_location(w)
                trig = unreal.Vector(float(r.x), float(r.y), float(r.z))
        if muz is None:
            for sn in ("muzzle", "barrel", "flash", "muzzle_top", "left_muzzle", "right_muzzle"):
                if sn in socks:
                    w = c.get_socket_location(sn)
                    if (abs(w.x - root_w.x) + abs(w.y - root_w.y) + abs(w.z - root_w.z)) > 0.5:
                        r = rtm.inverse_transform_location(w)
                        muz = unreal.Vector(float(r.x), float(r.y), float(r.z))
                        break
    if trig is None:
        trig = FALLBACK.get(lab, unreal.Vector(-5.0, 0.0, -7.0))
        log.append({"lab": lab, "warn": "fallback_trigger"})
    return trig, muz


def apply_to_actor(a, lab, trig, muz):
    for c in a.get_components_by_class(unreal.SceneComponent):
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
            try:
                # ensure SNAP
                gt = c.get_editor_property("GrabType")
                # leave as-is if enum works
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


def apply_to_bp(path, lab, trig, muz):
    bp = unreal.load_asset(path)
    if not bp:
        return False
    comps = gather(bp)
    if "GrabComponentSnap" in comps:
        comps["GrabComponentSnap"].set_editor_property("relative_location", trig)
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
        comps["SkeletalMesh"].set_editor_property("relative_location", ZERO)
    if muz is not None:
        for kn in ("MuzzleLocation", "XRMuzzleTip", "XRMuzzleTip_0"):
            if kn in comps:
                comps[kn].set_editor_property("relative_location", muz)
                comps[kn].set_editor_property("relative_rotation", MUZZLE_ROT)
    ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    return bool(ok)


spawned = []
# Update existing level actors in place (no destroy — avoid null instance crashes)
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" not in a.get_class().get_name():
        continue
    lab = a.get_actor_label()
    if lab not in GUNS:
        continue
    trig, muz = measure(a, lab)
    apply_to_actor(a, lab, trig, muz)
    if lab in TABLE:
        x, y, z = TABLE[lab]
        a.set_actor_location(unreal.Vector(x, y, z), False, False)
        a.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)
    ok = apply_to_bp(GUNS[lab], lab, trig, muz)

    g = k = None
    for c in a.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            g = {
                "loc": [round(c.relative_location.x, 2), round(c.relative_location.y, 2), round(c.relative_location.z, 2)],
                "rot": [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)],
            }
        if c.get_name() == "KitVisual":
            k = [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)]
    spawned.append({
        "lab": lab,
        "ok": ok,
        "grab": g,
        "kit": k,
        "trig": [round(trig.x, 2), round(trig.y, 2), round(trig.z, 2)],
        "muz": [round(muz.x, 2), round(muz.y, 2), round(muz.z, 2)] if muz else None,
    })

# Restore parent BP_Rifle grab so non-scifi children stay OK
try:
    rbp = unreal.load_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    rc = gather(rbp)
    if "GrabComponentSnap" in rc:
        rc["GrabComponentSnap"].set_editor_property("relative_location", unreal.Vector(-3.09, 0.0, -9.0))
        rc["GrabComponentSnap"].set_editor_property("relative_rotation", unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0))
    unreal.BlueprintEditorLibrary.compile_blueprint(rbp)
    unreal.EditorAssetLibrary.save_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    log.append("restored_parent_grab")
except Exception as e:
    log.append({"parent_err": str(e)})

unreal.EditorLevelLibrary.save_current_level()
path = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_pitch_neg90.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump({"log": log, "spawned": spawned}, f, indent=2)
RESULT = {"log": log, "spawned": spawned}
