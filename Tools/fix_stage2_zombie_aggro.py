"""Fix Stage2 zombie aggro: restore AI AggroScan, add pawn ForceAggro with cast, wire Stage2_PVE."""
from __future__ import annotations

import math
import unreal
from cursor_unreal_bridge import blueprint_ops as ops

AIC = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
AIC_C = AIC + ".BP_Zombie_AiController_Base_C"
PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
PAWN_C = PAWN + ".BP_Zombie_Pawn_C"
PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
LEVEL = "/Game/XRFramework/Levels/L_XRTemplate"
XR_C = "/Game/XRFramework/Blueprints/BP_XRPawn.BP_XRPawn_C"
FOREACH = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop"
CENTER = unreal.Vector(9000.0, 1700.0, 20.0)
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[S2Fight] {m}")


def bel():
    return ops._bel()


def pinlib():
    return ops._pinlib()


def find(ed, name=None, title=None, cls=None):
    for n in ed.list_all_nodes() or []:
        if name and n.get_name() == name:
            return n
        if title and ops._node_title(n) == title:
            if cls is None or n.get_class().get_name() == cls:
                return n
    return None


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
    except Exception as e:
        return str(e)


def setpos(n, x, y):
    try:
        ops._set_node_pos(n, x, y)
    except Exception:
        pass


def breakp(n, pname):
    p = pin(n, pname)
    if p:
        try:
            pinlib().break_pin_links(p)
        except Exception:
            pass


def end_pie():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        try:
            les.editor_request_end_play()
        except Exception:
            pass


def fix_ai_aggro():
    aic = ops._load_bp(AIC)
    ed, _ = ops._editor_for(aic, "EventGraph")
    aggro = find(ed, title="AggroScanPlayer", cls="K2Node_CustomEvent")
    getall = find(ed, name="K2Node_CallFunction_8")
    then_links = []
    if aggro and pin(aggro, "then"):
        for cp in pinlib().list_connected_pins(pin(aggro, "then")) or []:
            then_links.append(ops._node_title(pinlib().get_owning_node(cp)))
    log(("aggro_then_before", then_links))
    if aggro and getall and "GetAllActorsOfClass" not in then_links:
        breakp(aggro, "then")
        log(("restore_aggro", connect(aggro, "then", getall, "execute")))

    for nm in ("K2Node_CallFunction_8", "K2Node_CallFunction_2"):
        n = find(ed, name=nm)
        log((nm, setv(n, "ActorClass", XR_C) if n else "missing"))
    log(("idx", setv(find(ed, name="K2Node_CallArrayFunction_3"), "Index", "0")))
    log(("gtB", setv(find(ed, name="K2Node_PromotableOperator_4"), "B", "0")))
    timer = find(ed, name="t0_K2_SetTimer_1")
    log(("fn", setv(timer, "FunctionName", "AggroScanPlayer")))
    log(("time", setv(timer, "Time", "0.5")))
    log(("loop", setv(timer, "bLooping", "true")))
    log(("idelay", setv(timer, "InitialStartDelay", "0.15")))

    aggro_ft = find(ed, name="K2Node_CallFunction_7")
    get_pawn = find(ed, name="t4_GetPlayerPawn_1")
    if aggro_ft and get_pawn:
        breakp(aggro_ft, "Object")
        log(("ft_obj", connect(get_pawn, "ReturnValue", aggro_ft, "Object")))
        setv(get_pawn, "PlayerIndex", "0")

    br = find(ed, name="t0_IfThenElse_1")
    if br and aggro_ft:
        else_links = list(pinlib().list_connected_pins(pin(br, "else")) or [])
        if not else_links:
            log(("else-ft", connect(br, "else", aggro_ft, "execute")))

    unreal.BlueprintEditorLibrary.compile_blueprint(aic)
    log(("aic_status", str(aic.status)))
    unreal.EditorAssetLibrary.save_asset(AIC)


def make_cast(ed, x, y, target_cls):
    cast_n = None
    # Prefer create_node_from_name
    try:
        cast_n = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(float(x), float(y)), [])
    except Exception as e:
        log(("create_cast", str(e)))
    if cast_n:
        for prop in ("target_type", "TargetType"):
            try:
                cast_n.set_editor_property(prop, target_cls)
                log(("cast_prop", prop))
                break
            except Exception as e:
                log((prop, str(e)))
        return cast_n
    # Palette fallbacks
    for pal in (
        "Utilities|Casting|Cast To BP_Zombie_AiController_Base",
        "Cast To BP_Zombie_AiController_Base",
    ):
        res = ops.add_blueprint_nodes(
            asset_path=PAWN,
            nodes=[{"id": "c", "type": "palette", "palette": pal, "x": x, "y": y}],
            compile=False,
            save=False,
        )
        log(("pal", pal, res.get("created")))
        for n in ed.list_all_nodes() or []:
            t = ops._node_title(n)
            if "Cast" in t and "AiController" in t:
                return n
    return None


def fix_pawn_force_aggro():
    bp = ops._load_bp(PAWN)
    ed, _ = ops._editor_for(bp, "EventGraph")

    # Remove prior ForceAggro subgraph (custom event + anything exclusively hanging off it)
    evt = find(ed, title="Event_ForceAggroPlayer", cls="K2Node_CustomEvent")
    if evt:
        visited = set()
        queue = [evt]
        remove = []
        while queue:
            n = queue.pop(0)
            if n.get_name() in visited:
                continue
            visited.add(n.get_name())
            if n is not evt:
                remove.append(n)
            for p in bel().list_all_pins(n) or []:
                for cp in pinlib().list_connected_pins(p) or []:
                    own = pinlib().get_owning_node(cp)
                    if own.get_name() not in visited:
                        queue.append(own)
        if remove:
            ed.remove_nodes(remove)
            log(("removed_force_chain", len(remove)))

    evt = find(ed, title="Event_ForceAggroPlayer", cls="K2Node_CustomEvent")
    if not evt:
        evt = ed.add_custom_event_node("Event_ForceAggroPlayer")
    setpos(evt, 5200, 200)

    gc = ed.add_call_function_node("/Script/Engine.Pawn.GetController")
    setpos(gc, 5450, 320)
    gp = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerPawn")
    setv(gp, "PlayerIndex", "0")
    setpos(gp, 5450, 450)

    aic_cls = unreal.EditorAssetLibrary.load_blueprint_class(AIC)
    cast_n = make_cast(ed, 5700, 200, aic_cls)
    log(("cast", ops._node_title(cast_n) if cast_n else None))
    if cast_n:
        log(("cast_pins", [ops._pin_name(p) for p in bel().list_all_pins(cast_n) or []]))

    ft = ed.add_call_function_node(f"{AIC_C}.Event_ForceTarget")
    setpos(ft, 6100, 200)
    ag = ed.add_call_function_node(f"{AIC_C}.AggroScanPlayer")
    setpos(ag, 6450, 200)

    w = []
    if cast_n:
        w.append(("evt-cast", connect(evt, "then", cast_n, "execute")))
        w.append(("gc-obj", connect(gc, "ReturnValue", cast_n, "Object")))
        as_pin = None
        for p in bel().list_all_pins(cast_n) or []:
            pn = ops._pin_name(p)
            if pn.startswith("As"):
                as_pin = pn
                break
        w.append(("as", as_pin))
        w.append(("cast-ft", connect(cast_n, "then", ft, "execute")))
        if as_pin:
            w.append(("as-ft", connect(cast_n, as_pin, ft, "self")))
            w.append(("as-ag", connect(cast_n, as_pin, ag, "self")))
        w.append(("gp-obj", connect(gp, "ReturnValue", ft, "Object")))
        w.append(("ft-ag", connect(ft, "then", ag, "execute")))
    else:
        w.append(("NO_CAST", "failed"))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log(("pawn_status", str(bp.status)))
    try:
        for n in ed.list_nodes_with_errors() or []:
            log(("ERR", ops._node_title(n)))
    except Exception as e:
        log(("errlist", str(e)))
    unreal.EditorAssetLibrary.save_asset(PAWN)
    log(("pawn_wires", w))
    return cast_n is not None and str(bp.status).endswith("3>")


def rebuild_stage2_pve():
    """Tick: near player once -> ForEach zombies -> Event_ForceAggroPlayer."""
    bp = ops._load_bp(PVE)
    for vn, vt in (("bStarted", "bool"), ("TriggerDist", "float")):
        try:
            ops.add_blueprint_variable(asset_path=PVE, var_name=vn, var_type=vt, compile=False, save=False)
        except Exception as e:
            log((vn, str(e)))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("bStarted", False)
        cdo.set_editor_property("TriggerDist", 1800.0)
    except Exception as e:
        log(("cdo", str(e)))

    ed, _ = ops._editor_for(bp, "EventGraph")
    keep = {"Event BeginPlay", "Event Tick", "Event ActorBeginOverlap"}
    remove = [
        n
        for n in list(ed.list_all_nodes() or [])
        if not (n.get_class().get_name() == "K2Node_Event" and ops._node_title(n) in keep)
    ]
    if remove:
        ed.remove_nodes(remove)

    tick = find(ed, title="Event Tick")
    get_started = ed.add_get_member_variable_node("bStarted")
    set_started = ed.add_set_member_variable_node("bStarted")
    setv(set_started, "bStarted", "true")
    notb = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Not_PreBool")
    br0 = ed.add_branch_node()
    pawn = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerPawn")
    setv(pawn, "PlayerIndex", "0")
    isv = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.IsValid")
    br1 = ed.add_branch_node()
    dist = ed.add_call_function_node("/Script/Engine.Actor.GetDistanceTo")
    get_td = ed.add_get_member_variable_node("TriggerDist")
    lte = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble")
    br2 = ed.add_branch_node()
    getall = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetAllActorsOfClass")
    setv(getall, "ActorClass", PAWN_C)
    loop = ed.add_macro_node(FOREACH)
    force = ed.add_call_function_node(f"{PAWN_C}.Event_ForceAggroPlayer")
    printn = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
    setv(printn, "InString", "Stage2: zombies aggro YOU")
    setv(printn, "bPrintToScreen", "true")
    setv(printn, "Duration", "4.0")

    setpos(get_started, 200, 520)
    setpos(notb, 400, 520)
    setpos(br0, 600, 400)
    setpos(pawn, 800, 560)
    setpos(isv, 1000, 560)
    setpos(br1, 1200, 400)
    setpos(dist, 1400, 560)
    setpos(get_td, 1400, 700)
    setpos(lte, 1650, 560)
    setpos(br2, 1900, 400)
    setpos(set_started, 2200, 400)
    setpos(getall, 2500, 400)
    setpos(loop, 2850, 400)
    setpos(force, 3250, 400)
    setpos(printn, 2850, 200)

    w = []
    w.append(("t-br0", connect(tick, "then", br0, "execute")))
    w.append(("st-not", connect(get_started, "bStarted", notb, "A")))
    w.append(("not-br0", connect(notb, "ReturnValue", br0, "Condition")))
    w.append(("br0-br1", connect(br0, "then", br1, "execute")))
    w.append(("pawn-isv", connect(pawn, "ReturnValue", isv, "Object")))
    w.append(("isv-br1", connect(isv, "ReturnValue", br1, "Condition")))
    w.append(("br1-br2", connect(br1, "then", br2, "execute")))
    w.append(("pawn-dist", connect(pawn, "ReturnValue", dist, "OtherActor")))
    w.append(("dist-lte", connect(dist, "ReturnValue", lte, "A")))
    w.append(("td-lte", connect(get_td, "TriggerDist", lte, "B")))
    w.append(("lte-br2", connect(lte, "ReturnValue", br2, "Condition")))
    w.append(("br2-set", connect(br2, "then", set_started, "execute")))
    setv(set_started, "bStarted", "true")
    w.append(("set-getall", connect(set_started, "then", getall, "execute")))
    w.append(("getall-loop", connect(getall, "then", loop, "Exec")))
    w.append(("actors", connect(getall, "OutActors", loop, "Array")))
    w.append(("loop-force", connect(loop, "LoopBody", force, "execute")))
    w.append(("elem-self", connect(loop, "Array Element", force, "self")))
    w.append(("done", connect(loop, "Completed", printn, "execute")))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log(("pve_status", str(bp.status)))
    try:
        for n in ed.list_nodes_with_errors() or []:
            log(("PVE_ERR", ops._node_title(n)))
    except Exception as e:
        log(("pve_errlist", str(e)))
    unreal.EditorAssetLibrary.save_asset(PVE)
    log(("pve_wires", w))

    # Place/refresh actors
    end_pie()
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(LEVEL)
    except Exception:
        pass

    for a in list(unreal.EditorLevelLibrary.get_all_level_actors() or []):
        if a.get_actor_label().startswith("Stage2_AutoZombie"):
            unreal.EditorLevelLibrary.destroy_actor(a)

    zcls = unreal.EditorAssetLibrary.load_blueprint_class(PAWN)
    spots = [unreal.Vector(9300.0, 2000.0, 98.0), unreal.Vector(8700.0, 2000.0, 98.0)]
    for i, loc in enumerate(spots):
        z = unreal.EditorLevelLibrary.spawn_actor_from_class(
            zcls, loc, unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0)
        )
        z.set_actor_label(f"Stage2_AutoZombie_{i+1}")
        z.set_folder_path("Stages/Stage2/PVE")
        yaw = math.degrees(math.atan2(CENTER.y - loc.y, CENTER.x - loc.x))
        z.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=float(yaw), roll=0.0), False)
        try:
            z.set_editor_property("Health", 8.0)
            z.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
        except Exception:
            pass
        log(("placed", z.get_actor_label(), round(z.get_actor_rotation().yaw, 1)))

    pve = None
    for a in unreal.EditorLevelLibrary.get_all_level_actors() or []:
        if a.get_actor_label() == "Stage2_PVE":
            pve = a
            break
    if not pve:
        pcls = unreal.EditorAssetLibrary.load_blueprint_class(PVE)
        pve = unreal.EditorLevelLibrary.spawn_actor_from_class(pcls, CENTER)
        pve.set_actor_label("Stage2_PVE")
        pve.set_folder_path("Stages/Stage2/PVE")
    else:
        pve.set_actor_location(CENTER, False, True)
    try:
        pve.set_editor_property("bStarted", False)
        pve.set_editor_property("TriggerDist", 1800.0)
    except Exception:
        pass
    for c in pve.get_components_by_class(unreal.PrimitiveComponent):
        if "Click" in c.get_name() or "SpawnMore" in c.get_name():
            try:
                c.set_visibility(False)
                c.set_hidden_in_game(True)
                c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            except Exception:
                pass

    try:
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(), "RebuildNavigation"
        )
    except Exception as e:
        log(("nav", str(e)))

    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorAssetLibrary.save_asset(LEVEL)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


def main():
    end_pie()
    fix_ai_aggro()
    ok = fix_pawn_force_aggro()
    rebuild_stage2_pve()
    return {"log": LOG, "pawn_ok": ok}


RESULT = main()
