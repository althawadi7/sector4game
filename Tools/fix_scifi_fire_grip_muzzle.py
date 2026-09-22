"""Fix SciFi guns: muzzle/grip from kit sockets, DoFire SpawnTransform, ammo decrement, SetOwner on grab."""
from __future__ import annotations

import unreal
import json
import sys

sys.path.insert(0, r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python")
import cursor_unreal_bridge.blueprint_ops as bo

LOG: list[str] = []

GUNS = [
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Pistol",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_1",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_AssaultRifle_2",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_MachineGun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun",
    "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper",
]

# Fallbacks if no live actor / socket (SM_Pistol local space; barrel along -X)
FALLBACK = {
    "BP_XR_SciFi_Pistol": {"muzzle": (-10.0, 0.0, -20.0), "trigger": (-5.5, 0.0, -6.5)},
    "BP_XR_SciFi_AssaultRifle_1": {"muzzle": (-62.0, 0.0, 7.0), "trigger": (-6.5, 0.0, 5.0)},
    "BP_XR_SciFi_AssaultRifle_2": {"muzzle": (-60.0, 0.0, 12.0), "trigger": (-7.5, 0.0, 7.0)},
    "BP_XR_SciFi_MachineGun": {"muzzle": (-129.0, 0.0, -7.0), "trigger": (-9.0, 0.0, 5.0)},
    "BP_XR_SciFi_Shotgun": {"muzzle": (-38.0, 0.0, 3.0), "trigger": (-11.0, 0.0, -2.0)},
    "BP_XR_SciFi_Sniper": {"muzzle": (-102.0, 0.0, 11.0), "trigger": (-6.0, 0.0, 4.5)},
}


def log(msg: str):
    LOG.append(msg)
    unreal.log(f"[SciFiFireGrip] {msg}")


def _subobjs(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = []
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        n = str(lib.get_display_name(data)).replace("_GEN_VARIABLE", "")
        obj = lib.get_object(data)
        out.append((n, h, data, obj))
    return out


def _set_rel(obj, loc, rot=None):
    if obj is None:
        return
    obj.set_editor_property("relative_location", unreal.Vector(*loc))
    if rot is not None:
        obj.set_editor_property("relative_rotation", unreal.Rotator(rot[0], rot[1], rot[2]))


def _measure_sockets_from_level(label: str):
    """Return muzzle/trigger relative to SM_Pistol for a placed actor."""
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if a.get_actor_label() != label and label not in a.get_class().get_name():
            continue
        if "SciFi" not in a.get_class().get_name():
            continue
        root = None
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_name() == "SM_Pistol":
                root = c
                break
        if not root:
            continue
        muzzle = trigger = None
        # Prefer kit child sockets
        bodies = []
        for cac in a.get_components_by_class(unreal.ChildActorComponent):
            ch = cac.child_actor
            if not ch:
                continue
            for c in ch.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.skeletal_mesh:
                    bodies.append(c)
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.skeletal_mesh:
                bodies.append(c)

        def sock_rel(comp, sn):
            try:
                wloc = comp.get_socket_location(sn)
                wrot = comp.get_socket_rotation(sn)
                rtm = root.get_world_transform()
                rel = rtm.inverse_transform_location(wloc)
                rrot = rtm.inverse_transform_rotation(wrot)
                return (rel.x, rel.y, rel.z), (rrot.pitch, rrot.yaw, rrot.roll)
            except Exception:
                return None

        for c in bodies:
            socks = [str(s) for s in c.get_all_socket_names()]
            if muzzle is None:
                for sn in ("muzzle", "barrel", "flash"):
                    if sn in socks:
                        muzzle = sock_rel(c, sn)
                        if muzzle:
                            break
            if trigger is None and "trigger" in socks:
                trigger = sock_rel(c, "trigger")
        if muzzle or trigger:
            return {
                "muzzle": muzzle[0] if muzzle else None,
                "muzzle_rot": muzzle[1] if muzzle else None,
                "trigger": trigger[0] if trigger else None,
            }
    return None


def fix_gun_components(path: str):
    bp = unreal.load_asset(path)
    if not bp:
        log(f"MISSING {path}")
        return
    name = path.rsplit("/", 1)[-1]
    measured = _measure_sockets_from_level(name)
    fb = FALLBACK.get(name, {"muzzle": (-50.0, 0.0, 7.0), "trigger": (-7.0, 0.0, 5.0)})
    mloc = (measured or {}).get("muzzle") or fb["muzzle"]
    tloc = (measured or {}).get("trigger") or fb["trigger"]
    # Fire along -X (kit barrel). Component forward = +X at rot 0 → use yaw 180.
    mrot = (0.0, 180.0, 0.0)
    # Grip slightly below/behind trigger toward stock (+X)
    gloc = (tloc[0] + 2.0, tloc[1], tloc[2] - 2.0)
    # VR snap: keep controller-friendly tilt
    grot = (0.0, 180.0, 0.0)

    comps = {n: obj for n, h, d, obj in _subobjs(bp)}
    # Hide root cube but keep physics
    root = comps.get("SM_Pistol")
    if root:
        try:
            root.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
        except Exception:
            pass

    muzzle = comps.get("MuzzleLocation")
    if muzzle:
        _set_rel(muzzle, mloc, mrot)
        log(f"{name} MuzzleLocation -> {mloc} rot {mrot}")

    # Fix ALL XRMuzzleTip* to real muzzle (tag search uses these)
    for n, obj in comps.items():
        if n.startswith("XRMuzzleTip"):
            _set_rel(obj, mloc, mrot)
            # ensure tag
            try:
                tags = list(obj.get_editor_property("component_tags") or [])
                if "XRMuzzleTip" not in [str(t) for t in tags]:
                    tags.append("XRMuzzleTip")
                    obj.set_editor_property("component_tags", tags)
            except Exception:
                pass
            log(f"{name} {n} -> {mloc}")

    grab = comps.get("GrabComponentSnap")
    if grab:
        _set_rel(grab, gloc, grot)
        log(f"{name} GrabComponentSnap -> {gloc} rot {grot}")

    for n in ("WeaponFireAudio", "WeaponMuzzleFXComp"):
        obj = comps.get(n)
        if obj:
            _set_rel(obj, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            # Attach under MuzzleLocation if possible via relative parent already
            try:
                # ensure parent is MuzzleLocation by setting attach
                pass
            except Exception:
                pass
            # If currently under SM_Pistol with absolute offset, move to muzzle loc
            parent_name = None
            try:
                # relative already under muzzle in some guns at (0,55,8) wrong
                if obj.get_attach_parent() and obj.get_attach_parent().get_name() == "MuzzleLocation":
                    _set_rel(obj, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0) if n == "WeaponFireAudio" else (0.0, 0.0, 0.0))
                else:
                    _set_rel(obj, mloc, mrot if n != "WeaponFireAudio" else (0, 0, 0))
            except Exception:
                _set_rel(obj, mloc, (0, 0, 0))
            log(f"{name} {n} repositioned")

    # Niagara forward: often needs pitch 90 for flash axis — set mild
    fx = comps.get("WeaponMuzzleFXComp")
    if fx:
        try:
            # Keep identity relative to muzzle (muzzle already yaw 180)
            _set_rel(fx, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            if fx.get_attach_parent() is None or (fx.get_attach_parent() and fx.get_attach_parent().get_name() != "MuzzleLocation"):
                _set_rel(fx, mloc, (0.0, 0.0, 0.0))
        except Exception:
            pass

    audio = comps.get("WeaponFireAudio")
    if audio:
        try:
            audio.set_editor_property("auto_activate", False)
            # Make sure sound can play spatially near player
            try:
                audio.set_editor_property("b_override_attenuation", False)
            except Exception:
                pass
            try:
                audio.set_editor_property("volume_multiplier", 1.5)
            except Exception:
                pass
        except Exception:
            pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log(f"{name} saved")


def fix_dofire_spawn_transform():
    """Wire Get MuzzleLocation -> GetWorldTransform -> SpawnActor.SpawnTransform on DoFire path."""
    path = "/Game/XRFramework/Blueprints/BP_Rifle"
    bp = bo._load_bp(path)
    bel = bo._bel()
    pl = bo._pinlib()
    editor, graph = bo._editor_for(bp, "")
    nodes = list(editor.list_all_nodes() or [])

    def title(n):
        return bo._node_title(n)

    # Find DoFire -> ... -> SpawnActor that then links to ServerDoFire
    dofire = None
    for n in nodes:
        if title(n) == "DoFire" and "CustomEvent" in n.get_class().get_name():
            dofire = n
            break
    if not dofire:
        log("DoFire event not found")
        return

    spawn = None
    stack = [dofire]
    seen = set()
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if "SpawnActor" in title(cur):
            # check then -> ServerDoFire
            thenp = bo._find_pin(cur, "then")
            if thenp:
                for cp in list(pl.list_connected_pins(thenp) or []):
                    if "ServerDoFire" in title(pl.get_owning_node(cp)):
                        spawn = cur
        for p in list(bel.list_all_pins(cur) or []):
            if "OUTPUT" not in str(pl.get_pin_direction(p)).upper():
                continue
            for cp in list(pl.list_connected_pins(p) or []):
                stack.append(pl.get_owning_node(cp))

    if not spawn:
        log("DoFire SpawnActor not found")
        return

    spawn_xf_pin = bo._find_pin(spawn, "SpawnTransform")
    # If already linked, skip
    if spawn_xf_pin and list(pl.list_connected_pins(spawn_xf_pin) or []):
        log("SpawnTransform already wired")
    else:
        # Add Get MuzzleLocation + GetWorldTransform near spawn
        try:
            pos = bel.get_node_position(spawn)
            x, y = int(pos.x) - 400, int(pos.y) + 80
        except Exception:
            x, y = 3000, 9900

        get_m = editor.add_get_member_variable_node("MuzzleLocation")
        bel.set_node_position(get_m, unreal.Vector2D(x - 250, y))
        # Call GetWorldTransform on SceneComponent
        gwt = None
        for adder in ("add_call_function_node_on_class", "add_call_function_on_class"):
            fn = getattr(editor, adder, None) or getattr(bel, adder, None)
            if callable(fn):
                try:
                    gwt = fn(unreal.SceneComponent.static_class(), "GetWorldTransform")
                    break
                except Exception:
                    try:
                        gwt = fn(unreal.SceneComponent, "GetWorldTransform")
                        break
                    except Exception as e:
                        log(f"add GetWorldTransform fail: {e}")
        if gwt is None:
            # try ops helper
            try:
                added = bo.add_blueprint_nodes(
                    path,
                    [{"type": "CallFunction", "function": "GetWorldTransform", "class": "SceneComponent", "x": x, "y": y}],
                    graph_name="",
                    compile=False,
                    save=False,
                )
                log(f"ops add nodes: {added}")
            except Exception as e:
                log(f"ops add fail: {e}")
            # refresh
            editor, graph = bo._editor_for(bp, "")
            nodes = list(editor.list_all_nodes() or [])
            # find nearest GetWorldTransform
            for n in nodes:
                if title(n) == "GetWorldTransform" or title(n) == "Get World Transform":
                    gwt = n
                    break

        if gwt is None:
            # Fallback: MakeTransform from GetWorldLocation + GetWorldRotation
            log("Trying MakeTransform fallback")
            try:
                nodes_add = bo.add_blueprint_nodes(
                    path,
                    [
                        {"kind": "CallFunction|SceneComponent|GetWorldLocation", "x": x, "y": y},
                        {"kind": "CallFunction|SceneComponent|GetWorldRotation", "x": x, "y": y + 120},
                        {"kind": "CallFunction|KismetMathLibrary|MakeTransform", "x": x + 280, "y": y + 40},
                    ],
                    graph_name="",
                    compile=False,
                    save=False,
                )
                log(f"make transform nodes: {nodes_add}")
            except Exception as e:
                log(f"make transform add err: {e}")

            editor, graph = bo._editor_for(bp, "")
            # reconnect by title matching near spawn
            links = [
                {"from_node": "Get MuzzleLocation", "from_pin": "MuzzleLocation", "to_node": "GetWorldLocation", "to_pin": "self"},
                {"from_node": "Get MuzzleLocation", "from_pin": "MuzzleLocation", "to_node": "GetWorldRotation", "to_pin": "self"},
                {"from_node": "GetWorldLocation", "from_pin": "ReturnValue", "to_node": "MakeTransform", "to_pin": "Location"},
                {"from_node": "GetWorldRotation", "from_pin": "ReturnValue", "to_node": "MakeTransform", "to_pin": "Rotation"},
                {"from_node": "MakeTransform", "from_pin": "ReturnValue", "to_node": "SpawnActor BP Projectile", "to_pin": "SpawnTransform"},
            ]
            # Multiple Get MuzzleLocation / SpawnActor — use node names
            # Find specific spawn by name
            spawn_name = spawn.get_name()
            getm_name = None
            for n in list(editor.list_all_nodes() or []):
                if title(n) == "Get MuzzleLocation":
                    getm_name = n.get_name()
                    # prefer one we just added - last one
            # reconnect carefully with pinlib using node objects
            get_m_nodes = [n for n in editor.list_all_nodes() if title(n) == "Get MuzzleLocation"]
            gwl = [n for n in editor.list_all_nodes() if title(n) in ("GetWorldLocation", "Get World Location")]
            gwr = [n for n in editor.list_all_nodes() if title(n) in ("GetWorldRotation", "Get World Rotation")]
            mk = [n for n in editor.list_all_nodes() if title(n) == "MakeTransform"]
            # pick nodes closest to spawn
            def near(cands):
                if not cands:
                    return None
                try:
                    sp = bel.get_node_position(spawn)
                    def dist(n):
                        p = bel.get_node_position(n)
                        return (p.x - sp.x) ** 2 + (p.y - sp.y) ** 2
                    return sorted(cands, key=dist)[0]
                except Exception:
                    return cands[-1]

            gm = near(get_m_nodes) or (get_m if get_m else None)
            # If we created get_m earlier
            if "get_m" in dir() and get_m:
                gm = get_m
            n_gwl = near(gwl)
            n_gwr = near(gwr)
            n_mk = near(mk)
            if gm and n_gwl and n_gwr and n_mk and spawn_xf_pin:
                def link(a, ap, b, bpname):
                    pa = bo._find_pin(a, ap)
                    pb = bo._find_pin(b, bpname)
                    if pa and pb:
                        try:
                            pl.try_create_connection(pa, pb)
                            return True
                        except Exception as e:
                            log(f"link fail {ap}->{bpname}: {e}")
                    return False

                link(gm, "MuzzleLocation", n_gwl, "self")
                link(gm, "MuzzleLocation", n_gwr, "self")
                link(n_gwl, "ReturnValue", n_mk, "Location")
                link(n_gwr, "ReturnValue", n_mk, "Rotation")
                link(n_mk, "ReturnValue", spawn, "SpawnTransform")
                log("Wired MakeTransform -> SpawnTransform")
            else:
                log(f"Missing nodes gm={gm} gwl={n_gwl} gwr={n_gwr} mk={n_mk}")
        else:
            bel.set_node_position(gwt, unreal.Vector2D(x, y))
            # connect
            gm = get_m
            pa = bo._find_pin(gm, "MuzzleLocation")
            pb = bo._find_pin(gwt, "self")
            if pa and pb:
                pl.try_create_connection(pa, pb)
            po = bo._find_pin(gwt, "ReturnValue")
            if po and spawn_xf_pin:
                pl.try_create_connection(po, spawn_xf_pin)
            log("Wired GetWorldTransform -> SpawnTransform")

    # Fix Set CurrentAmmo = 0 on DoFire then_0: change to leave alone OR decrement
    # Find Set CurrentAmmo with default 0 in DoFire chain
    editor, graph = bo._editor_for(bp, "")
    pl = bo._pinlib()
    bel = bo._bel()
    nodes = list(editor.list_all_nodes() or [])
    dofire = next(n for n in nodes if title(n) == "DoFire" and "CustomEvent" in n.get_class().get_name())
    set_ammo = None
    stack = [dofire]
    seen = set()
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if title(cur) == "Set CurrentAmmo":
            set_ammo = cur
        for p in list(bel.list_all_pins(cur) or []):
            if "OUTPUT" not in str(pl.get_pin_direction(p)).upper():
                continue
            for cp in list(pl.list_connected_pins(p) or []):
                stack.append(pl.get_owning_node(cp))

    if set_ammo:
        # Break then_0 from Sequence to Set CurrentAmmo and reconnect Sequence then_0 to XRPushKitAmmo skip
        # Better: wire Get CurrentAmmo -> Subtract 1 -> Set
        try:
            pin = bo._find_pin(set_ammo, "CurrentAmmo")
            if pin:
                # if hardcoded 0, we'll add decrement graph
                val = pl.get_pin_value(pin)
                log(f"Set CurrentAmmo value={val}")
        except Exception:
            pass

        # Add get + subtract
        try:
            pos = bel.get_node_position(set_ammo)
            x, y = int(pos.x) - 350, int(pos.y)
        except Exception:
            x, y = 2000, 9800
        get_ammo = editor.add_get_member_variable_node("CurrentAmmo")
        bel.set_node_position(get_ammo, unreal.Vector2D(x, y))
        # int - int
        sub = None
        try:
            sub = editor.add_promotable_operator_node("-")
            bel.set_node_position(sub, unreal.Vector2D(x + 180, y))
        except Exception as e:
            log(f"add subtract fail: {e}")
            try:
                bo.add_blueprint_nodes(
                    path,
                    [{"kind": "CallFunction|KismetMathLibrary|Subtract_IntInt", "x": x + 180, "y": y}],
                    compile=False,
                    save=False,
                )
            except Exception as e2:
                log(f"subtract alt fail: {e2}")

        editor, graph = bo._editor_for(bp, "")
        nodes = list(editor.list_all_nodes() or [])
        # re-find set_ammo
        set_ammo = None
        dofire = None
        for n in nodes:
            if title(n) == "DoFire" and "CustomEvent" in n.get_class().get_name():
                dofire = n
        stack = [dofire]
        seen = set()
        while stack:
            cur = stack.pop()
            if id(cur) in seen:
                continue
            seen.add(id(cur))
            if title(cur) == "Set CurrentAmmo":
                set_ammo = cur
            for p in list(bel.list_all_pins(cur) or []):
                if "OUTPUT" not in str(pl.get_pin_direction(p)).upper():
                    continue
                for cp in list(pl.list_connected_pins(p) or []):
                    stack.append(pl.get_owning_node(cp))

        get_ammo_nodes = [n for n in nodes if title(n) == "Get CurrentAmmo"]
        sub_nodes = [n for n in nodes if "-" in title(n) or "Subtract" in title(n)]
        # use last get near set
        if set_ammo and get_ammo_nodes:
            ga = get_ammo_nodes[-1]
            # break existing links on CurrentAmmo input
            pin = bo._find_pin(set_ammo, "CurrentAmmo")
            if pin:
                try:
                    pl.break_pin_links(pin)
                except Exception:
                    pass
            # find subtract near set
            sn = None
            for n in sub_nodes:
                if title(n) in ("-", "int - int", "integer - integer", "Subtract_IntInt"):
                    sn = n
            if sn is None and sub_nodes:
                sn = sub_nodes[-1]
            if sn:
                # link Get -> A, set B=1, result -> Set
                try:
                    pl.try_create_connection(bo._find_pin(ga, "CurrentAmmo"), bo._find_pin(sn, "A") or bo._find_pin(sn, "In A") or list(bel.list_all_pins(sn))[0])
                except Exception as e:
                    log(f"sub A link: {e}")
                # set B default 1
                for pname in ("B", "In B", "B "):
                    bp_pin = bo._find_pin(sn, pname.strip())
                    if bp_pin:
                        try:
                            pl.set_pin_value(bp_pin, "1")
                        except Exception:
                            pass
                try:
                    outp = bo._find_pin(sn, "ReturnValue") or bo._find_pin(sn, "Result")
                    if outp and pin:
                        pl.try_create_connection(outp, pin)
                        log("Wired ammo decrement")
                except Exception as e:
                    log(f"sub out link: {e}")
            else:
                # last resort: set pin value to not wipe — disconnect set from sequence
                log("No subtract node; breaking Set CurrentAmmo=0 from Sequence")
                # find Sequence then_0
                for n in nodes:
                    if title(n) == "Sequence":
                        then0 = bo._find_pin(n, "then_0")
                        if then0:
                            for cp in list(pl.list_connected_pins(then0) or []):
                                if pl.get_owning_node(cp) == set_ammo:
                                    try:
                                        pl.break_single_pin_link(then0, cp)
                                        log("Broke Sequence then_0 -> Set CurrentAmmo")
                                    except Exception as e:
                                        log(f"break fail: {e}")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log("BP_Rifle DoFire transform/ammo patched")


def fix_set_owner_on_grab():
    """When GrabComponentSnap grabs, SetOwner to the pawn so ServerDoFire works."""
    # Patch BP_GrabComponent or rifle Event Graph OnGrabbed
    grab_paths = [
        "/Game/XRFramework/Blueprints/BP_GrabComponent",
        "/Game/XRFramework/Blueprints/Components/BP_GrabComponent",
    ]
    # find
    found = None
    for p in grab_paths:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            found = p
            break
    if not found:
        # search
        for a in unreal.EditorAssetLibrary.list_assets("/Game/XRFramework", True, False):
            if a.endswith("BP_GrabComponent.BP_GrabComponent") or a.endswith("/BP_GrabComponent"):
                found = a.split(".")[0]
                break
    if not found:
        log("BP_GrabComponent not found — skip SetOwner")
        return

    # On the rifle: simpler approach — in XRFireNow or DoFire start with SetOwner(GetPlayerPawn)
    path = "/Game/XRFramework/Blueprints/BP_Rifle"
    bp = bo._load_bp(path)
    bel = bo._bel()
    pl = bo._pinlib()
    editor, graph = bo._editor_for(bp, "")
    # Insert at start of DoFire: SetOwner(GetPlayerPawn(0))
    nodes = list(editor.list_all_nodes() or [])

    def title(n):
        return bo._node_title(n)

    dofire = next((n for n in nodes if title(n) == "DoFire" and "CustomEvent" in n.get_class().get_name()), None)
    if not dofire:
        return
    # Check if already has SetOwner near DoFire
    for n in nodes:
        if title(n) == "SetOwner":
            log("SetOwner already present")
            return

    try:
        pos = bel.get_node_position(dofire)
        x, y = int(pos.x) + 250, int(pos.y) - 150
    except Exception:
        x, y = -1200, 8000

    try:
        bo.add_blueprint_nodes(
            path,
            [
                {"kind": "CallFunction|GameplayStatics|GetPlayerPawn", "x": x, "y": y + 80},
                {"kind": "CallFunction|Actor|SetOwner", "x": x + 300, "y": y},
            ],
            compile=False,
            save=False,
        )
    except Exception as e:
        log(f"add SetOwner nodes: {e}")
        return

    editor, graph = bo._editor_for(bp, "")
    pl = bo._pinlib()
    bel = bo._bel()
    nodes = list(editor.list_all_nodes() or [])
    dofire = next(n for n in nodes if title(n) == "DoFire" and "CustomEvent" in n.get_class().get_name())
    set_owner = next((n for n in nodes if title(n) == "SetOwner"), None)
    get_pawn = next((n for n in nodes if title(n) == "GetPlayerPawn"), None)
    print_n = None
    # DoFire currently -> PrintString
    thenp = bo._find_pin(dofire, "then")
    first = None
    if thenp:
        conns = list(pl.list_connected_pins(thenp) or [])
        if conns:
            first = pl.get_owning_node(conns[0])
            print_n = first

    if set_owner and get_pawn and thenp:
        # Break DoFire -> Print
        try:
            pl.break_pin_links(thenp)
        except Exception:
            pass
        # DoFire -> SetOwner -> Print
        pl.try_create_connection(thenp, bo._find_pin(set_owner, "execute"))
        if print_n:
            pl.try_create_connection(bo._find_pin(set_owner, "then"), bo._find_pin(print_n, "execute"))
        # GetPlayerPawn -> NewOwner
        pl.try_create_connection(bo._find_pin(get_pawn, "ReturnValue"), bo._find_pin(set_owner, "NewOwner"))
        # PlayerIndex 0 default
        log("Wired DoFire SetOwner(GetPlayerPawn)")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)


def fix_live_actors():
    """Apply same transforms to placed level instances."""
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if "SciFi" not in a.get_class().get_name():
            continue
        name = a.get_class().get_name().replace("_C", "")
        fb = FALLBACK.get(name)
        measured = _measure_sockets_from_level(a.get_actor_label())
        if not fb and not measured:
            continue
        mloc = (measured or {}).get("muzzle") or fb["muzzle"]
        tloc = (measured or {}).get("trigger") or fb["trigger"]
        mrot = unreal.Rotator(0, 180, 0)
        gloc = unreal.Vector(tloc[0] + 2.0, tloc[1], tloc[2] - 2.0)
        for c in a.get_components_by_class(unreal.SceneComponent):
            n = c.get_name()
            if n == "MuzzleLocation" or n.startswith("XRMuzzleTip"):
                c.set_relative_location(unreal.Vector(*mloc))
                c.set_relative_rotation(mrot)
            elif n == "GrabComponentSnap":
                c.set_relative_location(gloc)
                c.set_relative_rotation(mrot)
            elif n in ("WeaponFireAudio", "WeaponMuzzleFXComp"):
                # zero if parented to muzzle else absolute muzzle
                parent = c.get_attach_parent()
                if parent and parent.get_name() == "MuzzleLocation":
                    c.set_relative_location(unreal.Vector(0, 0, 0))
                    c.set_relative_rotation(unreal.Rotator(0, 0, 0))
                else:
                    c.set_relative_location(unreal.Vector(*mloc))
        # Fix root pitch if wrongly 90
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_name() == "SM_Pistol":
                r = c.relative_rotation
                if abs(r.pitch - 90) < 1:
                    c.set_relative_rotation(unreal.Rotator(0, 0, 0))
                    log(f"live {a.get_actor_label()} cleared root pitch 90")
        log(f"live {a.get_actor_label()} muzzle={mloc}")


def main():
    for p in GUNS:
        try:
            fix_gun_components(p)
        except Exception as e:
            log(f"ERR components {p}: {e}")
    try:
        fix_dofire_spawn_transform()
    except Exception as e:
        log(f"ERR dofire: {e}")
    try:
        fix_set_owner_on_grab()
    except Exception as e:
        log(f"ERR setowner: {e}")
    try:
        fix_live_actors()
    except Exception as e:
        log(f"ERR live: {e}")

    out = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_fix_fire_grip_log.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=2)
    return LOG


RESULT = {"log": main()[-40:], "n": len(LOG)}
