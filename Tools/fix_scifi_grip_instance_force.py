"""Force SciFi grip on LEVEL INSTANCES only (child BP grab overrides do not stick).
KitVisual rot 0; actor table pose (90,90,0); Grab (0,180,0) at trigger.
Also set parent BP_Rifle grab to (0,180,0) + AR1 trigger as default so NEW spawns are closer.
"""
import unreal
import json

ZERO = unreal.Vector(0, 0, 0)
ZERO_ROT = unreal.Rotator(pitch=0, yaw=0, roll=0)
GRAB_ROT = unreal.Rotator(pitch=0.0, yaw=180.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=0.0, yaw=180.0, roll=0.0)
TABLE_ROT = unreal.Rotator(pitch=90.0, yaw=90.0, roll=0.0)

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
# kit-native trigger (no mesh pitch) — from official kit measure
TRIG = {
    "BP_XR_SciFi_Pistol": unreal.Vector(0.0, 0.4, -0.81),  # match working BP_Pistol loc; pistol uses (85,90,0) rot separately
    "BP_XR_SciFi_AssaultRifle_1": unreal.Vector(-6.5, 0.0, 5.18),
    "BP_XR_SciFi_AssaultRifle_2": unreal.Vector(-7.51, 0.0, 6.87),
    "BP_XR_SciFi_MachineGun": unreal.Vector(-8.76, 0.0, 5.3),
    "BP_XR_SciFi_Shotgun": unreal.Vector(-10.94, 0.0, -1.72),
    "BP_XR_SciFi_Sniper": unreal.Vector(-5.0, 0.0, 5.0),
}
MUZ = {
    "BP_XR_SciFi_AssaultRifle_1": unreal.Vector(-62.28, 0.0, 7.21),
    "BP_XR_SciFi_AssaultRifle_2": unreal.Vector(-60.39, 0.0, 12.44),
    "BP_XR_SciFi_MachineGun": unreal.Vector(-128.82, 0.0, -7.18),
    "BP_XR_SciFi_Shotgun": unreal.Vector(-57.89, 2.84, 3.99),
}
PISTOL_GRAB_ROT = unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0)  # working default VR pistol

log = []

# Destroy existing SciFi
for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if "SciFi" in a.get_class().get_name():
        unreal.EditorLevelLibrary.destroy_actor(a)

spawned = []
for lab, path in GUNS.items():
    x, y, z = TABLE[lab]
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(x, y, z), TABLE_ROT
    )
    if not actor:
        spawned.append({"lab": lab, "err": "spawn_fail"})
        continue
    actor.set_actor_label(lab)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(TABLE_ROT, False)

    grab_rot = PISTOL_GRAB_ROT if "Pistol" in lab else GRAB_ROT
    trig = TRIG[lab]
    muz = MUZ.get(lab)

    for c in actor.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            # Force instance override hard
            c.modify()
            c.set_editor_property("relative_location", trig)
            c.set_editor_property("relative_rotation", grab_rot)
            c.set_relative_location(trig, False, False)
            c.set_relative_rotation(grab_rot, False, False)
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "KitVisual":
            c.modify()
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", ZERO_ROT)
            try:
                c.set_relative_location(ZERO, False, False)
                c.set_relative_rotation(ZERO_ROT, False, False)
            except Exception:
                pass
        elif n == "SkeletalMesh":
            c.modify()
            c.set_editor_property("relative_location", ZERO)
            c.set_editor_property("relative_rotation", ZERO_ROT)
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz is not None:
                c.modify()
                c.set_editor_property("relative_location", muz)
                c.set_editor_property("relative_rotation", MUZZLE_ROT)

    # Re-read
    g = k = sk = None
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            g = {
                "loc": [round(c.relative_location.x, 2), round(c.relative_location.y, 2), round(c.relative_location.z, 2)],
                "rot": [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)],
            }
        if c.get_name() == "KitVisual":
            k = [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)]
        if c.get_name() == "SkeletalMesh":
            sk = [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)]
    spawned.append({"lab": lab, "grab": g, "kit": k, "sk": sk, "actor_rot": [90, 90, 0]})

# Fix parent BP_Rifle grab to kit-style so inheritance isn't (85,90) fighting rifles
# Keep pistol-style on parent for non-scifi; SciFi MUST use instance overrides
# Set parent to kit rifle defaults as primary table guns are SciFi now
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
try:
    rbp = unreal.load_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    comps = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(rbp):
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
    if "GrabComponentSnap" in comps:
        # Default for SciFi rifles (most children)
        comps["GrabComponentSnap"].set_editor_property("relative_location", TRIG["BP_XR_SciFi_AssaultRifle_1"])
        comps["GrabComponentSnap"].set_editor_property("relative_rotation", GRAB_ROT)
        try:
            comps["GrabComponentSnap"].set_editor_property("bSimulateOnDrop", False)
        except Exception:
            pass
    unreal.BlueprintEditorLibrary.compile_blueprint(rbp)
    unreal.EditorAssetLibrary.save_asset("/Game/XRFramework/Blueprints/BP_Rifle")
    log.append("parent_set_to_kit_grab_0180")
except Exception as e:
    log.append({"parent_err": str(e)})

# Re-apply instance overrides AFTER parent compile (compile can wipe instances if same class...)
# Re-get actors and force again
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if "SciFi" not in a.get_class().get_name():
        continue
    lab = a.get_actor_label()
    if lab not in TRIG:
        continue
    grab_rot = PISTOL_GRAB_ROT if "Pistol" in lab else GRAB_ROT
    trig = TRIG[lab]
    muz = MUZ.get(lab)
    a.set_actor_rotation(TABLE_ROT, False)
    for c in a.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            c.modify()
            c.set_editor_property("relative_location", trig)
            c.set_editor_property("relative_rotation", grab_rot)
            c.set_relative_location(trig, False, False)
            c.set_relative_rotation(grab_rot, False, False)
        elif n == "KitVisual":
            c.modify()
            c.set_editor_property("relative_rotation", ZERO_ROT)
            c.set_editor_property("relative_location", ZERO)
        elif n == "SkeletalMesh":
            c.set_editor_property("relative_rotation", ZERO_ROT)
        elif (n == "MuzzleLocation" or n.startswith("XRMuzzleTip")) and muz is not None:
            c.set_editor_property("relative_location", muz)
            c.set_editor_property("relative_rotation", MUZZLE_ROT)

final = []
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if "SciFi" not in a.get_class().get_name():
        continue
    lab = a.get_actor_label()
    row = {"lab": lab}
    for c in a.get_components_by_class(unreal.SceneComponent):
        if c.get_name() == "GrabComponentSnap":
            row["grab"] = {
                "loc": [round(c.relative_location.x, 2), round(c.relative_location.y, 2), round(c.relative_location.z, 2)],
                "rot": [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)],
            }
        if c.get_name() == "KitVisual":
            row["kit"] = [round(c.relative_rotation.pitch, 1), round(c.relative_rotation.yaw, 1), round(c.relative_rotation.roll, 1)]
    final.append(row)

unreal.EditorLevelLibrary.save_current_level()
with open(r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_instance_force.json", "w", encoding="utf-8") as f:
    json.dump({"log": log, "spawned": spawned, "final": final}, f, indent=2)
RESULT = {"log": log, "final": final}
