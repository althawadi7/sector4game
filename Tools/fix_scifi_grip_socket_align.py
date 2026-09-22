"""Fix SciFi VR grip: snap GrabComponent to trigger SOCKET transform (loc+rot).
Barrel along -Z after KitVisual pitch 90; old grab (85,90,0) pointed guns at floor.
"""
import unreal
import json

log = []
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

KIT_ROT = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
# Match trigger socket frame after kit pitch — snap aligns this to the hand
# (replaces broken (85,90,0) which aimed barrels at the floor)
GRAB_ROT = unreal.Rotator(pitch=90.0, yaw=0.0, roll=0.0)
MUZZLE_ROT = unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)
ZERO = unreal.Vector(0, 0, 0)

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


def root_of(a):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name() == "SM_Pistol":
            return c
    return a.root_component


def measure_sockets(a):
    root = root_of(a)
    if not root:
        return {}
    # Ensure kit pitched before measure
    for cac in a.get_components_by_class(unreal.ChildActorComponent):
        if cac.get_name() == "KitVisual":
            cac.set_editor_property("relative_rotation", KIT_ROT)
            cac.set_editor_property("relative_location", ZERO)
            try:
                cac.set_relative_rotation(KIT_ROT, False, False)
            except Exception:
                pass
    if "Pistol" in a.get_actor_label():
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("relative_rotation", KIT_ROT)

    out = {}
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
    for c in bodies:
        try:
            socks = [str(s) for s in c.get_all_socket_names()]
        except Exception:
            continue
        for sn in ("trigger", "muzzle", "barrel", "flash", "magazine"):
            if sn not in socks or sn in out:
                continue
            wloc = c.get_socket_location(sn)
            wrot = c.get_socket_rotation(sn)
            rel = rtm.inverse_transform_location(wloc)
            rrot = rtm.inverse_transform_rotation(wrot)
            out[sn] = {
                "loc": unreal.Vector(float(rel.x), float(rel.y), float(rel.z)),
                "rot": unreal.Rotator(
                    pitch=float(rrot.pitch), yaw=float(rrot.yaw), roll=float(rrot.roll)
                ),
                "body": c.get_name(),
            }
    return out


def gather(bp):
    comps = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj:
            comps[n] = obj
    return comps


results = []

# Fix live actors first (measure from them)
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if "SciFi" not in a.get_class().get_name():
        continue
    lab = a.get_actor_label()
    socks = measure_sockets(a)
    trig = socks.get("trigger")
    muz = socks.get("muzzle") or socks.get("barrel") or socks.get("flash")

    if not trig:
        log.append({"lab": lab, "err": "no trigger", "socks": list(socks)})
        # fallback canonical near grip
        grab_loc = unreal.Vector(-5.0, 0.0, -7.0)
        grab_rot = GRAB_ROT
    else:
        grab_loc = trig["loc"]
        # Use socket rotation so hand frame = trigger frame (barrel aims with socket forward)
        grab_rot = trig["rot"]
        # If socket rot is identity-ish wrong, force (90,0,0)
        if abs(grab_rot.pitch) < 5 and abs(grab_rot.yaw) < 5:
            grab_rot = GRAB_ROT

    # Slight offset into the grip (toward magazine / down the handle from trigger).
    # Magazine is further along -Z; nudge grab from trigger toward magazine by ~30%.
    if trig and "magazine" in socks:
        mag = socks["magazine"]["loc"]
        grab_loc = unreal.Vector(
            trig["loc"].x + (mag.x - trig["loc"].x) * 0.15,
            trig["loc"].y + (mag.y - trig["loc"].y) * 0.15,
            trig["loc"].z + (mag.z - trig["loc"].z) * 0.25,
        )

    for c in a.get_components_by_class(unreal.SceneComponent):
        n = c.get_name()
        if n == "GrabComponentSnap":
            c.set_editor_property("relative_location", grab_loc)
            c.set_editor_property("relative_rotation", grab_rot)
            try:
                c.set_relative_location(grab_loc, False, False)
                c.set_relative_rotation(grab_rot, False, False)
            except Exception:
                pass
            try:
                c.set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        elif n == "KitVisual":
            c.set_editor_property("relative_rotation", KIT_ROT)
            c.set_editor_property("relative_location", ZERO)
        elif n == "SkeletalMesh" and "Pistol" in lab:
            c.set_editor_property("relative_rotation", KIT_ROT)
        elif n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
            if muz:
                c.set_editor_property("relative_location", muz["loc"])
                # Fire along barrel: use muzzle socket rot if sensible, else -90 pitch
                mr = muz["rot"]
                if abs(mr.pitch) < 5 and abs(mr.yaw) < 5:
                    mr = MUZZLE_ROT
                c.set_editor_property("relative_rotation", mr)
        elif n == "SM_Pistol":
            try:
                c.set_simulate_physics(False)
            except Exception:
                pass

    if lab in TABLE:
        x, y, z = TABLE[lab]
        a.set_actor_location(unreal.Vector(x, y, z), False, False)
        a.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)

    # Persist to BP
    path = GUNS.get(lab)
    if path:
        bp = unreal.load_asset(path)
        comps = gather(bp)
        if "GrabComponentSnap" in comps:
            comps["GrabComponentSnap"].set_editor_property("relative_location", grab_loc)
            comps["GrabComponentSnap"].set_editor_property("relative_rotation", grab_rot)
            try:
                comps["GrabComponentSnap"].set_editor_property("bSimulateOnDrop", False)
            except Exception:
                pass
        if "KitVisual" in comps:
            comps["KitVisual"].set_editor_property("relative_rotation", KIT_ROT)
            comps["KitVisual"].set_editor_property("relative_location", ZERO)
        if "SkeletalMesh" in comps and "Pistol" in lab:
            comps["SkeletalMesh"].set_editor_property("relative_rotation", KIT_ROT)
        if muz:
            for kn in ("MuzzleLocation", "XRMuzzleTip", "XRMuzzleTip_0"):
                if kn in comps:
                    comps[kn].set_editor_property("relative_location", muz["loc"])
                    mr = muz["rot"]
                    if abs(mr.pitch) < 5 and abs(mr.yaw) < 5:
                        mr = MUZZLE_ROT
                    comps[kn].set_editor_property("relative_rotation", mr)
        ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(path)
        log.append({"saved": lab, "compiled": bool(ok)})

    results.append(
        {
            "lab": lab,
            "grab_loc": [round(grab_loc.x, 2), round(grab_loc.y, 2), round(grab_loc.z, 2)],
            "grab_rot": [
                round(grab_rot.pitch, 1),
                round(grab_rot.yaw, 1),
                round(grab_rot.roll, 1),
            ],
            "trig": (
                [
                    round(trig["loc"].x, 2),
                    round(trig["loc"].y, 2),
                    round(trig["loc"].z, 2),
                    round(trig["rot"].pitch, 1),
                ]
                if trig
                else None
            ),
            "muz": (
                [
                    round(muz["loc"].x, 2),
                    round(muz["loc"].y, 2),
                    round(muz["loc"].z, 2),
                ]
                if muz
                else None
            ),
        }
    )

unreal.EditorLevelLibrary.save_current_level()
with open(
    r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_grip_socket_align.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump({"log": log, "results": results}, f, indent=2)

RESULT = {"results": results, "log": log}
