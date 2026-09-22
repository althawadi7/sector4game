"""Fix: zombies SEARCH until XR player is near, then chase/fight. Randomize full character kit."""
from __future__ import annotations

import math
import unreal
from cursor_unreal_bridge import blueprint_ops as ops

AIC = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
AIC_C = AIC + ".BP_Zombie_AiController_Base_C"
PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
PAWN_C = PAWN + ".BP_Zombie_Pawn_C"
RAND = "/Game/Zombie/Blueprints/CharacterCreatorSimple/BP_Zombie_CharacterRandomizer"
PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
LEVEL = "/Game/XRFramework/Levels/L_XRTemplate"
XR = "/Game/XRFramework/Blueprints/BP_XRPawn"
XR_C = XR + ".BP_XRPawn_C"
FOREACH = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop"
CENTER = unreal.Vector(9000.0, 1700.0, 20.0)
AGGRO_RANGE = 2200.0
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[ZombieHunt] {m}")


def load_bp(path: str):
    name = path.rsplit("/", 1)[-1]
    bp = unreal.load_asset(f"{path}.{name}")
    if not bp:
        bp = unreal.load_asset(path)
    if not bp:
        raise RuntimeError(f"missing {path}")
    return bp


ops._load_bp = load_bp


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


def fix_randomizer():
    """Ensure kit randomizes body type / materials / jaw every spawn."""
    bp = load_bp(RAND)
    cls = bp.generated_class()
    cdo = unreal.get_default_object(cls)
    for prop, val in (("Random_BodyType", True), ("SelectedBodyType", 0)):
        try:
            cdo.set_editor_property(prop, val)
            log(("rand_cdo", prop, val))
        except Exception as e:
            log(("rand_cdo_err", prop, str(e)))

    # Ensure EventGraph BeginPlay -> CharacterStuff stays wired
    ed, _ = ops._editor_for(bp, "EventGraph")
    begin = find(ed, title="Event BeginPlay")
    call = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "CharacterStuff" and n.get_class().get_name() == "K2Node_CallFunction":
            call = n
            break
    if begin and call:
        breakp(begin, "then")
        log(("begin-char", connect(begin, "then", call, "execute")))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    try:
        unreal.EditorAssetLibrary.save_asset(RAND)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([bp.get_package()], True)
    log(("rand_status", str(bp.status)))

    # Pawn CDO: ensure child randomizer present; mesh tagged
    pawn = load_bp(PAWN)
    pcls = pawn.generated_class()
    pcdo = unreal.get_default_object(pcls)
    mesh = pcdo.get_editor_property("mesh")
    if mesh:
        tags = list(mesh.get_editor_property("component_tags") or [])
        if "ZombieMesh" not in [str(t) for t in tags]:
            tags.append("ZombieMesh")
            mesh.set_editor_property("component_tags", tags)
            log("added ZombieMesh tag")
        else:
            log("ZombieMesh tag ok")
    unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
    try:
        unreal.EditorAssetLibrary.save_asset(PAWN)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([pawn.get_package()], True)


def rebuild_aggro_scan():
    """
    AggroScanPlayer:
      GetControlledPawn -> GetAllActorsOfClass(BP_XRPawn) -> ForEach
      keep nearest within AGGRO_RANGE -> ForceTarget(that)
      if none: ClearValue(Key_TargetActor)  [search/roam, NO attack]
    Never ForceTarget Spectator / distant player.
    """
    aic = load_bp(AIC)
    ed, _ = ops._editor_for(aic, "EventGraph")

    aggro = find(ed, title="AggroScanPlayer", cls="K2Node_CustomEvent")
    if not aggro:
        aggro = ed.add_custom_event_node("AggroScanPlayer")
        setpos(aggro, 2500, 3500)

    # Detach old AggroScan then chain only (leave other systems alone)
    breakp(aggro, "then")

    # Build fresh hunt chain far to the right so we don't tangle old nodes
    X, Y = 5200, 5200
    get_pawn_self = ed.add_call_function_node("/Script/AIModule.AIController.K2_GetPawn")
    setpos(get_pawn_self, X, Y + 80)

    getall = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetAllActorsOfClass")
    setv(getall, "ActorClass", XR_C)
    setpos(getall, X + 250, Y)

    loop = ed.add_macro_node(FOREACH)
    setpos(loop, X + 550, Y)

    # Locals via pins: distance compare
    # For simplicity: use GetPlayerPawn only IF cast to XR succeeds AND distance OK
    # Cleaner single-path without ForEach nearest: GetAllActors + Length + Get[0] is wrong.
    # Use: ForEach -> GetDistanceTo(self pawn, element) -> Branch <= AGGRO -> ForceTarget
    # First valid in range wins; Completed clears if never set — use a bool bFound.

    # Add bHuntFound if missing
    try:
        ops.add_blueprint_variable(
            asset_path=AIC, var_name="bHuntFound", var_type="bool", compile=False, save=False
        )
    except Exception as e:
        log(("bHuntFound", str(e)))

    # Simpler robust approach without foreach nearest complexity:
    # Sequence:
    #  1) Set bHuntFound=false
    #  2) GetAllActors XR
    #  3) ForEach: dist check -> if near, ForceTarget + set found true (only if not found yet)
    #  4) Completed: if not found -> ClearValue Key_TargetActor

    set_found_false = ed.add_set_member_variable_node("bHuntFound")
    setv(set_found_false, "bHuntFound", "false")
    setpos(set_found_false, X + 100, Y - 120)

    get_found = ed.add_get_member_variable_node("bHuntFound")
    setpos(get_found, X + 900, Y + 200)
    not_found = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Not_PreBool")
    setpos(not_found, X + 1100, Y + 200)

    br_not_yet = ed.add_branch_node()
    setpos(br_not_yet, X + 1300, Y)

    # Distance: GetActorLocation controlled, GetActorLocation element, VSize, <=
    loc_self = ed.add_call_function_node("/Script/Engine.Actor.K2_GetActorLocation")
    setpos(loc_self, X + 900, Y + 320)
    loc_other = ed.add_call_function_node("/Script/Engine.Actor.K2_GetActorLocation")
    setpos(loc_other, X + 900, Y + 460)
    # Use GetDistanceTo on controlled pawn
    dist = ed.add_call_function_node("/Script/Engine.Actor.GetDistanceTo")
    setpos(dist, X + 1150, Y + 360)
    lte = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble")
    setv(lte, "B", str(AGGRO_RANGE))
    setpos(lte, X + 1400, Y + 360)
    br_near = ed.add_branch_node()
    setpos(br_near, X + 1600, Y)

    force = ed.add_call_function_node(f"{AIC_C}.Event_ForceTarget")
    setpos(force, X + 1900, Y)

    set_found_true = ed.add_set_member_variable_node("bHuntFound")
    setv(set_found_true, "bHuntFound", "true")
    setpos(set_found_true, X + 2200, Y)

    # Completed: if !bHuntFound -> ClearValue Key_TargetActor
    get_found2 = ed.add_get_member_variable_node("bHuntFound")
    not_found2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Not_PreBool")
    br_clear = ed.add_branch_node()
    setpos(get_found2, X + 550, Y + 280)
    setpos(not_found2, X + 750, Y + 280)
    setpos(br_clear, X + 950, Y + 200)

    get_bb = ed.add_call_function_node("/Script/AIModule.AIBlueprintHelperLibrary.GetBlackboard")
    setpos(get_bb, X + 1200, Y + 200)
    clear = ed.add_call_function_node("/Script/AIModule.BlackboardComponent.ClearValue")
    setpos(clear, X + 1500, Y + 200)
    key = ed.add_get_member_variable_node("Key_TargetActor")
    setpos(key, X + 1500, Y + 360)

    # Optional: print when cleared / found
    print_hunt = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
    setv(print_hunt, "InString", "Zombie: hunting YOU")
    setv(print_hunt, "bPrintToScreen", "true")
    setv(print_hunt, "Duration", "1.5")
    setpos(print_hunt, X + 2500, Y)

    print_search = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
    setv(print_search, "InString", "Zombie: searching...")
    setv(print_search, "bPrintToScreen", "true")
    setv(print_search, "Duration", "1.0")
    setpos(print_search, X + 1800, Y + 200)

    w = []
    w.append(("aggro-setF", connect(aggro, "then", set_found_false, "execute")))
    w.append(("setF-getall", connect(set_found_false, "then", getall, "execute")))
    w.append(("getall-loop", connect(getall, "then", loop, "Exec")))
    w.append(("actors", connect(getall, "OutActors", loop, "Array")))

    # LoopBody: if !bHuntFound AND near -> ForceTarget
    w.append(("loop-br", connect(loop, "LoopBody", br_not_yet, "execute")))
    w.append(("found-not", connect(get_found, "bHuntFound", not_found, "A")))
    w.append(("not-cond", connect(not_found, "ReturnValue", br_not_yet, "Condition")))
    w.append(("br-near", connect(br_not_yet, "then", br_near, "execute")))

    # dist: self=controlled pawn, Other=array element
    w.append(("pawn-distself", connect(get_pawn_self, "ReturnValue", dist, "self")))
    w.append(("elem-other", connect(loop, "Array Element", dist, "OtherActor")))
    w.append(("dist-lte", connect(dist, "ReturnValue", lte, "A")))
    setv(lte, "B", str(AGGRO_RANGE))
    w.append(("lte-br", connect(lte, "ReturnValue", br_near, "Condition")))
    w.append(("near-ft", connect(br_near, "then", force, "execute")))
    w.append(("elem-obj", connect(loop, "Array Element", force, "Object")))
    w.append(("ft-setT", connect(force, "then", set_found_true, "execute")))
    setv(set_found_true, "bHuntFound", "true")
    w.append(("setT-print", connect(set_found_true, "then", print_hunt, "execute")))

    # Completed clear path
    w.append(("done-br", connect(loop, "Completed", br_clear, "execute")))
    w.append(("f2-not", connect(get_found2, "bHuntFound", not_found2, "A")))
    w.append(("not2-cond", connect(not_found2, "ReturnValue", br_clear, "Condition")))
    w.append(("clear-bb", connect(br_clear, "then", clear, "execute")))
    # GetBlackboard Target = self AI
    # ClearValue KeyName = Key_TargetActor
    w.append(("bb-self", "skip"))  # GetBlackboard may need Target pin from self
    # Wire GetBlackboard
    selfn = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "Self-Reference":
            selfn = n
            break
    if selfn is None:
        # create via call that implies self — use AIController as Target through nothing
        pass
    # GetBlackboard Target pin
    w.append(("bb-clearself", connect(get_bb, "ReturnValue", clear, "self")))
    # Need execute GetBlackboard? It's pure usually
    w.append(("key-clear", connect(key, "Key_TargetActor", clear, "KeyName")))
    w.append(("br-getbb", connect(br_clear, "then", clear, "execute")))  # may duplicate
    w.append(("clear-print", connect(clear, "then", print_search, "execute")))

    # Timer still AggroScanPlayer
    timer = find(ed, name="t0_K2_SetTimer_1")
    if timer:
        setv(timer, "FunctionName", "AggroScanPlayer")
        setv(timer, "Time", "0.6")
        setv(timer, "bLooping", "true")
        setv(timer, "InitialStartDelay", "0.25")

    # Disable OLD AggroScan ForceTarget paths that always hit GetPlayerPawn:
    # Break then on K2Node_CallFunction_8 (old getall) from being the only path — already broke aggro.then
    # Also break Object on K2Node_CallFunction_7 if still tied to GetPlayerPawn from old scan — leave orphaned

    unreal.BlueprintEditorLibrary.compile_blueprint(aic)
    log(("aic_status", str(aic.status)))
    try:
        for n in ed.list_nodes_with_errors() or []:
            log(("AIC_ERR", ops._node_title(n)))
    except Exception as e:
        log(("errlist", str(e)))
    try:
        unreal.EditorAssetLibrary.save_asset(AIC)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([aic.get_package()], True)
    log(("aggro_wires", w))


def fix_force_aggro_player():
    """Event_ForceAggroPlayer: only ForceTarget if GetPlayerPawn is BP_XRPawn and near."""
    pawn = load_bp(PAWN)
    ed, _ = ops._editor_for(pawn, "EventGraph")

    evt = find(ed, title="Event_ForceAggroPlayer", cls="K2Node_CustomEvent")
    if not evt:
        log("no Event_ForceAggroPlayer")
        return

    # Remove prior subgraph hanging off evt
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
        log(("removed_force", len(remove)))

    # Rebuild: GetPlayerPawn -> Cast XR -> IsValid mesh path -> GetController cast AIC -> ForceTarget
    gp = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerPawn")
    setv(gp, "PlayerIndex", "0")
    setpos(gp, 5400, 280)

    xr_cls = unreal.load_object(None, XR_C)
    if xr_cls is None:
        xr_cls = unreal.EditorAssetLibrary.load_blueprint_class(XR)
    cast_xr = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(5650, 200), [])
    if cast_xr:
        try:
            cast_xr.set_editor_property("target_type", xr_cls)
        except Exception as e:
            log(("cast_xr_tt", str(e)))
    setpos(cast_xr, 5650, 200)

    dist = ed.add_call_function_node("/Script/Engine.Actor.GetDistanceTo")
    setpos(dist, 5950, 360)
    lte = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble")
    setv(lte, "B", str(AGGRO_RANGE))
    setpos(lte, 6200, 360)
    br = ed.add_branch_node()
    setpos(br, 6400, 200)

    gc = ed.add_call_function_node("/Script/Engine.Pawn.GetController")
    setpos(gc, 6400, 400)

    aic_cls = unreal.load_object(None, AIC_C) or unreal.EditorAssetLibrary.load_blueprint_class(AIC)
    cast_ai = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(6650, 200), [])
    if cast_ai:
        try:
            cast_ai.set_editor_property("target_type", aic_cls)
        except Exception as e:
            log(("cast_ai_tt", str(e)))
    setpos(cast_ai, 6650, 200)

    ft = ed.add_call_function_node(f"{AIC_C}.Event_ForceTarget")
    setpos(ft, 7000, 200)

    w = []
    as_xr = as_ai = None
    if cast_xr:
        for p in bel().list_all_pins(cast_xr) or []:
            if ops._pin_name(p).startswith("As"):
                as_xr = ops._pin_name(p)
        w.append(("evt-xr", connect(evt, "then", cast_xr, "execute")))
        w.append(("gp-xr", connect(gp, "ReturnValue", cast_xr, "Object")))
        w.append(("xr-br", connect(cast_xr, "then", br, "execute")))
        # dist self=zombie (implicit self on GetDistanceTo), Other=XR
        if as_xr:
            w.append(("xr-other", connect(cast_xr, as_xr, dist, "OtherActor")))
        w.append(("dist-lte", connect(dist, "ReturnValue", lte, "A")))
        setv(lte, "B", str(AGGRO_RANGE))
        w.append(("lte-cond", connect(lte, "ReturnValue", br, "Condition")))
        if cast_ai:
            w.append(("br-ai", connect(br, "then", cast_ai, "execute")))
            w.append(("gc-aiobj", connect(gc, "ReturnValue", cast_ai, "Object")))
            for p in bel().list_all_pins(cast_ai) or []:
                if ops._pin_name(p).startswith("As"):
                    as_ai = ops._pin_name(p)
            w.append(("ai-ft", connect(cast_ai, "then", ft, "execute")))
            if as_ai:
                w.append(("as-ft", connect(cast_ai, as_ai, ft, "self")))
            if as_xr:
                w.append(("xr-obj", connect(cast_xr, as_xr, ft, "Object")))

    unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
    log(("pawn_status", str(pawn.status)))
    try:
        for n in ed.list_nodes_with_errors() or []:
            log(("PAWN_ERR", ops._node_title(n)))
    except Exception as e:
        log(("pawn_err", str(e)))
    try:
        unreal.EditorAssetLibrary.save_asset(PAWN)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([pawn.get_package()], True)
    log(("force_wires", w))


def refresh_stage2_actors():
    end_pie()
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(LEVEL)
    except Exception:
        pass

    for a in list(unreal.EditorLevelLibrary.get_all_level_actors() or []):
        if a.get_actor_label().startswith("Stage2_AutoZombie"):
            unreal.EditorLevelLibrary.destroy_actor(a)

    zcls = unreal.load_object(None, PAWN_C) or unreal.EditorAssetLibrary.load_blueprint_class(PAWN)
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
        # Nudge randomizer child if present
        for c in z.get_components_by_class(unreal.ChildActorComponent) or []:
            if "Randomizer" in c.get_name() or "Character" in c.get_name():
                child = c.get_child_actor()
                if child:
                    try:
                        child.set_editor_property("Random_BodyType", True)
                    except Exception:
                        pass
        log(("placed", z.get_actor_label(), round(z.get_actor_rotation().yaw, 1)))

    unreal.EditorLevelLibrary.save_current_level()
    try:
        unreal.EditorAssetLibrary.save_asset(LEVEL)
    except Exception:
        pass
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


def main():
    end_pie()
    fix_randomizer()
    rebuild_aggro_scan()
    fix_force_aggro_player()
    refresh_stage2_actors()
    return {"log": LOG}


RESULT = main()
