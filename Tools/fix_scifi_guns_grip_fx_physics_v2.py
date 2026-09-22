"""
SciFi guns v2: trigger grip, muzzle-attached unique FX/SFX, stable floor physics.
"""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

LOG: list = []

RIFLE = "/Game/XRFramework/Blueprints/BP_Rifle"
CUBE = "/Engine/BasicShapes/Cube"
PHYS_MAT = "/Game/XRFramework/Physics/PM_WeaponDrop"
GRAB = "/Game/XRFramework/Blueprints/BP_GrabComponent"

GUNS = {
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol": {
        "sound": "/Game/FreeWeaponSounds/Cue/Handgun/Gunshots/handgun_gunshot_01_Cue.handgun_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_Pistol_MuzzleFlash.FXS_Pistol_MuzzleFlash",
        "mass": 1.2,
        "grip_along": 0.22,  # 0=stock .. 1=muzzle
        "grip_drop": 6.0,
        "box_yz": (0.10, 0.14),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1": {
        "sound": "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_gunshot_01_Cue.assault_rifle_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_02.FXS_NS_MuzzleFlash_02",
        "mass": 3.2,
        "grip_along": 0.28,
        "grip_drop": 5.5,
        "box_yz": (0.11, 0.14),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2": {
        "sound": "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_sil_gunshot_01_Cue.assault_rifle_sil_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_03.FXS_NS_MuzzleFlash_03",
        "mass": 3.0,
        "grip_along": 0.28,
        "grip_drop": 5.5,
        "box_yz": (0.11, 0.14),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun": {
        "sound": "/Game/Weapons/AK47/Audio/AK47_Fire_Cue.AK47_Fire_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_01.FXS_NS_ShotBurst_01",
        "mass": 6.5,
        "grip_along": 0.30,
        "grip_drop": 6.0,
        "box_yz": (0.14, 0.16),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun": {
        "sound": "/Game/FreeWeaponSounds/Cue/Shotgun/Gunshots/shotgun_gunshot_01_Cue.shotgun_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_02.FXS_NS_ShotBurst_02",
        "mass": 3.8,
        "grip_along": 0.26,
        "grip_drop": 5.0,
        "box_yz": (0.11, 0.13),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper": {
        "sound": "/Game/Weapons/UMP45/Audio/UMP45_Fire_Cue.UMP45_Fire_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_05.FXS_NS_MuzzleFlash_05",
        "mass": 4.5,
        "grip_along": 0.27,
        "grip_drop": 5.0,
        "box_yz": (0.11, 0.13),
    },
}


def _subobjs(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = []
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        out.append((n, obj, h, data))
    return out


def _ensure_phys_mat():
    if unreal.EditorAssetLibrary.does_asset_exist(PHYS_MAT):
        return unreal.load_asset(PHYS_MAT)
    # create simple physical material: no bounce, high friction
    try:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        factory = unreal.PhysicalMaterialFactoryNew()
        folder = "/Game/XRFramework/Physics"
        if not unreal.EditorAssetLibrary.does_directory_exist(folder):
            unreal.EditorAssetLibrary.make_directory(folder)
        mat = tools.create_asset("PM_WeaponDrop", folder, unreal.PhysicalMaterial, factory)
        if mat:
            mat.set_editor_property("restitution", 0.0)
            mat.set_editor_property("friction", 1.2)
            try:
                mat.set_editor_property("density", 1.0)
            except Exception:
                pass
            unreal.EditorAssetLibrary.save_asset(PHYS_MAT)
            LOG.append({"phys_mat": "created"})
            return mat
    except Exception as e:
        LOG.append({"phys_mat_err": str(e)})
    return None


def _set_phys(prim, mass: float, phys_mat):
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
        bi.set_editor_property("linear_damping", 6.0)
        bi.set_editor_property("angular_damping", 30.0)
    except Exception:
        pass
    try:
        bi.set_editor_property("b_override_mass", True)
        bi.set_editor_property("mass_in_kg_override", float(mass))
    except Exception:
        pass
    try:
        bi.set_editor_property("b_use_ccd", True)
    except Exception:
        pass
    if phys_mat:
        try:
            bi.set_editor_property("phys_material_override", phys_mat)
        except Exception:
            try:
                prim.set_editor_property("phys_material_override", phys_mat)
            except Exception as e:
                LOG.append({"pm_assign_err": str(e)})
    prim.set_editor_property("generate_overlap_events", True)
    try:
        # Keep COM near geometric center of long box
        bi.set_editor_property("b_inertia_conditioning", True)
    except Exception:
        pass


def _mesh_to_root(sk, lx, ly, lz):
    loc = sk.relative_location
    scale = sk.relative_scale3d
    x, y, z = lx * scale.x, ly * scale.y, lz * scale.z
    # SK yaw -90: (x,y,z) -> (y, -x, z)
    return unreal.Vector(loc.x + y, loc.y - x, loc.z + z)


def _estimate_stock_and_tip(sk, tip_comp):
    mesh = sk.skeletal_mesh
    b = mesh.get_imported_bounds() if hasattr(mesh, "get_imported_bounds") else mesh.get_bounds()
    ox, oy, oz = b.origin.x, b.origin.y, b.origin.z
    ex = b.box_extent.x
    # After yaw -90, mesh minX (ox-ex) -> tip side; mesh maxX (ox+ex) -> stock
    tip_from_mesh = _mesh_to_root(sk, ox - ex, oy, oz)
    stock_from_mesh = _mesh_to_root(sk, ox + ex, oy, oz)
    tip = tip_comp.relative_location if tip_comp else tip_from_mesh
    stock_y = stock_from_mesh.y
    tip_y = tip.y
    tip_z = tip.z
    return stock_y, tip_y, tip_z, tip


def configure_gun(path: str, cfg: dict, phys_mat):
    bp = unreal.load_asset(path)
    cube = unreal.load_asset(CUBE)
    sound = unreal.load_asset(cfg["sound"])
    fx = unreal.load_asset(cfg["fx"])

    sk = tip = muzzle = grab = root_mesh = audio = niag = None
    for n, obj, h, data in _subobjs(bp):
        if obj is None:
            continue
        if n == "SkeletalMesh" and isinstance(obj, unreal.SkeletalMeshComponent):
            sk = obj
        elif n == "XRMuzzleTip_0":
            tip = obj
        elif n.startswith("MuzzleLocation") and muzzle is None:
            muzzle = obj
        elif n.startswith("GrabComponent"):
            grab = obj
        elif n.startswith("SM_Pistol"):
            root_mesh = obj
        elif n == "WeaponFireAudio":
            audio = obj
        elif n == "WeaponMuzzleFXComp":
            niag = obj

    if not sk or not sk.skeletal_mesh:
        LOG.append({"err": path, "msg": "no skeletal mesh"})
        return

    stock_y, tip_y, tip_z, tip_loc = _estimate_stock_and_tip(sk, tip)
    along = float(cfg["grip_along"])
    grip_y = stock_y + (tip_y - stock_y) * along
    grip_z = tip_z - float(cfg["grip_drop"])
    grip = unreal.Vector(0.0, grip_y, grip_z)

    length = abs(tip_y - stock_y)
    # BasicShapes Cube = 100uu. Grab/Muzzle are children of SM_Pistol, so their
    # relative coords are scaled by this — compensate when setting them.
    box_y = max(0.28, (length + 12.0) / 100.0)
    bx, bz = cfg["box_yz"]
    sx, sy, sz = float(bx), float(box_y), float(bz)

    if root_mesh:
        if cube:
            root_mesh.set_editor_property("static_mesh", cube)
        root_mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 0.0))
        root_mesh.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        root_mesh.set_editor_property("relative_scale3d", unreal.Vector(sx, sy, sz))
        _set_phys(root_mesh, cfg["mass"], phys_mat)

    def under_root_mesh(v: unreal.Vector) -> unreal.Vector:
        # Convert actor/root-space offset into SM_Pistol local (pre-scale) space
        return unreal.Vector(v.x / sx, v.y / sy, v.z / sz)

    if grab:
        grab.set_editor_property("relative_location", under_root_mesh(grip))
        grab.set_editor_property("relative_rotation", unreal.Rotator(85.0, 90.0, 0.0))
        try:
            grab.set_editor_property("absolute_scale", True)
        except Exception:
            try:
                grab.set_editor_property("bAbsoluteScale", True)
            except Exception:
                pass
        try:
            grab.set_editor_property("bSimulateOnDrop", True)
        except Exception:
            pass

    if muzzle:
        muzzle.set_editor_property("relative_location", under_root_mesh(tip_loc))
        muzzle.set_editor_property("relative_rotation", unreal.Rotator(0.0, 90.0, 0.0))
        try:
            muzzle.set_editor_property("absolute_scale", True)
        except Exception:
            try:
                muzzle.set_editor_property("bAbsoluteScale", True)
            except Exception:
                pass

    # Attach FX/SFX at muzzle (relative 0) by matching muzzle world-ish relative coords
    if audio:
        audio.set_editor_property("relative_location", unreal.Vector(tip_loc.x, tip_loc.y, tip_loc.z))
        audio.set_editor_property("sound", sound)
        audio.set_editor_property("auto_activate", False)
        try:
            audio.set_editor_property("component_tags", ["WeaponFire"])
        except Exception:
            pass
    if niag:
        niag.set_editor_property("relative_location", unreal.Vector(tip_loc.x, tip_loc.y, tip_loc.z))
        niag.set_editor_property("relative_rotation", unreal.Rotator(0.0, 90.0, 0.0))
        try:
            niag.set_editor_property("asset", fx)
        except Exception:
            try:
                niag.set_editor_property("NiagaraSystemAsset", fx)
            except Exception:
                pass
        niag.set_editor_property("auto_activate", False)
        try:
            niag.set_editor_property("component_tags", ["WeaponMuzzle"])
        except Exception:
            pass

    # Visuals: no collision
    for n, obj, h, data in _subobjs(bp):
        if obj is None or n.startswith("SM_Pistol"):
            continue
        if isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
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
    unreal.EditorAssetLibrary.save_asset(path)
    LOG.append(
        {
            "gun": path.split("/")[-1],
            "grip": [round(grip.x, 1), round(grip.y, 1), round(grip.z, 1)],
            "tip": [round(tip_loc.x, 1), round(tip_loc.y, 1), round(tip_loc.z, 1)],
            "box_y": round(box_y, 3),
            "sound": cfg["sound"].split(".")[-1],
            "fx": cfg["fx"].split(".")[-1],
        }
    )


def ensure_rifle_default_fx():
    """Base rifle also gets tagged comps so XRFireNow never runs empty."""
    bp = unreal.load_asset(RIFLE)
    has_audio = has_fx = False
    for n, obj, h, data in _subobjs(bp):
        if n == "WeaponFireAudio":
            has_audio = True
        if n == "WeaponMuzzleFXComp":
            has_fx = True
    # Components already on children; parent may lack them — skip add if API hard
    LOG.append({"rifle_has_audio": has_audio, "rifle_has_fx": has_fx})


def damp_on_drop():
    """After physics enable on drop, kill crazy spin."""
    # Add SetPhysicsAngularVelocity / SetAllPhysicsAngularVelocity in TryRelease after SetPrimitiveCompPhysics
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    bp = unreal.load_asset(GRAB)
    editor, _ = ops._editor_for(bp, "TryRelease")
    nodes = list(editor.list_all_nodes())
    by = {n.get_name(): n for n in nodes}
    # Find SetPrimitiveCompPhysics call then pin
    setphys = None
    for n in nodes:
        if ops._node_title(n) == "SetPrimitiveCompPhysics":
            setphys = n
            break
    if not setphys:
        LOG.append({"drop_damp": "no SetPrimitiveCompPhysics"})
        return

    # Check if we already added a damp node
    for n in nodes:
        if "AngularVelocity" in ops._node_title(n) or "LinearVelocity" in ops._node_title(n):
            if "CursorDamp" in n.get_name() or True:
                # idempotent-ish: if SetPhysicsAngularVelocity already connected after setphys, skip recreate
                pass

    def pin(node, name, direction=None):
        for p in bel.list_all_pins(node):
            if str(pinlib.get_pin_name(p)) != name:
                continue
            d = str(pinlib.get_pin_direction(p))
            if direction == "output" and "OUTPUT" not in d:
                continue
            if direction == "input" and "INPUT" not in d:
                continue
            return p
        return None

    # Insert: after SetPrimitiveCompPhysics.then -> SetPhysicsAngularVelocity(0) on attach parent
    # Use existing GetAttachParent if present
    get_parent = None
    for n in nodes:
        if ops._node_title(n) == "GetAttachParent" and n.get_name() == "K2Node_CallFunction_2":
            get_parent = n
            break
    if not get_parent:
        for n in nodes:
            if ops._node_title(n) == "GetAttachParent":
                get_parent = n
                break

    # Create angular + linear zero velocity nodes
    try:
        ang = editor.create_node_from_name(
            "Set Physics Angular Velocity in Degrees", unreal.Vector2D(1200.0, 400.0), []
        )
    except Exception:
        try:
            ang = editor.create_node_from_name(
                "SetPhysicsAngularVelocityInDegrees", unreal.Vector2D(1200.0, 400.0), []
            )
        except Exception as e:
            LOG.append({"ang_create_err": str(e)})
            ang = None
    try:
        lin = editor.create_node_from_name(
            "Set Physics Linear Velocity", unreal.Vector2D(1500.0, 400.0), []
        )
    except Exception as e:
        LOG.append({"lin_create_err": str(e)})
        lin = None

    if not ang:
        # Fallback: just raise damping on guns; skip graph edit
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(GRAB)
        LOG.append({"drop_damp": "skipped graph; phys damping on guns only"})
        return

    then_sp = pin(setphys, "then", "output")
    # What was then connected to?
    old_targets = list(pinlib.list_connected_pins(then_sp) or [])
    for fn in ("break_all_pin_links", "break_pin_links"):
        f = getattr(pinlib, fn, None)
        if callable(f):
            try:
                f(then_sp)
                break
            except Exception:
                pass

    exec_ang = pin(ang, "execute", "input")
    then_ang = pin(ang, "then", "output")
    if then_sp and exec_ang:
        pinlib.try_create_connection(then_sp, exec_ang)

    # Wire target = GetAttachParent return
    if get_parent:
        rv = pin(get_parent, "ReturnValue", "output")
        self_ang = pin(ang, "self", "input") or pin(ang, "Target", "input")
        if rv and self_ang:
            pinlib.try_create_connection(rv, self_ang)

    # NewAngVel = 0,0,0 default
    pvel = pin(ang, "NewAngVel", "input") or pin(ang, "AngularVelocity", "input")
    if pvel:
        try:
            pinlib.set_pin_default_value(pvel, "0.0,0.0,0.0")
        except Exception:
            pass

    next_node = ang
    if lin:
        exec_lin = pin(lin, "execute", "input")
        if then_ang and exec_lin:
            pinlib.try_create_connection(then_ang, exec_lin)
        if get_parent:
            rv = pin(get_parent, "ReturnValue", "output")
            self_lin = pin(lin, "self", "input") or pin(lin, "Target", "input")
            if rv and self_lin:
                pinlib.try_create_connection(rv, self_lin)
        pnew = pin(lin, "NewVel", "input") or pin(lin, "Velocity", "input")
        if pnew:
            # Keep a mild drop — don't zero linear or throws feel dead; clamp later if needed
            # Actually user wants settle: zeroing linear on drop removes throw. Skip linear zero.
            pass
        # Don't use lin zero — disconnect idea: only kill angular
        # Remove lin from chain
        next_then = then_ang
    else:
        next_then = then_ang

    # Reconnect old targets to ang.then
    for ot in old_targets:
        try:
            pinlib.try_create_connection(next_then, ot)
        except Exception as e:
            LOG.append({"reconnect_err": str(e)})

    # If we created lin, remove it to avoid zeroing throw velocity
    if lin:
        try:
            editor.remove_node(lin)
        except Exception:
            pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    errs = [ops._node_title(n) for n in editor.list_nodes_with_errors()]
    unreal.EditorAssetLibrary.save_asset(GRAB)
    LOG.append({"drop_damp": "angular_zero_on_release", "status": str(bp.status), "errs": errs})


def respawn_level():
    placements = [
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol", 5150.0, -785.0, 110.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1", 5150.0, -695.0, 110.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2", 5150.0, -605.0, 110.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun", 5150.0, -515.0, 110.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun", 5150.0, -425.0, 110.0),
        ("/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper", 5150.0, -335.0, 110.0),
    ]
    deleted = 0
    for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        cn = a.get_class().get_name()
        if "SciFi" in cn:
            unreal.EditorLevelLibrary.destroy_actor(a)
            deleted += 1
    created = []
    for path, x, y, z in placements:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            cls, unreal.Vector(x, y, z), unreal.Rotator(0, 90, 0)
        )
        if actor and actor.root_component:
            actor.root_component.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
            created.append(actor.get_class().get_name())
    unreal.EditorLevelLibrary.save_current_level()
    LOG.append({"respawn": {"deleted": deleted, "created": created}})


def main():
    phys_mat = _ensure_phys_mat()
    ensure_rifle_default_fx()
    for path, cfg in GUNS.items():
        try:
            configure_gun(path, cfg, phys_mat)
        except Exception as e:
            LOG.append({"configure_err": path.split("/")[-1], "e": str(e)})
    try:
        damp_on_drop()
    except Exception as e:
        LOG.append({"damp_err": str(e)})
    respawn_level()
    return {"success": True, "log": LOG}


RESULT = main()
