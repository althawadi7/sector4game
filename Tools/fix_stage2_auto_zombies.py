"""Stage2 PVE: auto-spawn 2 zombies when player is near Stage2 (teleport-safe).
Removes click cube / spawn-more box. Replaces fragile overlap-only start.
"""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
SPAWNER = "/Game/Zombie/Blueprints/BP_ZombieSpawner"
SPAWNER_C = "/Game/Zombie/Blueprints/BP_ZombieSpawner.BP_ZombieSpawner_C"
ZOMBIE = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
LEVEL = "/Game/XRFramework/Levels/L_XRTemplate"
CENTER = unreal.Vector(9000.0, 1700.0, 20.0)
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[Stage2Auto] {m}")


def pin(node, name):
    bel, pinlib = ops._bel(), ops._pinlib()
    for p in bel.list_all_pins(node) or []:
        if ops._pin_name(p) == name:
            return p
    return None


def connect(a, ap, b, bp):
    pinlib = ops._pinlib()
    pa, pb = pin(a, ap), pin(b, bp)
    if not pa or not pb:
        return f"fail {ap}->{bp}"
    return "ok" if pinlib.try_create_connection(pa, pb) else "no"


def setdef(node, pname, value):
    p = pin(node, pname)
    if not p:
        return False
    pinlib = ops._pinlib()
    try:
        pinlib.set_pin_default_value(p, str(value))
        return True
    except Exception:
        try:
            p.default_value = str(value)
            return True
        except Exception:
            return False


def strip_click_junk(bp):
    """Hide/disable click mesh + spawn-more trigger (keep StartTrigger optional)."""
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in list(subsys.k2_gather_subobject_data_for_blueprint(bp) or []):
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object(data)
        if not obj:
            continue
        if name in ("ClickMesh", "SpawnMoreTrigger"):
            try:
                obj.set_editor_property("visible", False)
            except Exception:
                pass
            try:
                obj.set_hidden_in_game(True)
            except Exception:
                pass
            try:
                obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            except Exception:
                pass
            try:
                obj.set_editor_property("generate_overlap_events", False)
            except Exception:
                pass
            log(f"disabled {name}")
        if name == "StartTrigger" and isinstance(obj, unreal.BoxComponent):
            # Large volume covering Stage2 play area
            obj.set_box_extent(unreal.Vector(600.0, 800.0, 250.0), True)
            obj.set_relative_location(unreal.Vector(0.0, 0.0, 200.0), False, True)
            obj.set_editor_property("generate_overlap_events", True)
            try:
                obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
                obj.set_collision_profile_name("OverlapAllDynamic")
            except Exception:
                pass


def clear_and_rebuild_graph():
    bp = ops._load_bp(PVE)
    strip_click_junk(bp)

    # Ensure vars
    for vn, vt in (("bStarted", "bool"), ("TriggerDist", "float")):
        try:
            ops.add_blueprint_variable(asset_path=PVE, var_name=vn, var_type=vt, compile=False, save=False)
        except Exception as e:
            log(f"var {vn}: {e}")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("bStarted", False)
        cdo.set_editor_property("TriggerDist", 900.0)
    except Exception as e:
        log(f"cdo: {e}")

    ed, _ = ops._editor_for(bp, "EventGraph")
    # Remove all non-core events
    keep_titles = {"Event BeginPlay", "Event Tick", "Event ActorBeginOverlap"}
    remove = []
    for n in list(ed.list_all_nodes() or []):
        t = ops._node_title(n)
        cls = n.get_class().get_name()
        if t in keep_titles and cls == "K2Node_Event":
            continue
        remove.append(n)
    if remove:
        try:
            ed.remove_nodes(remove)
            log(f"cleared {len(remove)} nodes")
        except Exception as e:
            log(f"clear fail: {e}")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    ed, _ = ops._editor_for(bp, "EventGraph")

    # Build: Tick -> GetPlayerPawn -> IsValid -> Branch
    #   -> VSizeXY(pawnLoc - selfLoc) <= TriggerDist
    #   -> NOT bStarted -> Set bStarted -> GetActorOfClass(Spawner) -> Spawn -> Print
    created = ops.add_blueprint_nodes(
        asset_path=PVE,
        graph_name="EventGraph",
        nodes=[
            {"id": "get_pawn", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetPlayerPawn", "x": 250, "y": 400,
             "pin_defaults": {"PlayerIndex": "0"}},
            {"id": "is_valid", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsValid", "x": 500, "y": 400},
            {"id": "branch_valid", "type": "branch", "x": 750, "y": 400},
            {"id": "pawn_loc", "type": "call", "function_path": "/Script/Engine.Actor.K2_GetActorLocation", "x": 750, "y": 560},
            {"id": "self_loc", "type": "call", "function_path": "/Script/Engine.Actor.K2_GetActorLocation", "x": 750, "y": 700},
            {"id": "sub", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Subtract_VectorVector", "x": 1000, "y": 600},
            {"id": "vsize", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.VSizeXY", "x": 1250, "y": 600},
            {"id": "get_dist", "type": "palette", "palette": "Variables|Get TriggerDist", "x": 1250, "y": 720},
            {"id": "lte", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble", "x": 1500, "y": 600},
            {"id": "get_started", "type": "palette", "palette": "Variables|Get bStarted", "x": 1500, "y": 760},
            {"id": "not_started", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Not_PreBool", "x": 1700, "y": 760},
            {"id": "andb", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.BooleanAND", "x": 1900, "y": 600},
            {"id": "branch_go", "type": "branch", "x": 2150, "y": 400},
            {"id": "set_started", "type": "palette", "palette": "Variables|Set bStarted", "x": 2400, "y": 400},
            {"id": "get_spawner", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetActorOfClass", "x": 2700, "y": 400},
            {"id": "call_spawn", "type": "call", "function_path": f"{SPAWNER_C}.Spawn", "x": 3000, "y": 400},
            {"id": "print", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 3300, "y": 400,
             "pin_defaults": {"InString": "Stage2: 2 zombies spawned", "bPrintToScreen": "true", "Duration": "4.0"}},
        ],
        compile=False,
        save=False,
    )
    log(f"nodes: {created.get('created')}")

    # Fallback get/set via editor API if palette failed
    ed, _ = ops._editor_for(bp, "EventGraph")
    get_started = None
    set_started = None
    get_dist = None
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t == "Get bStarted":
            get_started = n
        if t == "Set bStarted":
            set_started = n
        if t == "Get TriggerDist":
            get_dist = n
    if get_started is None:
        get_started = ed.add_get_member_variable_node("bStarted")
    if set_started is None:
        set_started = ed.add_set_member_variable_node("bStarted")
    if get_dist is None:
        get_dist = ed.add_get_member_variable_node("TriggerDist")
    setdef(set_started, "bStarted", "true")

    def find(title=None, name=None, pred=None):
        for n in ed.list_all_nodes() or []:
            if name and n.get_name() == name:
                return n
            if title and ops._node_title(n) == title:
                return n
            if pred and pred(n):
                return n
        return None

    tick = find(title="Event Tick")
    get_pawn = find(title="GetPlayerPawn")
    is_valid = find(title="IsValid")
    branches = [n for n in ed.list_all_nodes() or [] if ops._node_title(n) == "Branch"]
    branch_valid = branches[0] if len(branches) > 0 else None
    branch_go = branches[1] if len(branches) > 1 else None
    locs = [n for n in ed.list_all_nodes() or [] if ops._node_title(n) == "Get Actor Location"]
    pawn_loc = locs[0] if len(locs) > 0 else None
    self_loc = locs[1] if len(locs) > 1 else None
    sub = find(pred=lambda n: "vector - vector" in ops._node_title(n).lower() or "Subtract_VectorVector" in n.get_name())
    if sub is None:
        for n in ed.list_all_nodes() or []:
            if "Subtract" in ops._node_title(n) or ops._node_title(n) == "vector - vector":
                sub = n
    vsize = None
    for n in ed.list_all_nodes() or []:
        if "VSizeXY" in ops._node_title(n) or "Vector Length XY" in ops._node_title(n):
            vsize = n
    lte = None
    for n in ed.list_all_nodes() or []:
        if "<=" in ops._node_title(n) or "LessEqual" in ops._node_title(n).lower() or "float <= float" in ops._node_title(n):
            lte = n
    notb = None
    for n in ed.list_all_nodes() or []:
        if "NOT Boolean" in ops._node_title(n):
            notb = n
    andb = None
    for n in ed.list_all_nodes() or []:
        if "AND Boolean" in ops._node_title(n):
            andb = n
    get_spawner = find(title="GetActorOfClass")
    call_spawn = find(title="Spawn")
    printn = find(title="PrintString")

    # Re-find get/set after add
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t == "Get bStarted":
            get_started = n
        if t == "Set bStarted":
            set_started = n
        if t == "Get TriggerDist":
            get_dist = n

    wires = []
    if tick and get_pawn:
        wires.append(("tick", connect(tick, "then", get_pawn, "execute")))
    if get_pawn and is_valid:
        # IsValid may be pure — use Branch with IsValid return
        # Actually KismetSystemLibrary.IsValid is PURE in UE5 - no exec!
        # So: Tick -> Branch(IsValid(pawn)) via connecting ReturnValue to Condition
        # Need exec: Tick -> Branch directly, condition = IsValid(GetPlayerPawn)
        pass

    # Rebuild exec more carefully for pure IsValid:
    # Tick -> Branch_valid (Condition=IsValid(pawn)) -> ...
    if tick and branch_valid:
        # disconnect get_pawn exec path; use pure chain
        wires.append(("tick-br", connect(tick, "then", branch_valid, "execute")))
    if get_pawn and is_valid:
        # GetPlayerPawn is pure too in some versions - check
        wires.append(("pawn-valid", connect(get_pawn, "ReturnValue", is_valid, "Object") if pin(is_valid, "Object") else connect(get_pawn, "ReturnValue", is_valid, "InputObject")))
        if branch_valid:
            wires.append(("valid-br", connect(is_valid, "ReturnValue", branch_valid, "Condition")))
    if branch_valid and branch_go:
        wires.append(("brv-brg", connect(branch_valid, "then", branch_go, "execute")))

    # Distance data (pure)
    if get_pawn and pawn_loc:
        wires.append(("pawn-loc", connect(get_pawn, "ReturnValue", pawn_loc, "self")))
    if pawn_loc and sub:
        wires.append(("loc-a", connect(pawn_loc, "ReturnValue", sub, "A")))
    if self_loc and sub:
        wires.append(("loc-b", connect(self_loc, "ReturnValue", sub, "B")))
    if sub and vsize:
        wires.append(("sub-vs", connect(sub, "ReturnValue", vsize, "A")))
    if vsize and lte:
        wires.append(("vs-lte", connect(vsize, "ReturnValue", lte, "A")))
    if get_dist and lte:
        wires.append(("dist-lte", connect(get_dist, "TriggerDist", lte, "B")))
    if lte and andb:
        wires.append(("lte-and", connect(lte, "ReturnValue", andb, "A")))
    if get_started and notb:
        wires.append(("st-not", connect(get_started, "bStarted", notb, "A")))
    if notb and andb:
        wires.append(("not-and", connect(notb, "ReturnValue", andb, "B")))
    if andb and branch_go:
        wires.append(("and-brg", connect(andb, "ReturnValue", branch_go, "Condition")))

    if branch_go and set_started:
        wires.append(("go-set", connect(branch_go, "then", set_started, "execute")))
        setdef(set_started, "bStarted", "true")
    if set_started and get_spawner:
        wires.append(("set-gs", connect(set_started, "then", get_spawner, "execute")))
        setdef(get_spawner, "ActorClass", SPAWNER_C)
    if get_spawner and call_spawn:
        wires.append(("gs-sp", connect(get_spawner, "then", call_spawn, "execute")))
        wires.append(("gs-self", connect(get_spawner, "ReturnValue", call_spawn, "self")))
    if call_spawn and printn:
        wires.append(("sp-pr", connect(call_spawn, "then", printn, "execute")))

    # ALSO: direct spawn of 2 zombies if spawner Spawn fails — add fallback SpawnActor nodes
    # Place zombie actors in level as guaranteed visible enemies
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log(f"compile={bp.status}")
    try:
        errs = list(ed.list_nodes_with_errors() or [])
        log(f"errs={len(errs)}")
        for n in errs[:10]:
            log(f"  {ops._node_title(n)}")
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(PVE)
    log({"wires": wires})
    return wires


def place_two_zombies_and_cleanup_level():
    els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        els.load_level(LEVEL)
    except Exception as e:
        log(f"load: {e}")

    # Remove click label
    for a in list(unreal.EditorLevelLibrary.get_all_level_actors() or []):
        lab = a.get_actor_label()
        if lab in ("Stage2_PVE_ClickLabel",) or lab.startswith("Stage2_AutoZombie"):
            unreal.EditorLevelLibrary.destroy_actor(a)

    # Configure spawner instance
    spawner = None
    for a in unreal.EditorLevelLibrary.get_all_level_actors() or []:
        if a.get_actor_label() == "Stage2_ZombieSpawner":
            spawner = a
            break
    if spawner is None:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(SPAWNER)
        spawner = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, CENTER + unreal.Vector(0, 0, 40))
        spawner.set_actor_label("Stage2_ZombieSpawner")
        spawner.set_folder_path("Stages/Stage2/PVE")
    for k, v in (("NumberOfZombies", 2), ("SpawnRadius", 500.0), ("Health", 8.0), ("Attack Damage", 1.0)):
        try:
            spawner.set_editor_property(k, v)
        except Exception as e:
            log(f"spawner {k}: {e}")

    # Ensure PVE actor exists at center
    pve = None
    for a in unreal.EditorLevelLibrary.get_all_level_actors() or []:
        if a.get_actor_label() == "Stage2_PVE":
            pve = a
            break
    if pve is None:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(PVE)
        pve = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, CENTER)
        pve.set_actor_label("Stage2_PVE")
        pve.set_folder_path("Stages/Stage2/PVE")
    else:
        pve.set_actor_location(CENTER, False, True)
    try:
        pve.set_editor_property("bStarted", False)
        pve.set_editor_property("TriggerDist", 900.0)
    except Exception as e:
        log(f"pve props: {e}")

    # GUARANTEE: place 2 zombie pawns already in Stage2 (visible when you arrive)
    zcls = unreal.EditorAssetLibrary.load_blueprint_class(ZOMBIE)
    spots = [
        CENTER + unreal.Vector(420, 220, 95),
        CENTER + unreal.Vector(-320, 360, 95),
    ]
    placed = []
    for i, loc in enumerate(spots):
        z = unreal.EditorLevelLibrary.spawn_actor_from_class(zcls, loc)
        z.set_actor_label(f"Stage2_AutoZombie_{i+1}")
        z.set_folder_path("Stages/Stage2/PVE")
        try:
            z.set_editor_property("Health", 8.0)
            z.set_editor_property("MaxHealth", 8.0)
        except Exception as e:
            log(f"zombie health: {e}")
        # Face toward landing
        try:
            z.set_actor_rotation(unreal.Rotator(0, 180, 0), False)
        except Exception:
            pass
        placed.append(z.get_actor_label())
        log(f"placed {z.get_actor_label()} at {loc}")

    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorAssetLibrary.save_asset(PVE)
    unreal.EditorAssetLibrary.save_asset(SPAWNER)
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception:
        pass
    return placed


def main():
    clear_and_rebuild_graph()
    placed = place_two_zombies_and_cleanup_level()
    return {"log": LOG, "placed": placed}


RESULT = main()
