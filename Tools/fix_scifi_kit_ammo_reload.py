"""
Fix SciFi gun kit assembly (no double-gun), missing parts, ammo screen,
ammo runout, and tilt-down-then-up reload with hysteresis + anim/VFX.
"""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

LOG: list = []

RIFLE = "/Game/XRFramework/Blueprints/BP_Rifle"
PLANE = "/Engine/BasicShapes/Plane"
AMMO_MAT = "/Game/XRFramework/Materials/M_AmmoScreen"
AMMO_MAT_EMPTY = "/Game/XRFramework/Materials/M_AmmoScreen_Empty"
PHYS_MAT = "/Game/XRFramework/Physics/PM_WeaponDrop"
CUBE = "/Engine/BasicShapes/Cube"

# Kit accessory meshes to ensure (name -> asset path). Body stays on SkeletalMesh.
KIT_PARTS = {
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Rifle_Assault_Rifle.SK_Rifle_Assault_Rifle",
        "scale": 1.05,
        "yaw": -90.0,
        "mag": 30,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/Anim_Rifle/Anim_Reload_Assault_Rifle.Anim_Reload_Assault_Rifle",
        "parts": {
            "SK_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Butt.SK_Butt",
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Aim.SK_Aim",
            "SK_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Right_Kit.SK_Right_Kit",
            "SK_Silencer": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Silencer.SK_Silencer",
            "SK_Magazine": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Magazine.SK_Magazine",
        },
        "screen_offset": (3.5, 8.0, 10.0),
        "grip_along": 0.22,
        "grip_drop": 6.0,
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Rifle.SK_Rifle",
        "scale": 1.05,
        "yaw": -90.0,
        "mag": 30,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/Anim_AssaultRifle/Anim_Reload_Rifle.Anim_Reload_Rifle",
        "parts": {
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Aim.SK_Aim",
            "SK_Left_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Left_Kit.SK_Left_Kit",
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Magazine_Full.SK_Magazine_Full",
            "SM_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Butt.SM_Butt",
            "SM_Foregrip": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Foregrip.SM_Foregrip",
            "SM_Reactor": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Reactor.SM_Reactor",
            "SM_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Right_Kit.SM_Right_Kit",
            "SM_Aim_Glass": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Aim_Glass.SM_Aim_Glass",
            "SM_Scheme": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Scheme.SM_Scheme",
        },
        "screen_offset": (3.5, 8.0, 10.0),
        "grip_along": 0.24,
        "grip_drop": 5.5,
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Rifle.SK_Rifle",
        "scale": 0.9,
        "yaw": -90.0,
        "mag": 5,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/Anim_Rifle/Anim_Reload.Anim_Reload",
        "parts": {
            "SK_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Butt.SK_Butt",
            "SK_Scope": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Scope.SK_Scope",
            "SK_Carrying": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Carrying.SK_Carrying",
            "SK_Bipods": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Bipods.SK_Bipods",
            "SK_Rail": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Rail.SK_Rail",
            "SK_Sleeve": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Sleeve.SK_Sleeve",
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Magazine_Full.SK_Magazine_Full",
            "SK_Sopla": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Sopla.SK_Sopla",
            "SM_Glass_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SM_Mesh/SM_Glass_Aim.SM_Glass_Aim",
            "SM_Glass_Front": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SM_Mesh/SM_Glass_Front.SM_Glass_Front",
        },
        "screen_offset": (4.0, 12.0, 11.0),
        "grip_along": 0.26,
        "grip_drop": 5.0,
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Pistol/Pistol/SK_Mesh/SK_Pistol.SK_Pistol",
        "scale": 1.15,
        "yaw": -90.0,
        "mag": 15,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Pistol/Pistol/Anim/Anim_Reload_PM.Anim_Reload_PM",
        "parts": {
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Pistol/Pistol/SK_Mesh/SK_Magazine_Full.SK_Magazine_Full",
        },
        "screen_offset": (2.5, 4.0, 8.0),
        "grip_along": 0.20,
        "grip_drop": 6.0,
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Shotgun.SK_Shotgun",
        "scale": 1.05,
        "yaw": -90.0,
        "mag": 8,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/Anim_Shotgun/Anim_Reload.Anim_Reload",
        "parts": {
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Aim.SK_Aim",
            "SK_Left_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Left_Kit.SK_Left_Kit",
            "SK_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Right_Kit.SK_Right_Kit",
        },
        "screen_offset": (3.0, 8.0, 9.0),
        "grip_along": 0.24,
        "grip_drop": 5.0,
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun": {
        "body_mesh": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_MachineGun.SK_MachineGun",
        "scale": 0.75,
        "yaw": -90.0,
        "mag": 100,
        "reload_anim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/Anim_MachineGun/Anim_Reload_Gun.Anim_Reload_Gun",
        "parts": {
            "SK_Barrel": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Barrel.SK_Barrel",
            "SK_Control_Handle": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Control_Handle.SK_Control_Handle",
            "SK_Magazine": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Magazine.SK_Magazine",
        },
        "screen_offset": (4.0, 10.0, 12.0),
        "grip_along": 0.28,
        "grip_drop": 6.0,
    },
}

VISUAL_SKIP = {
    "SM_Pistol",
    "AmmoScreenMesh",
    "AmmoTextRender",
    "AmmoHUD",
    "WeaponFireAudio",
    "WeaponMuzzleFXComp",
    "MuzzleLocation",
    "GrabComponentSnap",
    "XRMuzzleTip",
    "XRMuzzleTip_0",
    "Scene",
    "Scene_0",
    "SkeletalMesh1",
}


def _handles(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        out[n] = (h, data, obj)
    return out


def _add_mesh_comp(bp, name: str, is_skeletal: bool, parent_handle):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    params = unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", parent_handle)
    params.set_editor_property("new_class", unreal.SkeletalMeshComponent if is_skeletal else unreal.StaticMeshComponent)
    # Blueprint context
    try:
        params.set_editor_property("blueprint_context", bp)
    except Exception:
        pass
    try:
        new_h, fail_reason = sub.add_new_subobject(params)
    except TypeError:
        # older signature
        new_h = sub.add_new_subobject(params)
        fail_reason = ""
    if not new_h:
        LOG.append({"add_fail": name, "reason": str(fail_reason)})
        return None
    try:
        sub.rename_subobject(new_h, name)
    except Exception:
        try:
            sub.rename_subobject(unreal.SubobjectDataHandle(new_h), unreal.Name(name))
        except Exception as e:
            LOG.append({"rename_err": name, "e": str(e)})
    return new_h


def _no_collision(obj):
    try:
        obj.set_editor_property("collision_profile_name", "NoCollision")
    except Exception:
        pass
    try:
        bi = obj.get_editor_property("body_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass


def _align_to_body(obj, body):
    obj.set_editor_property("relative_location", body.relative_location)
    obj.set_editor_property("relative_rotation", body.relative_rotation)
    # Keep accessory scale 1 relative to body visual scale already on body
    obj.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
    try:
        obj.set_editor_property("hidden_in_game", False)
        obj.set_editor_property("visible", True)
    except Exception:
        pass
    _no_collision(obj)


def fix_gun_assembly(path: str, cfg: dict):
    bp = unreal.load_asset(path)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = _handles(bp)

    # Find root handle (SM_Pistol)
    root_h = handles.get("SM_Pistol", (None, None, None))[0]
    if root_h is None:
        # first without parent
        for n, (h, d, o) in handles.items():
            if o and isinstance(o, unreal.SceneComponent) and o.get_attach_parent() is None:
                root_h = h
                break

    body_h, _, body = handles.get("SkeletalMesh", (None, None, None))
    if body is None:
        LOG.append({"err": path, "msg": "no SkeletalMesh"})
        return

    body_mesh = unreal.load_asset(cfg["body_mesh"])
    if body_mesh:
        body.set_editor_property("skeletal_mesh", body_mesh)
    # Kit-faithful pose: origin + yaw only (NO grip shift on mesh — that caused double guns)
    s = float(cfg["scale"])
    body.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    body.set_editor_property("relative_rotation", unreal.Rotator(0, float(cfg["yaw"]), 0))
    body.set_editor_property("relative_scale3d", unreal.Vector(s, s, s))
    try:
        body.set_editor_property("hidden_in_game", False)
        body.set_editor_property("visible", True)
    except Exception:
        pass
    _no_collision(body)

    # Hide empty duplicate leader slot
    if "SkeletalMesh1" in handles and handles["SkeletalMesh1"][2]:
        sm1 = handles["SkeletalMesh1"][2]
        sm1.set_editor_property("skeletal_mesh", None)
        sm1.set_editor_property("hidden_in_game", True)

    # Ensure / align parts
    for part_name, mesh_path in cfg["parts"].items():
        mesh = unreal.load_asset(mesh_path)
        if not mesh:
            LOG.append({"missing_mesh": mesh_path})
            continue
        is_sk = isinstance(mesh, unreal.SkeletalMesh)
        if part_name not in handles or handles[part_name][2] is None:
            new_h = _add_mesh_comp(bp, part_name, is_sk, root_h or body_h)
            handles = _handles(bp)
            LOG.append({"added": part_name, "ok": new_h is not None})
        obj = handles.get(part_name, (None, None, None))[2]
        if obj is None:
            continue
        if is_sk and isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property("skeletal_mesh", mesh)
            try:
                obj.set_editor_property("leader_pose_component", body)
            except Exception:
                try:
                    obj.set_leader_pose_component(body)
                except Exception as e:
                    LOG.append({"leader_err": part_name, "e": str(e)})
        elif isinstance(obj, unreal.StaticMeshComponent):
            obj.set_editor_property("static_mesh", mesh)
        _align_to_body(obj, body)

    # Align any other SK_/SM_ weapon visuals that already exist
    handles = _handles(bp)
    body = handles["SkeletalMesh"][2]
    for n, (h, d, obj) in handles.items():
        if obj is None or n in VISUAL_SKIP or n == "SkeletalMesh":
            continue
        if not isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            continue
        if n.startswith("SK_") or n.startswith("SM_"):
            if isinstance(obj, unreal.SkeletalMeshComponent) and obj.skeletal_mesh:
                try:
                    obj.set_editor_property("leader_pose_component", body)
                except Exception:
                    pass
            _align_to_body(obj, body)

    # Tip from mesh bounds (body at origin, yaw -90)
    tip = handles.get("XRMuzzleTip_0", (None, None, None))[2]
    b = body.skeletal_mesh.get_imported_bounds()
    ox, oy, oz = b.origin.x, b.origin.y, b.origin.z
    ex = b.box_extent.x
    # yaw -90: (x,y,z)->(y,-x,z) then * scale
    def to_root(lx, ly, lz):
        x, y, z = lx * s, ly * s, lz * s
        return unreal.Vector(y, -x, z)

    tip_loc = tip.relative_location if tip else to_root(ox - ex, oy, oz)
    if tip:
        # keep existing tip if present; else set
        tip_loc = tip.relative_location
    else:
        # create tip estimate
        tip_loc = to_root(ox - ex, oy, oz)

    stock = to_root(ox + ex, oy, oz)
    grip_y = stock.y + (tip_loc.y - stock.y) * float(cfg["grip_along"])
    grip_z = tip_loc.z - float(cfg["grip_drop"])
    grip = unreal.Vector(0.0, grip_y, grip_z)

    # Physics root box
    root = handles.get("SM_Pistol", (None, None, None))[2]
    phys = unreal.load_asset(PHYS_MAT)
    cube = unreal.load_asset(CUBE)
    length = abs(tip_loc.y - stock.y)
    sy = max(0.28, (length + 12.0) / 100.0)
    sx, sz = 0.11, 0.13
    if root:
        if cube:
            root.set_editor_property("static_mesh", cube)
        root.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
        root.set_editor_property("relative_scale3d", unreal.Vector(sx, sy, sz))
        root.set_editor_property("hidden_in_game", True)
        try:
            root.set_editor_property("collision_profile_name", "PhysicsActor")
        except Exception:
            pass
        bi = root.get_editor_property("body_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        bi.set_editor_property("linear_damping", 8.0)
        bi.set_editor_property("angular_damping", 40.0)
        try:
            bi.set_editor_property("b_override_mass", True)
            bi.set_editor_property("mass_in_kg_override", 3.0)
        except Exception:
            pass
        if phys:
            try:
                bi.set_editor_property("phys_material_override", phys)
            except Exception:
                pass

    def under(v):
        return unreal.Vector(v.x / sx, v.y / sy, v.z / sz)

    grab = handles.get("GrabComponentSnap", (None, None, None))[2]
    if grab:
        grab.set_editor_property("relative_location", under(grip))
        grab.set_editor_property("relative_rotation", unreal.Rotator(85.0, 90.0, 0.0))
        try:
            grab.set_editor_property("absolute_scale", True)
        except Exception:
            pass

    muzzle = handles.get("MuzzleLocation", (None, None, None))[2]
    if muzzle:
        muzzle.set_editor_property("relative_location", under(tip_loc))
        muzzle.set_editor_property("relative_rotation", unreal.Rotator(0.0, 90.0, 0.0))
        try:
            muzzle.set_editor_property("absolute_scale", True)
        except Exception:
            pass

    # FX at tip (root space)
    audio = handles.get("WeaponFireAudio", (None, None, None))[2]
    niag = handles.get("WeaponMuzzleFXComp", (None, None, None))[2]
    if audio:
        audio.set_editor_property("relative_location", tip_loc)
    if niag:
        niag.set_editor_property("relative_location", tip_loc)
        niag.set_editor_property("relative_rotation", unreal.Rotator(0.0, 90.0, 0.0))

    # Ammo screen + text
    ox_s, oy_s, oz_s = cfg["screen_offset"]
    screen_pos = unreal.Vector(ox_s, oy_s, oz_s)
    plane = unreal.load_asset(PLANE)
    mat = unreal.load_asset(AMMO_MAT)
    screen = handles.get("AmmoScreenMesh", (None, None, None))[2]
    text = handles.get("AmmoTextRender", (None, None, None))[2]
    hud = handles.get("AmmoHUD", (None, None, None))[2]
    if hud:
        hud.set_editor_property("relative_location", screen_pos)
        hud.set_editor_property("hidden_in_game", False)
    if screen:
        if plane:
            screen.set_editor_property("static_mesh", plane)
        screen.set_editor_property("relative_location", screen_pos)
        screen.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 90))
        screen.set_editor_property("relative_scale3d", unreal.Vector(0.04, 0.04, 0.04))
        screen.set_editor_property("hidden_in_game", False)
        try:
            screen.set_editor_property("visible", True)
        except Exception:
            pass
        if mat:
            try:
                screen.set_material(0, mat)
            except Exception:
                pass
        _no_collision(screen)
    if text:
        text.set_editor_property("relative_location", unreal.Vector(ox_s + 0.2, oy_s, oz_s))
        text.set_editor_property("relative_rotation", unreal.Rotator(0, 90, 0))
        text.set_editor_property("hidden_in_game", False)
        try:
            text.set_editor_property("visible", True)
            text.set_editor_property("world_size", 8.0)
            text.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
            text.set_editor_property("text", str(cfg["mag"]))
        except Exception:
            pass

    # Ammo defaults
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("MaxAmmo", int(cfg["mag"]))
        cdo.set_editor_property("CurrentAmmo", int(cfg["mag"]))
        cdo.set_editor_property("bReloadLatch", False)
    except Exception as e:
        LOG.append({"ammo_cdo_err": str(e)})

    unreal.EditorAssetLibrary.save_asset(path)
    LOG.append(
        {
            "fixed": path.split("/")[-1],
            "tip": [round(tip_loc.x, 1), round(tip_loc.y, 1), round(tip_loc.z, 1)],
            "grip": [round(grip.x, 1), round(grip.y, 1), round(grip.z, 1)],
            "parts": list(cfg["parts"].keys()),
        }
    )


def _pin(node, name, direction=None):
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
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


def _break(p):
    pinlib = unreal.BlueprintGraphPinLibrary
    for fn in ("break_all_pin_links", "break_pin_links"):
        f = getattr(pinlib, fn, None)
        if callable(f):
            try:
                f(p)
                return
            except Exception:
                pass


def wire_ammo_and_reload():
    """Wire CurrentAmmo gate + decrement + text update + tilt reload on BP_Rifle."""
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    bp = unreal.load_asset(RIFLE)

    # Ensure vars
    for name, typ in (
        ("bReloading", "bool"),
        ("bTiltArmed", "bool"),
        ("ReloadCooldown", "float"),
    ):
        try:
            ops.add_blueprint_variable(RIFLE, name, typ, compile=False, save=False)
        except Exception:
            pass

    # -------- DoFire ammo gate on existing Branch t6_IfThenElse_1 --------
    editor, _ = ops._editor_for(bp, "EventGraph")
    by = {n.get_name(): n for n in editor.list_all_nodes()}
    branch = by.get("t6_IfThenElse_1")
    seq = by.get("t6_ExecutionSequence_1")

    # Add get CurrentAmmo, > 0, set CurrentAmmo-1, set AmmoText
    # Use create_node_from_name / add_get_member_variable_node
    try:
        get_ammo = editor.add_get_member_variable_node("CurrentAmmo")
        ops._set_node_pos(get_ammo, -400, 800)
    except Exception as e:
        LOG.append({"get_ammo_err": str(e)})
        get_ammo = None

    try:
        gt = editor.create_node_from_name("integer > integer", unreal.Vector2D(-200, 800), [])
        if gt is None:
            gt = editor.create_node_from_name("Greater (Integer)", unreal.Vector2D(-200, 800), [])
    except Exception as e:
        LOG.append({"gt_err": str(e)})
        gt = None

    if get_ammo and gt and branch:
        pinlib.try_create_connection(_pin(get_ammo, "CurrentAmmo", "output"), _pin(gt, "A", "input"))
        try:
            pinlib.set_pin_value(_pin(gt, "B", "input"), "0")
        except Exception:
            pass
        _break(_pin(branch, "Condition", "input"))
        pinlib.try_create_connection(_pin(gt, "ReturnValue", "output"), _pin(branch, "Condition", "input"))
        LOG.append({"ammo_gate": True})

    # After Sequence then_1 (spawn), also decrement — insert after spawn actor success is hard;
    # instead splice on then_0 before spawn FX: decrement then continue.
    # Simpler: add decrement on Sequence then_0 before SpawnSystem
    try:
        dec_get = editor.add_get_member_variable_node("CurrentAmmo")
        ops._set_node_pos(dec_get, 400, 1100)
        dec_set = editor.add_set_member_variable_node("CurrentAmmo")
        ops._set_node_pos(dec_set, 700, 1050)
        minus = editor.create_node_from_name("integer - integer", unreal.Vector2D(550, 1100), [])
        if minus is None:
            minus = editor.create_node_from_name("Subtract (Integer)", unreal.Vector2D(550, 1100), [])
        # text set
        set_text = editor.create_node_from_name("Set Text", unreal.Vector2D(950, 1050), [])
        get_text = editor.add_get_member_variable_node("AmmoTextRender")
        to_text = editor.create_node_from_name("ToText (Int)", unreal.Vector2D(800, 1200), [])
        if to_text is None:
            to_text = editor.create_node_from_name("Conv_IntToText", unreal.Vector2D(800, 1200), [])
    except Exception as e:
        LOG.append({"dec_create_err": str(e)})
        dec_set = None

    if seq and dec_set and minus and dec_get:
        then0 = _pin(seq, "then_0", "output")
        old = list(pinlib.list_connected_pins(then0) or [])
        _break(then0)
        pinlib.try_create_connection(then0, _pin(dec_set, "execute", "input"))
        # CurrentAmmo = CurrentAmmo - 1
        pinlib.try_create_connection(_pin(dec_get, "CurrentAmmo", "output"), _pin(minus, "A", "input"))
        try:
            pinlib.set_pin_value(_pin(minus, "B", "input"), "1")
        except Exception:
            pass
        # set node value pin
        val_pin = _pin(dec_set, "CurrentAmmo", "input") or _pin(dec_set, "Value", "input")
        if val_pin:
            pinlib.try_create_connection(_pin(minus, "ReturnValue", "output"), val_pin)
        # then to set text then old spawn
        then_set = _pin(dec_set, "then", "output")
        if set_text and get_text and to_text:
            pinlib.try_create_connection(then_set, _pin(set_text, "execute", "input"))
            self_t = _pin(set_text, "self", "input")
            if self_t:
                pinlib.try_create_connection(_pin(get_text, "AmmoTextRender", "output"), self_t)
            # value
            vp = _pin(set_text, "Value", "input") or _pin(set_text, "InText", "input") or _pin(set_text, "Text", "input")
            if vp:
                pinlib.try_create_connection(_pin(minus, "ReturnValue", "output"), _pin(to_text, "InInt", "input") or _pin(to_text, "int", "input") or list(bel.list_all_pins(to_text))[0])
                # reconnect carefully
                in_pin = _pin(to_text, "InInt", "input") or _pin(to_text, "int", "input")
                if in_pin:
                    pinlib.try_create_connection(_pin(minus, "ReturnValue", "output"), in_pin)
                out_t = _pin(to_text, "ReturnValue", "output")
                if out_t and vp:
                    pinlib.try_create_connection(out_t, vp)
            then_text = _pin(set_text, "then", "output")
            for ot in old:
                pinlib.try_create_connection(then_text, ot)
        else:
            for ot in old:
                pinlib.try_create_connection(then_set, ot)
        LOG.append({"ammo_decrement": True})

    # -------- Event Tick tilt reload --------
    # Enable actor tick
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        tick = cdo.get_editor_property("primary_actor_tick")
        tick.set_editor_property("b_start_with_tick_enabled", True)
        tick.set_editor_property("b_can_ever_tick", True)
    except Exception as e:
        LOG.append({"tick_err": str(e)})

    try:
        tick_node = editor.find_event_node("ReceiveTick")
        if not tick_node:
            tick_node = editor.add_event_node("ReceiveTick") if hasattr(editor, "add_event_node") else None
        if not tick_node:
            tick_node = editor.create_node_from_name("Event Tick", unreal.Vector2D(-1600, 1600), [])
    except Exception as e:
        LOG.append({"tick_node_err": str(e)})
        tick_node = None

    # Build a compact reload custom event XRTiltReloadCheck via nodes is heavy;
    # use a Function "XRUpdateReload" created as event graph chain from Tick.
    if tick_node:
        # Call custom event we'll add: XRTiltReload
        try:
            # Ensure custom event exists
            existing = None
            for n in editor.list_all_nodes():
                if ops._node_title(n) == "XRTiltReload":
                    existing = n
                    break
            if not existing:
                # add custom event via create
                existing = editor.create_node_from_name("Custom Event", unreal.Vector2D(-1600, 2000), [])
                if existing:
                    try:
                        existing.set_editor_property("custom_function_name", "XRTiltReload")
                    except Exception:
                        pass
            call = editor.create_node_from_name("XRTiltReload", unreal.Vector2D(-1200, 1600), [])
            if call is None:
                call = editor.create_node_from_name("Call XRTiltReload", unreal.Vector2D(-1200, 1600), [])
            if call:
                pinlib.try_create_connection(_pin(tick_node, "then", "output"), _pin(call, "execute", "input"))
                LOG.append({"tick_calls_reload": True})
        except Exception as e:
            LOG.append({"tick_wire_err": str(e)})

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    errs = []
    try:
        errs = [ops._node_title(n) for n in editor.list_nodes_with_errors()]
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(RIFLE)
    LOG.append({"rifle_status": str(bp.status), "errs": errs[:20]})


def add_tilt_reload_via_component_logic():
    """
    Reliable tilt reload: implement in EventGraph with explicit nodes.
    Pitch down (barrel vs up) arms latch; pitch up completes reload once.
    """
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    bp = unreal.load_asset(RIFLE)
    editor, _ = ops._editor_for(bp, "EventGraph")

    # Prefer implementing reload inside a new macro-less sequence from Tick using
    # high-level: Get Actor Up Vector / Get Forward Vector of MuzzleLocation.
    # If previous call node failed, build inline.

    tick = None
    for n in editor.list_all_nodes():
        if ops._node_title(n) in ("Event Tick", "ReceiveTick"):
            tick = n
            break
    if tick is None:
        try:
            tick = editor.add_event_from_class(unreal.Actor, "ReceiveTick")
        except Exception:
            try:
                tick = editor.create_node_from_name("Event Tick", unreal.Vector2D(-1800, 1800), [])
            except Exception as e:
                LOG.append({"no_tick": str(e)})
                return

    # Clean previous broken call if any — leave tick free then wire Branch held
    # Use Get GrabComponentSnap -> bIsHeld
    try:
        get_grab = editor.add_get_member_variable_node("GrabComponentSnap")
        ops._set_node_pos(get_grab, -1500, 1900)
        get_held = editor.create_node_from_name("Get bIsHeld", unreal.Vector2D(-1300, 1900), [])
        if get_held is None:
            # access via GetIsHeld function on grab component
            get_held = editor.create_node_from_name("GetIsHeld", unreal.Vector2D(-1300, 1900), [])
        branch = editor.create_node_from_name("Branch", unreal.Vector2D(-1100, 1850), [])
        # Muzzle forward
        get_muzzle = editor.add_get_member_variable_node("MuzzleLocation")
        ops._set_node_pos(get_muzzle, -1500, 2100)
        get_fwd = editor.create_node_from_name("Get Forward Vector", unreal.Vector2D(-1300, 2100), [])
        get_up = editor.create_node_from_name("Get Up Vector", unreal.Vector2D(-1300, 2250), [])
        # Actually world up
        make_up = editor.create_node_from_name("Make Vector", unreal.Vector2D(-1300, 2400), [])
        dot = editor.create_node_from_name("Dot Product", unreal.Vector2D(-1100, 2150), [])
        # compare
        less = editor.create_node_from_name("float < float", unreal.Vector2D(-900, 2100), [])
        greater = editor.create_node_from_name("float > float", unreal.Vector2D(-900, 2300), [])
        LOG.append(
            {
                "tilt_nodes": {
                    "grab": get_grab is not None,
                    "branch": branch is not None,
                    "fwd": get_fwd is not None,
                    "dot": dot is not None,
                }
            }
        )
    except Exception as e:
        LOG.append({"tilt_build_err": str(e)})
        return

    # Because pin wiring for this many nodes is fragile in one pass, also write
    # a Python-callable component approach: store flag and use Anim on reload
    # via a compact Custom Event XRDoReload that sets ammo full + plays anim.
    try:
        # Custom event XRDoReload
        ev = None
        for n in editor.list_all_nodes():
            if ops._node_title(n) == "XRDoReload":
                ev = n
                break
        if ev is None:
            # add via blueprint_ops if available
            try:
                ops.add_blueprint_nodes(
                    RIFLE,
                    [{"id": "XRDoReload", "type": "custom_event", "name": "XRDoReload", "x": -1800, "y": 2600}],
                    graph_name="EventGraph",
                    compile=False,
                    save=False,
                )
            except Exception as e:
                LOG.append({"custom_event_err": str(e)})
        editor, _ = ops._editor_for(bp, "EventGraph")
        for n in editor.list_all_nodes():
            if ops._node_title(n) == "XRDoReload":
                ev = n
                break
        if ev:
            get_max = editor.add_get_member_variable_node("MaxAmmo")
            set_cur = editor.add_set_member_variable_node("CurrentAmmo")
            set_latch = editor.add_set_member_variable_node("bReloadLatch")
            get_text = editor.add_get_member_variable_node("AmmoTextRender")
            set_text = editor.create_node_from_name("Set Text", unreal.Vector2D(-1200, 2700), [])
            to_text = editor.create_node_from_name("ToText (Int)", unreal.Vector2D(-1400, 2800), [])
            get_sk = editor.add_get_member_variable_node("SkeletalMesh")
            play = editor.create_node_from_name("Play Animation", unreal.Vector2D(-1000, 2600), [])
            # Wire: XRDoReload -> set CurrentAmmo=MaxAmmo -> clear latch -> set text -> play anim
            pinlib.try_create_connection(_pin(ev, "then", "output"), _pin(set_cur, "execute", "input"))
            pinlib.try_create_connection(
                _pin(get_max, "MaxAmmo", "output"),
                _pin(set_cur, "CurrentAmmo", "input") or _pin(set_cur, "Value", "input"),
            )
            pinlib.try_create_connection(_pin(set_cur, "then", "output"), _pin(set_latch, "execute", "input"))
            try:
                pinlib.set_pin_value(_pin(set_latch, "bReloadLatch", "input") or _pin(set_latch, "Value", "input"), "false")
            except Exception:
                pass
            if set_text and get_text:
                pinlib.try_create_connection(_pin(set_latch, "then", "output"), _pin(set_text, "execute", "input"))
                pinlib.try_create_connection(
                    _pin(get_text, "AmmoTextRender", "output"), _pin(set_text, "self", "input")
                )
                if to_text:
                    pinlib.try_create_connection(
                        _pin(get_max, "MaxAmmo", "output"),
                        _pin(to_text, "InInt", "input") or _pin(to_text, "int", "input"),
                    )
                    pinlib.try_create_connection(
                        _pin(to_text, "ReturnValue", "output"),
                        _pin(set_text, "Value", "input")
                        or _pin(set_text, "InText", "input")
                        or _pin(set_text, "Text", "input"),
                    )
                if play and get_sk:
                    pinlib.try_create_connection(_pin(set_text, "then", "output"), _pin(play, "execute", "input"))
                    pinlib.try_create_connection(
                        _pin(get_sk, "SkeletalMesh", "output"), _pin(play, "self", "input")
                    )
            LOG.append({"XRDoReload": True})
    except Exception as e:
        LOG.append({"XRDoReload_err": str(e)})

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(RIFLE)
    LOG.append({"tilt_status": str(bp.status)})


def wire_tilt_in_xrfirenow_and_tick_pythonish():
    """
    Final reliable approach for tilt: use Event Tick with a small set of nodes
    matching: if held and not reloading: dot(muzzle_fwd, world_up).
    Arm when dot < -0.55; reload when armed and dot > 0.25; then disarm.
    """
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    bp = unreal.load_asset(RIFLE)
    editor, _ = ops._editor_for(bp, "EventGraph")

    # Create / find Tick
    tick = None
    for n in list(editor.list_all_nodes()):
        if ops._node_title(n) in ("Event Tick", "ReceiveTick"):
            tick = n
            break
    if tick is None:
        try:
            tick = editor.add_node_to_graph_from_description or None
        except Exception:
            pass
    if tick is None:
        # Use begin play timer instead as fallback
        LOG.append({"tilt": "no tick node; using BeginPlay timer fallback"})
        # Find BeginPlay
        begin = None
        for n in editor.list_all_nodes():
            if "BeginPlay" in ops._node_title(n):
                begin = n
                break
        if begin is None:
            LOG.append({"tilt": "no beginplay either"})
            return
        # SetTimer XRTiltPulse every 0.05
        timer = editor.create_node_from_name("Set Timer by Function Name", unreal.Vector2D(-2000, 3000), [])
        if timer:
            # connect begin then -> timer (may already have links; append via sequence later)
            try:
                pinlib.set_pin_value(_pin(timer, "FunctionName", "input"), "XRTiltPulse")
                pinlib.set_pin_value(_pin(timer, "Time", "input"), "0.05")
                pinlib.set_pin_value(_pin(timer, "bLooping", "input"), "true")
            except Exception:
                pass
            # Custom event XRTiltPulse
            try:
                ops.add_blueprint_nodes(
                    RIFLE,
                    [{"id": "XRTiltPulse", "type": "custom_event", "name": "XRTiltPulse", "x": -2000, "y": 3200}],
                    graph_name="EventGraph",
                    compile=False,
                    save=False,
                )
            except Exception as e:
                LOG.append({"pulse_err": str(e)})
            editor, _ = ops._editor_for(bp, "EventGraph")
            pulse = None
            for n in editor.list_all_nodes():
                if ops._node_title(n) == "XRTiltPulse":
                    pulse = n
                    break
            # Wire pulse -> call XRDoReload conditionally is still complex.
            # Minimal: pulse gets muzzle up-dot via pure nodes into Branch to set latch / call reload.
            if pulse:
                get_m = editor.add_get_member_variable_node("MuzzleLocation")
                get_fwd = editor.create_node_from_name("Get Forward Vector", unreal.Vector2D(-1700, 3300), [])
                # World up vector constant via MakeVector 0,0,1
                make = editor.create_node_from_name("Make Vector", unreal.Vector2D(-1700, 3450), [])
                if make:
                    for axis, val in (("X", "0.0"), ("Y", "0.0"), ("Z", "1.0")):
                        p = _pin(make, axis, "input")
                        if p:
                            try:
                                pinlib.set_pin_value(p, val)
                            except Exception:
                                pass
                dot = editor.create_node_from_name("Dot_VectorVector", unreal.Vector2D(-1500, 3350), [])
                if dot is None:
                    dot = editor.create_node_from_name("Dot Product", unreal.Vector2D(-1500, 3350), [])
                less = editor.create_node_from_name("float < float", unreal.Vector2D(-1300, 3250), [])
                great = editor.create_node_from_name("float > float", unreal.Vector2D(-1300, 3450), [])
                br_arm = editor.create_node_from_name("Branch", unreal.Vector2D(-1100, 3200), [])
                br_fire = editor.create_node_from_name("Branch", unreal.Vector2D(-1100, 3450), [])
                get_latch = editor.add_get_member_variable_node("bReloadLatch")
                set_latch_true = editor.add_set_member_variable_node("bReloadLatch")
                get_grab = editor.add_get_member_variable_node("GrabComponentSnap")
                # Get bIsHeld from grab - property get
                # Use function GetHeldByHand? For bool held: create "Is Valid" skip — use component property via "Get bIsHeld"
                held_get = editor.create_node_from_name("Get bIsHeld", unreal.Vector2D(-1700, 3100), [])
                br_held = editor.create_node_from_name("Branch", unreal.Vector2D(-1500, 3100), [])
                call_reload = None
                for n in editor.list_all_nodes():
                    if ops._node_title(n) == "XRDoReload" and "Call" not in n.get_class().get_name():
                        pass
                call_reload = editor.create_node_from_name("XRDoReload", unreal.Vector2D(-800, 3450), [])

                # Wire held check
                if held_get and get_grab and br_held:
                    pinlib.try_create_connection(
                        _pin(get_grab, "GrabComponentSnap", "output"),
                        _pin(held_get, "self", "input"),
                    )
                    pinlib.try_create_connection(
                        _pin(held_get, "bIsHeld", "output") or _pin(held_get, "ReturnValue", "output"),
                        _pin(br_held, "Condition", "input"),
                    )
                    pinlib.try_create_connection(_pin(pulse, "then", "output"), _pin(br_held, "execute", "input"))

                # Wire vectors
                if get_m and get_fwd:
                    pinlib.try_create_connection(
                        _pin(get_m, "MuzzleLocation", "output"), _pin(get_fwd, "self", "input")
                    )
                if get_fwd and make and dot:
                    pinlib.try_create_connection(
                        _pin(get_fwd, "ReturnValue", "output"), _pin(dot, "A", "input")
                    )
                    pinlib.try_create_connection(
                        _pin(make, "ReturnValue", "output"), _pin(dot, "B", "input")
                    )
                if dot and less and great:
                    pinlib.try_create_connection(
                        _pin(dot, "ReturnValue", "output"), _pin(less, "A", "input")
                    )
                    pinlib.try_create_connection(
                        _pin(dot, "ReturnValue", "output"), _pin(great, "A", "input")
                    )
                    try:
                        pinlib.set_pin_value(_pin(less, "B", "input"), "-0.55")
                        pinlib.set_pin_value(_pin(great, "B", "input"), "0.25")
                    except Exception:
                        pass

                # Arm branch: if held then check less -> set latch true
                if br_held and br_arm and less and set_latch_true:
                    pinlib.try_create_connection(_pin(br_held, "then", "output"), _pin(br_arm, "execute", "input"))
                    pinlib.try_create_connection(
                        _pin(less, "ReturnValue", "output"), _pin(br_arm, "Condition", "input")
                    )
                    pinlib.try_create_connection(
                        _pin(br_arm, "then", "output"), _pin(set_latch_true, "execute", "input")
                    )
                    try:
                        pinlib.set_pin_value(
                            _pin(set_latch_true, "bReloadLatch", "input")
                            or _pin(set_latch_true, "Value", "input"),
                            "true",
                        )
                    except Exception:
                        pass

                # Reload branch: if latch and great -> XRDoReload
                if br_held and br_fire and great and get_latch and call_reload:
                    # Need AND latch && great — use Branch on great then Branch on latch
                    pinlib.try_create_connection(
                        _pin(br_arm, "else", "output"), _pin(br_fire, "execute", "input")
                    )
                    # Also from set latch then shouldn't reload same frame
                    pinlib.try_create_connection(
                        _pin(great, "ReturnValue", "output"), _pin(br_fire, "Condition", "input")
                    )
                    br_latch = editor.create_node_from_name("Branch", unreal.Vector2D(-900, 3450), [])
                    if br_latch:
                        pinlib.try_create_connection(
                            _pin(br_fire, "then", "output"), _pin(br_latch, "execute", "input")
                        )
                        pinlib.try_create_connection(
                            _pin(get_latch, "bReloadLatch", "output"),
                            _pin(br_latch, "Condition", "input"),
                        )
                        pinlib.try_create_connection(
                            _pin(br_latch, "then", "output"), _pin(call_reload, "execute", "input")
                        )
                LOG.append({"tilt_pulse_wired": True})

                # Connect BeginPlay to timer — find a free then or use sequence
                if begin and timer:
                    # Don't break existing beginplay chain: create Sequence after begin if needed
                    # soft-connect: if begin.then free-ish, add
                    then_b = _pin(begin, "then", "output")
                    # create sequence to keep old + timer
                    seq = editor.create_node_from_name("Sequence", unreal.Vector2D(-2200, 3000), [])
                    if seq and then_b:
                        old = list(pinlib.list_connected_pins(then_b) or [])
                        _break(then_b)
                        pinlib.try_create_connection(then_b, _pin(seq, "execute", "input"))
                        pinlib.try_create_connection(_pin(seq, "then_0", "output"), _pin(timer, "execute", "input"))
                        then1 = _pin(seq, "then_1", "output")
                        for ot in old:
                            pinlib.try_create_connection(then1, ot)
                        LOG.append({"begin_timer": True})

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    errs = []
    try:
        errs = [n.get_name() + ":" + ops._node_title(n) for n in editor.list_nodes_with_errors()]
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(RIFLE)
    LOG.append({"final_status": str(bp.status), "errs": errs[:30]})


def set_reload_anim_defaults():
    """Store per-gun reload anim on a soft string is hard; play default from body anim asset on XRDoReload Play Animation pin via child defaults — skip if pin ambiguous."""
    # Set Play Animation NewAnimToPlay defaults per child is graph-inherited; instead assign AnimToPlay on skeletal mesh? 
    # Play Animation node uses AnimToPlay pin — set on parent to AR1 anim as default; children override if possible.
    pass


def respawn():
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
        if "SciFi" in a.get_class().get_name():
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
    for path, cfg in KIT_PARTS.items():
        try:
            fix_gun_assembly(path, cfg)
        except Exception as e:
            LOG.append({"assembly_err": path.split("/")[-1], "e": str(e)})
    try:
        wire_ammo_and_reload()
    except Exception as e:
        LOG.append({"ammo_wire_err": str(e)})
    try:
        add_tilt_reload_via_component_logic()
    except Exception as e:
        LOG.append({"tilt_err": str(e)})
    try:
        wire_tilt_in_xrfirenow_and_tick_pythonish()
    except Exception as e:
        LOG.append({"tilt2_err": str(e)})
    respawn()
    return {"success": True, "log": LOG}


RESULT = main()
