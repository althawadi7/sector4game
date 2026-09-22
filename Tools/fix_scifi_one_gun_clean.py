"""
ONE clean kit gun per BP — no double-mesh Frankenstein.

Root cause: we offset/rotated body and kit parts differently, so accessories
rendered as a second broken gun. Kit BPs keep EVERY visual piece at 0,0,0 / 0,0,0.

This script:
1) Assigns only the correct kit meshes for each SciFi XR gun
2) Forces all visuals to identity transform (match kit)
3) Leader-poses skeletal accessories to the body
4) Hides/clears junk (SkeletalMesh1, empty slots, audio sprite noise stays but tip fixed)
5) Leaves grab/muzzle/physics as separate non-visual setup
"""
from __future__ import annotations

import unreal

LOG: list = []

CUBE = "/Engine/BasicShapes/Cube"
PLANE = "/Engine/BasicShapes/Plane"
PHYS_MAT = "/Game/XRFramework/Physics/PM_WeaponDrop"
AMMO_MAT = "/Game/XRFramework/Materials/M_AmmoScreen"

# Exact kit assembly (same meshes as pack demo BPs). Body key = SkeletalMesh component.
GUNS = {
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Rifle_Assault_Rifle.SK_Rifle_Assault_Rifle",
        "scale": 1.0,
        "mag": 30,
        "sk_parts": {
            "SK_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Butt.SK_Butt",
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Aim.SK_Aim",
            "SK_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Right_Kit.SK_Right_Kit",
            "SK_Silencer": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Silencer.SK_Silencer",
            "SK_Magazine": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_1/Assault_Rifle/SK_Rifle_Mesh/SK_Magazine.SK_Magazine",
        },
        "sm_parts": {},
        "hide_extra_sk": True,
        "tip": (0.0, 55.0, 8.0),
        "grip": (0.0, 6.0, 2.0),
        "screen": (0.0, 12.0, 10.0),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Rifle.SK_Rifle",
        "scale": 1.0,
        "mag": 30,
        "sk_parts": {
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Aim.SK_Aim",
            "SK_Left_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Left_Kit.SK_Left_Kit",
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SK_AssaultRifle_Mesh/SK_Magazine_Full.SK_Magazine_Full",
        },
        "sm_parts": {
            "SM_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Butt.SM_Butt",
            "SM_Foregrip": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Foregrip.SM_Foregrip",
            "SM_Reactor": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Reactor.SM_Reactor",
            "SM_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Right_Kit.SM_Right_Kit",
            "SM_Aim_Glass": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Aim_Glass.SM_Aim_Glass",
            "SM_Scheme": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Assault_Rifle_2/AssaultRifle/SM_AssaultRifle_Mesh/SM_Scheme.SM_Scheme",
        },
        "hide_extra_sk": True,
        "tip": (0.0, 55.0, 8.0),
        "grip": (0.0, 6.0, 2.0),
        "screen": (0.0, 12.0, 10.0),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Rifle.SK_Rifle",
        "scale": 1.0,
        "mag": 5,
        "sk_parts": {
            "SK_Butt": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Butt.SK_Butt",
            "SK_Scope": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Scope.SK_Scope",
            "SK_Carrying": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Carrying.SK_Carrying",
            "SK_Bipods": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Bipods.SK_Bipods",
            "SK_Rail": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Rail.SK_Rail",
            "SK_Sleeve": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Sleeve.SK_Sleeve",
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Magazine_Full.SK_Magazine_Full",
            "SK_Sopla": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SK_Rifle_Mesh/SK_Sopla.SK_Sopla",
        },
        "sm_parts": {
            "SM_Glass_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SM_Mesh/SM_Glass_Aim.SM_Glass_Aim",
            "SM_Glass_Front": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Sniper_Rifle/Sniper_Rifle/SM_Mesh/SM_Glass_Front.SM_Glass_Front",
        },
        "hide_extra_sk": True,
        "tip": (0.0, 80.0, 7.0),
        "grip": (0.0, 10.0, 2.0),
        "screen": (0.0, 16.0, 11.0),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Pistol/Pistol/SK_Mesh/SK_Pistol.SK_Pistol",
        "scale": 1.0,
        "mag": 15,
        "sk_parts": {
            "SK_Magazine_Full": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Pistol/Pistol/SK_Mesh/SK_Magazine_Full.SK_Magazine_Full",
        },
        "sm_parts": {},
        "hide_extra_sk": True,
        "tip": (0.0, 22.0, 8.0),
        "grip": (0.0, 2.0, 2.0),
        "screen": (0.0, 6.0, 8.0),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Shotgun.SK_Shotgun",
        "scale": 1.0,
        "mag": 8,
        "sk_parts": {
            "SK_Aim": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Aim.SK_Aim",
            "SK_Left_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Left_Kit.SK_Left_Kit",
            "SK_Right_Kit": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_Shotgun/Shotgun/SK_Mesh/SK_Right_Kit.SK_Right_Kit",
        },
        "sm_parts": {},
        "hide_extra_sk": True,
        "tip": (0.0, 58.0, 7.0),
        "grip": (0.0, 5.0, 2.0),
        "screen": (0.0, 10.0, 9.0),
    },
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun": {
        "body": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_MachineGun.SK_MachineGun",
        "scale": 1.0,
        "mag": 100,
        "sk_parts": {
            "SK_Barrel": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Barrel.SK_Barrel",
            "SK_Control_Handle": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Control_Handle.SK_Control_Handle",
            "SK_Magazine": "/Game/Sci-Fi_Weapon_Starter_Pack/Sci-Fi_MachineGun/MachineGun/SK_MachineGun_Mesh/SK_Magazine.SK_Magazine",
        },
        "sm_parts": {},
        "hide_extra_sk": True,
        "tip": (0.0, 85.0, 8.0),
        "grip": (0.0, 12.0, 2.0),
        "screen": (0.0, 14.0, 12.0),
    },
}

KEEP_NONVIS = {
    "SM_Pistol",
    "GrabComponentSnap",
    "MuzzleLocation",
    "XRMuzzleTip",
    "XRMuzzleTip_0",
    "WeaponFireAudio",
    "WeaponMuzzleFXComp",
    "AmmoHUD",
    "AmmoScreenMesh",
    "AmmoTextRender",
    "Scene",
    "Scene_0",
}


def _comps(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = {}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        if obj is not None:
            out[n] = obj
    return out


def _identity(obj):
    obj.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    obj.set_editor_property("relative_rotation", unreal.Rotator(pitch=0, yaw=0, roll=0))
    obj.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))


def _hide_clear_mesh(obj):
    try:
        if isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property("skeletal_mesh", None)
            try:
                obj.set_editor_property("leader_pose_component", None)
            except Exception:
                pass
        if isinstance(obj, unreal.StaticMeshComponent):
            # don't clear SM_Pistol cube here
            pass
    except Exception:
        pass
    obj.set_editor_property("hidden_in_game", True)
    try:
        obj.set_editor_property("visible", False)
    except Exception:
        pass


def _show(obj):
    obj.set_editor_property("hidden_in_game", False)
    try:
        obj.set_editor_property("visible", True)
    except Exception:
        pass


def _no_col(obj):
    try:
        obj.set_editor_property("collision_profile_name", "NoCollision")
    except Exception:
        pass
    try:
        bi = obj.get_editor_property("body_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass


def _add_sk_or_sm(bp, name: str, is_sk: bool):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    # parent = SM_Pistol root if possible
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    parent = None
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        if n == "SM_Pistol":
            parent = h
            break
    params = unreal.AddNewSubobjectParams()
    if parent:
        params.set_editor_property("parent_handle", parent)
    params.set_editor_property(
        "new_class", unreal.SkeletalMeshComponent if is_sk else unreal.StaticMeshComponent
    )
    try:
        params.set_editor_property("blueprint_context", bp)
    except Exception:
        pass
    try:
        new_h, _reason = sub.add_new_subobject(params)
    except TypeError:
        new_h = sub.add_new_subobject(params)
    if not new_h:
        return False
    try:
        sub.rename_subobject(new_h, name)
    except Exception:
        try:
            sub.rename_subobject(new_h, unreal.Name(name))
        except Exception:
            pass
    return True


def fix_gun(path: str, cfg: dict):
    bp = unreal.load_asset(path)
    allowed_sk = set(cfg["sk_parts"].keys()) | {"SkeletalMesh"}
    allowed_sm = set(cfg["sm_parts"].keys())

    comps = _comps(bp)
    body = comps.get("SkeletalMesh")
    if body is None:
        LOG.append({"err": path, "msg": "no SkeletalMesh"})
        return

    # 1) Body = kit body only, identity transform
    mesh = unreal.load_asset(cfg["body"])
    body.set_editor_property("skeletal_mesh", mesh)
    _identity(body)
    s = float(cfg["scale"])
    body.set_editor_property("relative_scale3d", unreal.Vector(s, s, s))
    _show(body)
    _no_col(body)
    try:
        body.set_editor_property("leader_pose_component", None)
    except Exception:
        pass

    # 2) Hide / clear ANY other mesh that is not part of this kit
    comps = _comps(bp)
    for n, obj in list(comps.items()):
        if n == "SkeletalMesh" or n == "SM_Pistol":
            continue
        if not isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            continue
        if n in allowed_sk or n in allowed_sm:
            continue
        # Extra junk mesh (old kits, wrong guns, SkeletalMesh1, etc.)
        if isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property("skeletal_mesh", None)
            try:
                obj.set_editor_property("leader_pose_component", None)
            except Exception:
                pass
            _hide_clear_mesh(obj)
            LOG.append({"hidden_extra": path.split("/")[-1], "n": n})
        elif isinstance(obj, unreal.StaticMeshComponent) and n.startswith("SM_"):
            # hide non-kit static weapon parts
            obj.set_editor_property("static_mesh", None)
            _hide_clear_mesh(obj)
            LOG.append({"hidden_extra_sm": path.split("/")[-1], "n": n})

    # 3) Ensure and align kit SK parts (leader pose to body)
    for name, mesh_path in cfg["sk_parts"].items():
        comps = _comps(bp)
        if name not in comps:
            _add_sk_or_sm(bp, name, True)
            comps = _comps(bp)
        obj = comps.get(name)
        if obj is None:
            LOG.append({"missing_part": name})
            continue
        m = unreal.load_asset(mesh_path)
        obj.set_editor_property("skeletal_mesh", m)
        _identity(obj)
        try:
            obj.set_editor_property("leader_pose_component", body)
        except Exception:
            try:
                obj.set_leader_pose_component(body)
            except Exception as e:
                LOG.append({"leader_err": name, "e": str(e)})
        _show(obj)
        _no_col(obj)

    # 4) Ensure and align kit SM parts (same identity — pack authored that way)
    for name, mesh_path in cfg["sm_parts"].items():
        comps = _comps(bp)
        if name not in comps:
            _add_sk_or_sm(bp, name, False)
            comps = _comps(bp)
        obj = comps.get(name)
        if obj is None:
            LOG.append({"missing_sm": name})
            continue
        m = unreal.load_asset(mesh_path)
        obj.set_editor_property("static_mesh", m)
        _identity(obj)
        _show(obj)
        _no_col(obj)

    comps = _comps(bp)

    # 5) Physics root cube (hidden)
    root = comps.get("SM_Pistol")
    cube = unreal.load_asset(CUBE)
    phys = unreal.load_asset(PHYS_MAT) if unreal.EditorAssetLibrary.does_asset_exist(PHYS_MAT) else None
    tip = unreal.Vector(*cfg["tip"])
    grip = unreal.Vector(*cfg["grip"])
    length = abs(tip.y) + 20.0
    sy = max(0.3, length / 100.0)
    sx, sz = 0.12, 0.14
    if root and cube:
        root.set_editor_property("static_mesh", cube)
        root.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
        root.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        root.set_editor_property("relative_scale3d", unreal.Vector(sx, sy, sz))
        root.set_editor_property("hidden_in_game", True)
        try:
            root.set_editor_property("visible", False)
        except Exception:
            pass
        try:
            root.set_editor_property("collision_profile_name", "PhysicsActor")
        except Exception:
            pass
        bi = root.get_editor_property("body_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        bi.set_editor_property("linear_damping", 8.0)
        bi.set_editor_property("angular_damping", 40.0)
        if phys:
            try:
                bi.set_editor_property("phys_material_override", phys)
            except Exception:
                pass

    def under(v: unreal.Vector):
        return unreal.Vector(v.x / sx, v.y / sy, v.z / sz)

    grab = comps.get("GrabComponentSnap")
    if grab:
        grab.set_editor_property("relative_location", under(grip))
        grab.set_editor_property("relative_rotation", unreal.Rotator(pitch=85.0, yaw=90.0, roll=0.0))
        try:
            grab.set_editor_property("absolute_scale", True)
        except Exception:
            pass

    muzzle = comps.get("MuzzleLocation")
    if muzzle:
        muzzle.set_editor_property("relative_location", under(tip))
        muzzle.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0))
        try:
            muzzle.set_editor_property("absolute_scale", True)
        except Exception:
            pass

    tip_comp = comps.get("XRMuzzleTip_0") or comps.get("XRMuzzleTip")
    if tip_comp:
        tip_comp.set_editor_property("relative_location", tip)
        tip_comp.set_editor_property("relative_rotation", unreal.Rotator(0, 90, 0))

    # Hide legacy XRMuzzleTip far away junk
    if comps.get("XRMuzzleTip") and tip_comp is not comps.get("XRMuzzleTip"):
        comps["XRMuzzleTip"].set_editor_property("hidden_in_game", True)

    audio = comps.get("WeaponFireAudio")
    if audio:
        audio.set_editor_property("relative_location", tip)
        try:
            audio.set_editor_property("b_visualizes_sound", False)
        except Exception:
            try:
                audio.set_editor_property("visualizes_sound", False)
            except Exception:
                pass

    niag = comps.get("WeaponMuzzleFXComp")
    if niag:
        niag.set_editor_property("relative_location", tip)
        niag.set_editor_property("relative_rotation", unreal.Rotator(0, 90, 0))

    # Ammo readout — small, near gun, not giant billboard
    sx, sy, sz = cfg["screen"]
    screen_pos = unreal.Vector(sx, sy, sz)
    plane = unreal.load_asset(PLANE)
    mat = unreal.load_asset(AMMO_MAT) if unreal.EditorAssetLibrary.does_asset_exist(AMMO_MAT) else None
    for n in ("AmmoHUD", "AmmoScreenMesh", "AmmoTextRender"):
        obj = comps.get(n)
        if not obj:
            continue
        obj.set_editor_property("relative_location", screen_pos)
        obj.set_editor_property("hidden_in_game", False)
        try:
            obj.set_editor_property("visible", True)
        except Exception:
            pass
    screen = comps.get("AmmoScreenMesh")
    if screen and plane:
        screen.set_editor_property("static_mesh", plane)
        screen.set_editor_property("relative_rotation", unreal.Rotator(pitch=0, yaw=0, roll=90))
        screen.set_editor_property("relative_scale3d", unreal.Vector(0.03, 0.03, 0.03))
        if mat:
            try:
                screen.set_material(0, mat)
            except Exception:
                pass
        _no_col(screen)
    text = comps.get("AmmoTextRender")
    if text:
        text.set_editor_property("relative_location", unreal.Vector(sx, sy, sz + 0.5))
        text.set_editor_property("relative_rotation", unreal.Rotator(pitch=0, yaw=90, roll=0))
        try:
            text.set_editor_property("world_size", 5.0)
            text.set_editor_property("text", str(cfg["mag"]))
            text.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
        except Exception:
            pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("CurrentAmmo", int(cfg["mag"]))
        cdo.set_editor_property("MaxAmmo", int(cfg["mag"]))
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(path)

    # Verify: list visible meshes
    comps = _comps(bp)
    vis = []
    for n, obj in comps.items():
        if not isinstance(obj, (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent)):
            continue
        if n == "SM_Pistol":
            continue
        hid = bool(obj.get_editor_property("hidden_in_game"))
        mesh_name = ""
        if isinstance(obj, unreal.SkeletalMeshComponent) and obj.skeletal_mesh:
            mesh_name = obj.skeletal_mesh.get_name()
        if isinstance(obj, unreal.StaticMeshComponent) and obj.static_mesh:
            mesh_name = obj.static_mesh.get_name()
        if mesh_name and not hid:
            vis.append(
                {
                    "n": n,
                    "mesh": mesh_name,
                    "loc": [
                        round(obj.relative_location.x, 1),
                        round(obj.relative_location.y, 1),
                        round(obj.relative_location.z, 1),
                    ],
                    "yaw": round(obj.relative_rotation.yaw, 1),
                    "pitch": round(obj.relative_rotation.pitch, 1),
                }
            )
    LOG.append({"gun": path.split("/")[-1], "visible_meshes": vis})


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
        # Actor yaw 90 so kit (authored along -X) faces usable in XR table layout
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            cls, unreal.Vector(x, y, z), unreal.Rotator(pitch=0, yaw=90, roll=0)
        )
        if actor and actor.root_component:
            actor.root_component.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
            created.append(actor.get_class().get_name())
    unreal.EditorLevelLibrary.save_current_level()
    LOG.append({"respawn": {"deleted": deleted, "created": created}})


def main():
    for path, cfg in GUNS.items():
        try:
            fix_gun(path, cfg)
        except Exception as e:
            LOG.append({"fix_err": path.split("/")[-1], "e": str(e)})
    respawn()
    return {"success": True, "log": LOG}


RESULT = main()
