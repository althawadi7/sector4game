"""
SciFi guns: pivot at trigger grip, unique VFX/SFX, stable floor physics.
"""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

LOG: list = []

RIFLE = "/Game/XRFramework/Blueprints/BP_Rifle"
CUBE = "/Engine/BasicShapes/Cube"
GRAB_COMP = "/Game/XRFramework/Blueprints/BP_GrabComponent"

# grip = estimated handle in current root space (before pivot shift)
# After shift, mesh moves by -grip so handle sits at origin.
GUNS = {
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol": {
        "sound": "/Game/FreeWeaponSounds/Cue/Handgun/Gunshots/handgun_gunshot_01_Cue.handgun_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_Pistol_MuzzleFlash.FXS_Pistol_MuzzleFlash",
        "grip": (0.0, 70.0, -1.5),
        "mass": 1.2,
        "cube_scale": (0.08, 0.10, 0.12),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1": {
        "sound": "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_gunshot_01_Cue.assault_rifle_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_02.FXS_NS_MuzzleFlash_02",
        "grip": (0.0, 38.0, 0.0),
        "mass": 3.2,
        "cube_scale": (0.09, 0.14, 0.12),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2": {
        "sound": "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_sil_gunshot_01_Cue.assault_rifle_sil_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_03.FXS_NS_MuzzleFlash_03",
        "grip": (0.0, 38.0, 0.0),
        "mass": 3.0,
        "cube_scale": (0.09, 0.14, 0.12),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun": {
        "sound": "/Game/Weapons/AK47/Audio/AK47_Fire_Cue.AK47_Fire_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_01.FXS_NS_ShotBurst_01",
        "grip": (0.0, 8.0, 0.0),
        "mass": 6.5,
        "cube_scale": (0.12, 0.16, 0.14),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun": {
        "sound": "/Game/FreeWeaponSounds/Cue/Shotgun/Gunshots/shotgun_gunshot_01_Cue.shotgun_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_02.FXS_NS_ShotBurst_02",
        "grip": (0.0, 35.0, 1.0),
        "mass": 3.8,
        "cube_scale": (0.09, 0.14, 0.12),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper": {
        "sound": "/Game/Weapons/UMP45/Audio/UMP45_Fire_Cue.UMP45_Fire_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_05.FXS_NS_MuzzleFlash_05",
        "grip": (0.0, 14.0, 1.0),
        "mass": 4.5,
        "cube_scale": (0.09, 0.14, 0.12),
    },
}

# Current muzzle flash spawn point in root space (before grip shift)
OLD_MUZZLE = (-1.4, 92.2, 4.2)
DEFAULT_SOUND = "/Game/XRFramework/Audio/Fire_Cue.Fire_Cue"
DEFAULT_FX = "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_00.FXS_NS_MuzzleFlash_00"


def _subobjs(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = []
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        out.append((n, obj))
    return out


def _set_phys(prim: unreal.PrimitiveComponent, mass: float):
    prim.set_editor_property("hidden_in_game", True)
    try:
        prim.set_editor_property("visible", False)
    except Exception:
        pass
    try:
        prim.set_editor_property("collision_profile_name", "PhysicsActor")
    except Exception:
        pass
    bi = prim.get_editor_property("body_instance")
    bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    try:
        bi.set_editor_property("linear_damping", 3.0)
        bi.set_editor_property("angular_damping", 10.0)
    except Exception:
        pass
    try:
        bi.set_editor_property("b_override_mass", True)
        bi.set_editor_property("mass_in_kg_override", float(mass))
    except Exception:
        try:
            bi.set_editor_property("mass_scale", max(0.5, float(mass) / 3.0))
        except Exception:
            pass
    try:
        # Reduce bounce
        bi.set_editor_property("phys_material_override", None)
    except Exception:
        pass
    prim.set_editor_property("generate_overlap_events", True)
    try:
        # CCD off can reduce jitter with small cubes; keep off
        bi.set_editor_property("b_use_ccd", False)
    except Exception:
        pass


def wire_rifle_fx_defaults():
    try:
        r = ops.set_blueprint_pin_defaults(
            RIFLE,
            [
                {"node": "K2Node_CallFunction_6", "pin": "Sound", "value": DEFAULT_SOUND},
                {"node": "K2Node_CallFunction_5", "pin": "SystemTemplate", "value": DEFAULT_FX},
            ],
            graph_name="XRFireNow",
            compile=False,
            save=False,
        )
        LOG.append({"rifle_pin_defaults": r})
    except Exception as e:
        LOG.append({"rifle_pin_defaults_err": str(e)})

    # Remove accidental PrintString nodes from earlier attempt
    info = ops.inspect_blueprint(RIFLE, "XRFireNow")
    remove = []
    for n in info.get("nodes", []):
        if n.get("name") in ("K2Node_CallFunction_16", "K2Node_CallFunction_17"):
            remove.append(n.get("name"))
    if remove:
        try:
            ops.remove_blueprint_nodes(RIFLE, remove, graph_name="XRFireNow", compile=False, save=False)
        except Exception as e:
            LOG.append({"remove_err": str(e)})

    # Palette variable gets + connect
    for palette, y in (("WeaponFireSound", 240), ("WeaponMuzzleFX", 100)):
        try:
            ops.add_blueprint_nodes(
                RIFLE,
                [{"id": palette, "type": "palette", "palette": palette, "x": -480, "y": y}],
                graph_name="XRFireNow",
                compile=False,
                save=False,
            )
        except Exception as e:
            LOG.append({"palette_err": palette, "e": str(e)})

    bp = unreal.load_asset(RIFLE)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for prop, path in (("WeaponFireSound", DEFAULT_SOUND), ("WeaponMuzzleFX", DEFAULT_FX)):
        try:
            cdo.set_editor_property(prop, unreal.load_asset(path))
        except Exception as e:
            LOG.append({"rifle_cdo_err": prop, "e": str(e)})

    info = ops.inspect_blueprint(RIFLE, "XRFireNow")
    get_snd = get_fx = None
    for n in info.get("nodes", []):
        t = str(n.get("title", ""))
        if "WeaponFireSound" in t:
            get_snd = n.get("name")
        if "WeaponMuzzleFX" in t:
            get_fx = n.get("name")
    links = []
    if get_snd:
        # pin name on get node is usually the variable name
        for pin in ("WeaponFireSound", "ReturnValue", "output"):
            links.append(
                {
                    "from_node": get_snd,
                    "from_pin": pin,
                    "to_node": "K2Node_CallFunction_6",
                    "to_pin": "Sound",
                }
            )
            break
    if get_fx:
        links.append(
            {
                "from_node": get_fx,
                "from_pin": "WeaponMuzzleFX",
                "to_node": "K2Node_CallFunction_5",
                "to_pin": "SystemTemplate",
            }
        )
    if get_snd or get_fx:
        try:
            # try connect with correct pins via inspect
            links = []
            for n in info.get("nodes", []):
                if n.get("name") == get_snd:
                    for p in n.get("pins", []):
                        if "OUTPUT" in str(p.get("direction")) and p.get("name") not in ("execute", "then", "self"):
                            links.append(
                                {
                                    "from_node": get_snd,
                                    "from_pin": p.get("name"),
                                    "to_node": "K2Node_CallFunction_6",
                                    "to_pin": "Sound",
                                }
                            )
                            break
                if n.get("name") == get_fx:
                    for p in n.get("pins", []):
                        if "OUTPUT" in str(p.get("direction")) and p.get("name") not in ("execute", "then", "self"):
                            links.append(
                                {
                                    "from_node": get_fx,
                                    "from_pin": p.get("name"),
                                    "to_node": "K2Node_CallFunction_5",
                                    "to_pin": "SystemTemplate",
                                }
                            )
                            break
            lr = ops.connect_blueprint_pins(RIFLE, links, graph_name="XRFireNow", compile=True, save=True)
            LOG.append({"connect": lr, "links": links})
        except Exception as e:
            LOG.append({"connect_err": str(e)})
            unreal.EditorAssetLibrary.save_asset(RIFLE)
    else:
        unreal.EditorAssetLibrary.save_asset(RIFLE)
        LOG.append({"connect": "using hard pin defaults; child CDO overrides may not apply to pins"})


def configure_gun(path: str, cfg: dict):
    bp = unreal.load_asset(path)
    cube = unreal.load_asset(CUBE)
    sound = unreal.load_asset(cfg["sound"])
    fx = unreal.load_asset(cfg["fx"])
    gx, gy, gz = cfg["grip"]
    csx, csy, csz = cfg["cube_scale"]

    # New muzzle after pivoting grip to origin
    mx, my, mz = OLD_MUZZLE[0] - gx, OLD_MUZZLE[1] - gy, OLD_MUZZLE[2] - gz

    for n, obj in _subobjs(bp):
        if obj is None:
            continue

        if n.startswith("SM_Pistol"):
            if cube:
                obj.set_editor_property("static_mesh", cube)
            obj.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
            obj.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
            obj.set_editor_property("relative_scale3d", unreal.Vector(csx, csy, csz))
            _set_phys(obj, cfg["mass"])

        elif n.startswith("GrabComponent"):
            # Hand snaps here — at weapon pivot / trigger grip
            obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -2.0))
            obj.set_editor_property("relative_rotation", unreal.Rotator(85.0, 90.0, 0.0))

        elif n == "MuzzleLocation" or n.startswith("MuzzleLocation"):
            obj.set_editor_property("relative_location", unreal.Vector(mx, my, mz))
            obj.set_editor_property("relative_rotation", unreal.Rotator(0.0, 90.0, 0.0))

        elif n == "SkeletalMesh":
            loc = obj.get_editor_property("relative_location")
            obj.set_editor_property(
                "relative_location",
                unreal.Vector(loc.x - gx, loc.y - gy, loc.z - gz),
            )

        elif n.startswith("XRMuzzleTip"):
            loc = obj.get_editor_property("relative_location")
            obj.set_editor_property(
                "relative_location",
                unreal.Vector(loc.x - gx, loc.y - gy, loc.z - gz),
            )

        # kits attached to SK follow automatically; empty/orphan scene kits at 0 stay
        if isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            if not n.startswith("SM_Pistol"):
                try:
                    obj.set_editor_property("collision_profile_name", "NoCollision")
                except Exception:
                    pass
                try:
                    bi = obj.get_editor_property("body_instance")
                    bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for prop, asset in (("WeaponFireSound", sound), ("WeaponMuzzleFX", fx)):
        try:
            cdo.set_editor_property(prop, asset)
            LOG.append({"set": path.split("/")[-1], "prop": prop, "ok": True})
        except Exception as e:
            LOG.append({"set": path.split("/")[-1], "prop": prop, "err": str(e)})

    # Per-child pin defaults on inherited XRFireNow (UE often allows this)
    try:
        pr = ops.set_blueprint_pin_defaults(
            path,
            [
                {"node": "K2Node_CallFunction_6", "pin": "Sound", "value": cfg["sound"]},
                {"node": "K2Node_CallFunction_5", "pin": "SystemTemplate", "value": cfg["fx"]},
            ],
            graph_name="XRFireNow",
            compile=True,
            save=True,
        )
        LOG.append({"child_pins": path.split("/")[-1], "r": pr})
    except Exception as e:
        unreal.EditorAssetLibrary.save_asset(path)
        LOG.append({"child_pins_err": path.split("/")[-1], "e": str(e)})

    LOG.append(
        {
            "gun": path.split("/")[-1],
            "grip_shift": cfg["grip"],
            "muzzle": [round(mx, 1), round(my, 1), round(mz, 1)],
            "sound": cfg["sound"].split(".")[-1],
            "fx": cfg["fx"].split(".")[-1],
        }
    )


def fix_grab_component():
    info = ops.inspect_blueprint(GRAB_COMP, "SetPrimitiveCompPhysics")
    updates = []
    for n in info.get("nodes", []):
        if n.get("title") == "SetCollisionProfileName":
            updates.append(
                {"node": n.get("name"), "pin": "InCollisionProfileName", "value": "PhysicsActor"}
            )
    if updates:
        try:
            r = ops.set_blueprint_pin_defaults(
                GRAB_COMP, updates, graph_name="SetPrimitiveCompPhysics", compile=True, save=True
            )
            LOG.append({"grab_profile": r})
        except Exception as e:
            LOG.append({"grab_profile_err": str(e)})


def respawn_level():
    placements = [
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol", 5150.0, -785.0, 105.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1", 5150.0, -695.0, 105.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2", 5150.0, -605.0, 105.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun", 5150.0, -515.0, 105.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun", 5150.0, -425.0, 105.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper", 5150.0, -335.0, 105.0),
    ]
    deleted = 0
    for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if "SciFi" in a.get_class().get_name():
            unreal.EditorLevelLibrary.destroy_actor(a)
            deleted += 1
    created = []
    for path, x, y, z in placements:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            cls, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 0)
        )
        if actor and actor.root_component:
            actor.root_component.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
            created.append(actor.get_class().get_name())
    unreal.EditorLevelLibrary.save_current_level()
    LOG.append({"respawn": {"deleted": deleted, "created": created}})


def main():
    wire_rifle_fx_defaults()
    for path, cfg in GUNS.items():
        try:
            configure_gun(path, cfg)
        except Exception as e:
            LOG.append({"configure_err": path.split("/")[-1], "e": str(e)})
    fix_grab_component()
    respawn_level()
    return {"success": True, "log": LOG}


RESULT = main()
