"""Fix zombie AnimBlueprint None, ForceAggro empty, bullet overlap, locomotion."""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
PAWN_C = PAWN + ".BP_Zombie_Pawn_C"
AIC = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
AIC_C = AIC + ".BP_Zombie_AiController_Base_C"
XR = "/Game/XRFramework/Blueprints/BP_XRPawn"
XR_C = XR + ".BP_XRPawn_C"
ANIMBP = "/Game/Zombie/Animations/AnimBP_Zombie"
PROJ = "/Game/XRFramework/Blueprints/BP_Projectile"
AGGRO_RANGE = 2200.0
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[ZombieFix] {m}")


def load_bp(path: str):
    name = path.rsplit("/", 1)[-1]
    bp = unreal.load_asset(f"{path}.{name}")
    if not bp:
        bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        raise RuntimeError(f"missing {path}")
    return bp


ops._load_bp = load_bp


def bel():
    return ops._bel()


def pinlib():
    return ops._pinlib()


def find(ed, title=None, cls=None):
    for n in ed.list_all_nodes() or []:
        if title and ops._node_title(n) == title:
            if cls is None or n.get_class().get_name() == cls:
                return n
    return None


def find_all(ed, title=None, substr=None):
    out = []
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if title and t == title:
            out.append(n)
        elif substr and substr in t:
            out.append(n)
    return out


def pin(n, name):
    if not n:
        return None
    for p in bel().list_all_pins(n) or []:
        if ops._pin_name(p) == name:
            return p
    return None


def connect(a, ap, b, bp):
    pa, pb = pin(a, ap), pin(b, bp)
    if not pa or not pb:
        return f"miss {ap}->{bp}"
    return "ok" if pinlib().try_create_connection(pa, pb) else f"no {ap}->{bp}"


def setv(n, pname, val):
    p = pin(n, pname)
    if not p:
        return f"miss {pname}"
    try:
        pinlib().set_pin_value(p, str(val))
        return "ok"
    except Exception:
        try:
            pinlib().set_pin_default_value(p, str(val))
            return "ok"
        except Exception as e:
            return str(e)


def breakp(n, pname):
    p = pin(n, pname)
    if p:
        try:
            pinlib().break_pin_links(p)
        except Exception:
            pass


def as_pin(n):
    for p in bel().list_all_pins(n) or []:
        if ops._pin_name(p).startswith("As"):
            return ops._pin_name(p)
    return None


def save(bp, path):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    try:
        unreal.EditorAssetLibrary.save_asset(path)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([bp.get_package()], True)
    log(("saved", path, str(bp.status)))


def fix_anim_blueprint():
    """BeginPlay: mesh anim instance -> Cast AnimBP_Zombie -> Set AnimBlueprint, then HP chain."""
    bp = load_bp(PAWN)
    ed, _ = ops._editor_for(bp, "EventGraph")

    begin = find(ed, title="Event BeginPlay")
    set_max = find(ed, title="Set MaxHealth")
    # existing first node after begin
    if not begin:
        log("no BeginPlay")
        return

    # Idempotent marker
    for n in find_all(ed, title="PrintString"):
        p = pin(n, "InString")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if v == "ANIM_BP_INIT":
            log("anim init already present")
            # still ensure variable path works - fall through to verify wiring
            break
    else:
        # add nodes
        r = ops.add_blueprint_nodes(
            asset_path=PAWN,
            graph_name="EventGraph",
            nodes=[
                {
                    "id": "getmesh",
                    "type": "call",
                    "function_path": "/Script/Engine.Character.GetMesh",
                    "x": -400,
                    "y": -200,
                },
                {
                    "id": "getai",
                    "type": "call",
                    "function_path": "/Script/Engine.SkeletalMeshComponent.GetAnimInstance",
                    "x": -150,
                    "y": -200,
                },
                {
                    "id": "cast",
                    "type": "cast",
                    "class_path": ANIMBP,
                    "x": 100,
                    "y": -200,
                },
                {"id": "seta", "type": "variable_set", "var_name": "AnimBlueprint", "x": 400, "y": -200},
                {
                    "id": "mark",
                    "type": "call",
                    "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
                    "x": 650,
                    "y": -350,
                    "pin_defaults": {
                        "InString": "ANIM_BP_INIT",
                        "bPrintToScreen": "false",
                        "bPrintToLog": "false",
                        "Duration": "0.1",
                    },
                },
            ],
            compile=False,
            save=False,
        )
        log(("anim_add", str(r)[:500]))

    ed, _ = ops._editor_for(bp, "EventGraph")
    begin = find(ed, title="Event BeginPlay")
    getmesh = find(ed, title="GetMesh") or find(ed, title="Get Mesh")
    getai = find(ed, title="Get Anim Instance") or find(ed, title="GetAnimInstance")
    # Prefer cast to AnimBP_Zombie
    cast = None
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if "AnimBP_Zombie" in t or t == "Cast To AnimBP_Zombie":
            cast = n
            break
    if not cast:
        # try create via palette name like flinch script
        try:
            cast = ed.create_node_from_name(
                "Utilities|Casting|CastToAnimBP_Zombie", unreal.Vector2D(100, -200), []
            )
            log(("cast_palette", bool(cast), ops._node_title(cast) if cast else None))
        except Exception as e:
            log(("cast_palette_err", str(e)[:100]))
    if not cast:
        # DynamicCast + set target
        try:
            anim_cls = unreal.BlueprintEditorLibrary.generated_class(load_bp(ANIMBP))
            cast = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(100, -200), [])
            if cast:
                try:
                    cast.set_editor_property("target_type", anim_cls)
                except Exception:
                    pass
            log(("dyn_cast", bool(cast), ops._node_title(cast) if cast else None))
        except Exception as e:
            log(("dyn_err", str(e)[:100]))

    seta = find(ed, title="Set AnimBlueprint")
    if not seta:
        seta = ed.add_set_member_variable_node("AnimBlueprint")

    mark = None
    for n in find_all(ed, title="PrintString"):
        p = pin(n, "InString")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if v == "ANIM_BP_INIT":
            mark = n

    # What BeginPlay currently goes to
    next_after = None
    p = pin(begin, "then")
    for cp in pinlib().list_connected_pins(p) or []:
        next_after = pinlib().get_owning_node(cp)
        break

    wires = []
    if begin and getmesh and getai and cast and seta:
        breakp(begin, "then")
        # GetMesh may need self - usually implicit
        wires.append(connect(begin, "then", getmesh, "execute") if pin(getmesh, "execute") else "mesh_pure")
        if wires[-1] != "ok" and wires[-1] != "mesh_pure":
            # pure getters - wire data only
            pass
        # data: GetMesh -> GetAnimInstance.target/self
        for pn in ("self", "Target"):
            if pin(getai, pn):
                wires.append(connect(getmesh, "ReturnValue", getai, pn))
                break
        wires.append(connect(getai, "ReturnValue", cast, "Object"))
        # exec: Begin -> SetAnim or Cast
        if pin(cast, "execute"):
            # pure mesh/anim - start at cast with Begin
            wires.append(connect(begin, "then", cast, "execute"))
            wires.append(connect(cast, "then", seta, "execute"))
            asp = as_pin(cast)
            if asp:
                wires.append(connect(cast, asp, seta, "AnimBlueprint"))
            # CastFailed still continue
            cont = next_after
            if mark:
                wires.append(connect(seta, "then", mark, "execute"))
                if cont and cont is not mark:
                    wires.append(connect(mark, "then", cont, "execute"))
                wires.append(connect(cast, "CastFailed", mark, "execute"))
            elif cont:
                wires.append(connect(seta, "then", cont, "execute"))
                wires.append(connect(cast, "CastFailed", cont, "execute"))
        else:
            wires.append("cast_no_exec")
    else:
        log(("anim_missing", bool(begin), bool(getmesh), bool(getai), bool(cast), bool(seta)))
        if begin and next_after:
            connect(begin, "then", next_after, "execute")

    log(("anim_wires", wires))
    save(bp, PAWN)


def fix_force_aggro():
    """Restore Event_ForceAggroPlayer -> Cast XR -> ForceTarget on AI."""
    bp = load_bp(PAWN)
    ed, _ = ops._editor_for(bp, "EventGraph")
    evt = find(ed, title="Event_ForceAggroPlayer", cls="K2Node_CustomEvent")
    if not evt:
        evt = ed.add_custom_event_node("Event_ForceAggroPlayer")
        log("added ForceAggro event")

    # If already wired, skip
    if pinlib().list_connected_pins(pin(evt, "then") or pin(evt, "execute") or list(bel().list_all_pins(evt) or [])[0]):
        # check if goes somewhere useful
        linked = False
        for p in bel().list_all_pins(evt) or []:
            if pinlib().list_connected_pins(p):
                linked = True
        if linked:
            # verify ForceTarget exists downstream - if then empty we rebuild
            pthen = pin(evt, "then")
            if pthen and (pinlib().list_connected_pins(pthen) or []):
                log("ForceAggro already wired")
                return

    r = ops.add_blueprint_nodes(
        asset_path=PAWN,
        graph_name="EventGraph",
        nodes=[
            {
                "id": "gp",
                "type": "call",
                "function_path": "/Script/Engine.GameplayStatics.GetPlayerPawn",
                "x": 200,
                "y": 2200,
                "pin_defaults": {"PlayerIndex": "0"},
            },
            {"id": "cxr", "type": "cast", "class_path": XR, "x": 450, "y": 2200},
            {
                "id": "dist",
                "type": "call",
                "function_path": "/Script/Engine.Actor.GetDistanceTo",
                "x": 700,
                "y": 2400,
            },
            {
                "id": "lte",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble",
                "x": 950,
                "y": 2400,
                "pin_defaults": {"B": str(AGGRO_RANGE)},
            },
            {"id": "br", "type": "branch", "x": 1200, "y": 2200},
            {
                "id": "gc",
                "type": "call",
                "function_path": "/Script/Engine.Pawn.GetController",
                "x": 1200,
                "y": 2500,
            },
            {"id": "cai", "type": "cast", "class_path": AIC, "x": 1450, "y": 2200},
            {
                "id": "ft",
                "type": "call",
                "function_path": f"{AIC_C}:Event_ForceTarget",
                "x": 1750,
                "y": 2200,
            },
        ],
        compile=False,
        save=False,
    )
    log(("force_add", str(r)[:600]))

    ed, _ = ops._editor_for(bp, "EventGraph")
    evt = find(ed, title="Event_ForceAggroPlayer", cls="K2Node_CustomEvent")
    gp = find_all(ed, title="GetPlayerPawn")[-1]
    # casts
    cxr = None
    for n in ed.list_all_nodes() or []:
        if "XRPawn" in ops._node_title(n) or ops._node_title(n) == "Cast To BP_XRPawn":
            cxr = n
    if not cxr:
        # bad cast may appear - find newest DynamicCast near force
        for n in ed.list_all_nodes() or []:
            if ops._node_title(n) in ("Bad cast node",) and not (pinlib().list_connected_pins(pin(n, "execute")) or []):
                cxr = n
                # try set target
                try:
                    xr_cls = unreal.BlueprintEditorLibrary.generated_class(load_bp(XR))
                    n.set_editor_property("target_type", xr_cls)
                except Exception:
                    pass

    # Prefer create cast via palette
    if not cxr or ops._node_title(cxr) == "Bad cast node" or "PrintString" in ops._node_title(cxr):
        try:
            xr_cls = unreal.BlueprintEditorLibrary.generated_class(load_bp(XR))
            cxr = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(450, 2200), [])
            try:
                cxr.set_editor_property("target_type", xr_cls)
            except Exception as e:
                log(("xr_tt", str(e)[:80]))
            log(("xr_cast", ops._node_title(cxr) if cxr else None))
        except Exception as e:
            log(("xr_create", str(e)[:100]))

    dist = find_all(ed, title="GetDistanceTo")[-1] if find_all(ed, title="GetDistanceTo") else None
    lte = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) in ("float <= float", "Timespan <= Timespan"):
            # unconnected B=2200 likely ours
            try:
                b = pinlib().get_pin_value(pin(n, "B"))
            except Exception:
                b = ""
            if str(b).startswith("2200") or not (pinlib().list_connected_pins(pin(n, "ReturnValue")) or []):
                lte = n
    if lte:
        setv(lte, "B", str(AGGRO_RANGE))
        # promote by connecting floats later

    branches = find_all(ed, title="Branch")
    br = branches[-1] if branches else None
    gc = find_all(ed, title="GetController")[-1] if find_all(ed, title="GetController") else None

    cai = None
    for n in ed.list_all_nodes() or []:
        if "AiController" in ops._node_title(n) or "AIController" in ops._node_title(n):
            if "Cast" in ops._node_title(n) or n.get_class().get_name() == "K2Node_DynamicCast":
                cai = n
    if not cai:
        try:
            aic_cls = unreal.BlueprintEditorLibrary.generated_class(load_bp(AIC))
            cai = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(1450, 2200), [])
            try:
                cai.set_editor_property("target_type", aic_cls)
            except Exception:
                pass
        except Exception as e:
            log(("ai_cast", str(e)[:80]))

    ft = None
    for n in find_all(ed, substr="ForceTarget"):
        if n.get_class().get_name() == "K2Node_CallFunction":
            # prefer unconnected exec
            if not (pinlib().list_connected_pins(pin(n, "execute")) or []):
                ft = n
    if not ft:
        for n in find_all(ed, substr="ForceTarget"):
            if n.get_class().get_name() == "K2Node_CallFunction":
                ft = n

    wires = []
    if evt and gp and cxr and br and gc and cai and ft and dist and lte:
        breakp(evt, "then")
        wires.append(connect(evt, "then", cxr, "execute"))
        wires.append(connect(gp, "ReturnValue", cxr, "Object"))
        wires.append(connect(cxr, "then", br, "execute"))
        asp = as_pin(cxr)
        if asp:
            wires.append(connect(cxr, asp, dist, "OtherActor"))
        wires.append(connect(dist, "ReturnValue", lte, "A"))
        setv(lte, "B", str(AGGRO_RANGE))
        wires.append(connect(lte, "ReturnValue", br, "Condition"))
        wires.append(connect(br, "then", cai, "execute"))
        wires.append(connect(gc, "ReturnValue", cai, "Object"))
        wires.append(connect(cai, "then", ft, "execute"))
        # ForceTarget Object = XR pawn
        if asp:
            wires.append(connect(cxr, asp, ft, "Object"))
        else:
            wires.append(connect(gp, "ReturnValue", ft, "Object"))
    else:
        log(
            (
                "force_missing",
                bool(evt),
                bool(gp),
                bool(cxr),
                bool(br),
                bool(gc),
                bool(cai),
                bool(ft),
                bool(dist),
                bool(lte),
            )
        )

    log(("force_wires", wires))
    save(bp, PAWN)


def fix_collision():
    """Ensure zombie mesh/capsule overlap projectiles; projectile overlaps pawns."""
    OV = unreal.CollisionResponseType.ECR_OVERLAP
    bp = load_bp(PAWN)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    changed = []
    for c in cdo.get_components_by_class(unreal.PrimitiveComponent):
        if not isinstance(c, (unreal.CapsuleComponent, unreal.SkeletalMeshComponent)):
            continue
        try:
            c.set_editor_property("generate_overlap_events", True)
            c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_DYNAMIC, OV)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PHYSICS_BODY, OV)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_STATIC, unreal.CollisionResponseType.ECR_BLOCK)
            changed.append(c.get_name())
        except Exception as e:
            log(("col_err", c.get_name(), str(e)[:80]))
    log(("zombie_col", changed))

    # Projectile
    pbp = load_bp(PROJ)
    pcdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(pbp))
    pchanged = []
    for c in pcdo.get_components_by_class(unreal.PrimitiveComponent):
        try:
            c.set_editor_property("generate_overlap_events", True)
            c.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
            # Object type WorldDynamic commonly
            try:
                c.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
            except Exception:
                pass
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN, OV)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_STATIC, unreal.CollisionResponseType.ECR_BLOCK)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_DYNAMIC, OV)
            pchanged.append(c.get_name())
        except Exception as e:
            log(("proj_col_err", str(e)[:80]))
    # Also try named SphereCollision via find
    try:
        scs = getattr(pbp, "simple_construction_script", None)
        if scs:
            for node in scs.get_all_nodes():
                try:
                    name = str(node.get_variable_name())
                except Exception:
                    name = "?"
                if "Sphere" in name or "Collision" in name:
                    log(("proj_scs", name))
    except Exception as e:
        log(("scs", str(e)[:60]))

    log(("proj_col", pchanged))
    save(bp, PAWN)
    save(pbp, PROJ)


def fix_locomotion():
    WALK = 90.0
    RUN = 150.0
    bp = load_bp(PAWN)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    for prop, val in (("WalkingSpeed", WALK), ("RunningSpeed", RUN), ("bUseRunSpeed", False)):
        try:
            cdo.set_editor_property(prop, val)
        except Exception as e:
            log(("speed", prop, str(e)[:60]))
    mc = cdo.get_editor_property("character_movement")
    if mc:
        mc.set_editor_property("max_walk_speed", WALK)
        mc.set_editor_property("max_acceleration", 480.0)
        mc.set_editor_property("braking_deceleration_walking", 720.0)
        mc.set_editor_property("bOrientRotationToMovement", False)
        mc.set_editor_property("bUseControllerDesiredRotation", True)
        mc.set_editor_property("rotation_rate", unreal.Rotator(0, 180, 0))
    save(bp, PAWN)
    log("locomotion ok")


def main():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        try:
            les.editor_request_end_play()
        except Exception:
            pass
    fix_anim_blueprint()
    fix_force_aggro()
    fix_collision()
    fix_locomotion()
    return {"log": LOG[-50:]}


RESULT = main()
