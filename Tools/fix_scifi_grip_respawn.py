import unreal
import json

lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

ZERO = unreal.Vector(0,0,0)
ZERO_ROT = unreal.Rotator(pitch=0, yaw=0, roll=0)
GRAB_ROT = unreal.Rotator(pitch=0.0, yaw=180.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=0.0, yaw=180.0, roll=0.0)
TABLE_ROT = unreal.Rotator(pitch=90.0, yaw=90.0, roll=0.0)
PARENT_GRAB_LOC = unreal.Vector(0.0, 0.4, -0.81)
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
# measured from level pass
MEAS = {
    "BP_XR_SciFi_Pistol": {"trig": (0.0, 0.4, -0.81), "muz": None},
    "BP_XR_SciFi_AssaultRifle_1": {"trig": (-6.5, 0.0, 5.18), "muz": (-62.28, 0.0, 7.21)},
    "BP_XR_SciFi_AssaultRifle_2": {"trig": (-7.51, 0.0, 6.87), "muz": (-60.39, 0.0, 12.44)},
    "BP_XR_SciFi_MachineGun": {"trig": (-8.76, 0.0, 5.3), "muz": (-128.82, 0.0, -7.18)},
    "BP_XR_SciFi_Shotgun": {"trig": (-10.94, 0.0, -1.72), "muz": (-57.89, 2.84, 3.99)},
    "BP_XR_SciFi_Sniper": {"trig": (-5.0, 0.0, 5.0), "muz": None},
}

log = []

def gather(bp):
    comps = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        try:
            data = sub.k2_find_subobject_data_from_handle(h)
            if not data:
                continue
            n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
            obj = lib.get_object(data)
            if obj:
                comps[n] = obj
        except Exception:
            continue
    return comps

def bake_one(lab, path):
    m = MEAS[lab]
    trig = unreal.Vector(*m["trig"])
    muz = unreal.Vector(*m["muz"]) if m["muz"] else None
    bp = unreal.load_asset(path)
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
        comps["KitVisual"].set_editor_property("relative_rotation", ZERO_ROT)
    if "SkeletalMesh" in comps and "Pistol" in lab:
        comps["SkeletalMesh"].set_editor_property("relative_location", ZERO)
        comps["SkeletalMesh"].set_editor_property("relative_rotation", ZERO_ROT)
    if muz is not None:
        for kn in ("MuzzleLocation", "XRMuzzleTip", "XRMuzzleTip_0"):
            if kn in comps:
                comps[kn].set_editor_property("relative_location", muz)
                comps[kn].set_editor_property("relative_rotation", MUZZLE_ROT)
    ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    return bool(ok)

# Bake BPs one by one
for lab, path in GUNS.items():
    try:
        ok = bake_one(lab, path)
        log.append({"bake": lab, "ok": ok})
    except Exception as e:
        log.append({"bake": lab, "err": str(e)})

# Restore parent
try:
    rbp = unreal.load_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    rc = gather(rbp)
    if "GrabComponentSnap" in rc:
        rc["GrabComponentSnap"].set_editor_property("relative_location", PARENT_GRAB_LOC)
        rc["GrabComponentSnap"].set_editor_property("relative_rotation", PARENT_GRAB_ROT)
    unreal.BlueprintEditorLibrary.compile_blueprint(rbp)
    unreal.EditorAssetLibrary.save_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    log.append({"bake": "BP_Rifle_parent", "ok": True})
except Exception as e:
    log.append({"bake": "BP_Rifle_parent", "err": str(e)})

# DESTROY all SciFi actors then respawn fresh (kills instance overrides)
destroyed = 0
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" in a.get_class().get_name():
        unreal.EditorLevelLibrary.destroy_actor(a)
        destroyed += 1

spawned = []
for lab, path in GUNS.items():
    x, y, z = TABLE[lab]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, unreal.Vector(x, y, z), TABLE_ROT)
    if not actor:
        spawned.append({"lab": lab, "err": "spawn_failed"})
        continue
    actor.set_actor_label(lab)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(TABLE_ROT, False)
    m = MEAS[lab]
    trig = unreal.Vector(*m["trig"])
    muz = unreal.Vector(*m["muz"]) if m["muz"] else None
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
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", ZERO_ROT)
        elif n == "SkeletalMesh" and "Pistol" in lab:
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", ZERO_ROT)
        elif (n == "MuzzleLocation" or n.startswith("XRMuzzleTip")) and muz is not None:
            c.set_editor_property("relative_location", muz)
            c.set_editor_property("relative_rotation", MUZZLE_ROT)
    g = k = None
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            g = {
                "loc": [round(c.relative_location.x, 2), round(c.relative_location.y, 2), round(c.relative_location.z, 2)],
                "rot": [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)],
            }
        if c.get_name() == "KitVisual":
            k = [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)]
    spawned.append({"lab": lab, "grab": g, "kit": k})

unreal.EditorLevelLibrary.save_current_level()
with open(r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_respawn.json", "w", encoding="utf-8") as f:
    json.dump({"log": log, "destroyed": destroyed, "spawned": spawned}, f, indent=2)
RESULT = {"log": log, "destroyed": destroyed, "spawned": spawned}
