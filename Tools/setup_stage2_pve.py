"""Stage 2 PVE: 2 zombies on enter, click/touch for +2 more. Uses BP_ZombieSpawner."""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

SPAWNER = "/Game/Zombie/Blueprints/BP_ZombieSpawner"
PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
LEVEL = "/Game/XRFramework/Levels/L_XRTemplate"
CENTER = unreal.Vector(9000.0, 1700.0, 20.0)
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[Stage2PVE] {m}")


def pin(node, name, want_out=None):
    bel, pinlib = ops._bel(), ops._pinlib()
    for p in bel.list_all_pins(node) or []:
        if ops._pin_name(p) != name:
            continue
        d = str(pinlib.get_pin_direction(p)).upper()
        if want_out is True and "OUTPUT" not in d:
            continue
        if want_out is False and "INPUT" not in d:
            continue
        return p
    return None


def connect(a, ap, b, bp):
    pa, pb = pin(a, ap), pin(b, bp)
    if not pa or not pb:
        return f"fail {getattr(a,'get_name',lambda: '?')()}.{ap}->{getattr(b,'get_name',lambda: '?')()}.{bp}"
    ok = bool(ops._pinlib().try_create_connection(pa, pb))
    return f"{'ok' if ok else 'no'} {a.get_name()}.{ap}->{b.get_name()}.{bp}"


def set_default(node, pname, value):
    p = pin(node, pname, want_out=False)
    if not p:
        return False
    pinlib = ops._pinlib()
    for fn in ("set_pin_default_value", "set_pin_value"):
        if hasattr(pinlib, fn):
            try:
                getattr(pinlib, fn)(p, str(value))
                return True
            except Exception:
                pass
    try:
        p.default_value = str(value)
        return True
    except Exception:
        return False


def find(ed, title=None, name=None):
    for n in ed.list_all_nodes() or []:
        if name and n.get_name() == name:
            return n
        if title and ops._node_title(n) == title:
            return n
    return None


def configure_spawner():
    bp = ops._load_bp(SPAWNER)
    cdo = unreal.get_default_object(bp.generated_class())
    for k, v in (("NumberOfZombies", 2), ("SpawnRadius", 450.0), ("Health", 8.0), ("Attack Damage", 1.0)):
        try:
            cdo.set_editor_property(k, v)
            log(f"CDO {k}={v}")
        except Exception as e:
            log(f"CDO {k} fail {e}")

    ed, _ = ops._editor_for(bp, "EventGraph")
    mul = find(ed, name="K2Node_PromotableOperator_0")
    mn = find(ed, name="K2Node_CommutativeAssociativeBinaryOperator_1")
    if mul:
        set_default(mul, "B", "2")
    if mn:
        set_default(mn, "B", "2")
    started_set = find(ed, name="t4_VariableSet_1")
    if started_set:
        set_default(started_set, "bHasStarted", "true")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(SPAWNER)


def ensure_components():
    bp = ops._load_bp(PVE)
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = list(subsys.k2_gather_subobject_data_for_blueprint(bp) or [])
    root_h = handles[0] if handles else None
    by_name = {}
    for h in handles:
        data = lib.get_data(h)
        by_name[str(lib.get_variable_name(data))] = (h, lib.get_object(data))
        n = str(lib.get_variable_name(data))
        if "DefaultSceneRoot" in n:
            root_h = h

    def add_box(name, extent, rel):
        if name in by_name and isinstance(by_name[name][1], unreal.BoxComponent):
            obj = by_name[name][1]
        else:
            params = unreal.AddNewSubobjectParams()
            params.set_editor_property("new_class", unreal.BoxComponent)
            params.set_editor_property("parent_handle", root_h)
            params.set_editor_property("blueprint_context", bp)
            h, _ = subsys.add_new_subobject(params)
            try:
                subsys.rename_subobject(h, unreal.Name(name))
            except Exception:
                pass
            obj = lib.get_object(lib.get_data(h))
            by_name[name] = (h, obj)
        obj.set_box_extent(unreal.Vector(*extent), True)
        obj.set_relative_location(unreal.Vector(*rel), False, True)
        obj.set_editor_property("generate_overlap_events", True)
        try:
            obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
            obj.set_collision_profile_name("OverlapAllDynamic")
        except Exception:
            pass
        return obj

    add_box("StartTrigger", (550.0, 750.0, 220.0), (0.0, 0.0, 200.0))
    add_box("SpawnMoreTrigger", (70.0, 70.0, 70.0), (0.0, -380.0, 110.0))

    if "ClickMesh" not in by_name or not isinstance(by_name.get("ClickMesh", (None, None))[1], unreal.StaticMeshComponent):
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("new_class", unreal.StaticMeshComponent)
        params.set_editor_property("parent_handle", root_h)
        params.set_editor_property("blueprint_context", bp)
        h, _ = subsys.add_new_subobject(params)
        try:
            subsys.rename_subobject(h, unreal.Name("ClickMesh"))
        except Exception:
            pass
        mesh = lib.get_object(lib.get_data(h))
    else:
        mesh = by_name["ClickMesh"][1]
    cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
    if cube and mesh:
        mesh.set_editor_property("static_mesh", cube)
        mesh.set_relative_location(unreal.Vector(0.0, -380.0, 110.0), False, True)
        mesh.set_relative_scale3d(unreal.Vector(0.55, 0.55, 0.55))
        try:
            mesh.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
            mesh.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_VISIBILITY, unreal.CollisionResponse.ECR_BLOCK
            )
        except Exception:
            pass

    # vars
    for vn, vt in (("bStarted", "bool"), ("BatchSize", "int")):
        try:
            ops.add_blueprint_variable(asset_path=PVE, var_name=vn, var_type=vt, compile=False, save=False)
        except Exception as e:
            log(f"var {vn}: {e}")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("BatchSize", 2)
        cdo.set_editor_property("bStarted", False)
    except Exception as e:
        log(f"pve cdo: {e}")
    unreal.EditorAssetLibrary.save_asset(PVE)
    log("components ok")


def clear_graph_helpers():
    bp = ops._load_bp(PVE)
    ed, _ = ops._editor_for(bp, "EventGraph")
    keep = {"Event BeginPlay", "Event ActorBeginOverlap", "Event Tick", "Event ActorOnClicked"}
    remove = []
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t in keep:
            continue
        # keep nothing else — rebuild
        remove.append(n)
    if remove:
        try:
            ed.remove_nodes(remove)
            log(f"removed {len(remove)} nodes")
        except Exception as e:
            log(f"remove fail {e}")
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)


def wire_graph():
    clear_graph_helpers()
    bp = ops._load_bp(PVE)
    ed, _ = ops._editor_for(bp, "EventGraph")

    # Ensure OnClicked event
    if not find(ed, title="Event ActorOnClicked"):
        try:
            ops.add_blueprint_nodes(
                asset_path=PVE,
                nodes=[{"id": "clk", "type": "palette", "palette": "Add Event|Mouse|ActorOnClicked", "x": 0, "y": 700}],
                compile=False,
                save=False,
            )
        except Exception as e:
            log(f"onclick add: {e}")
            try:
                ops.add_blueprint_nodes(
                    asset_path=PVE,
                    nodes=[{"id": "clk", "type": "palette", "palette": "Event|ActorOnClicked", "x": 0, "y": 700}],
                    compile=False,
                    save=False,
                )
            except Exception as e2:
                log(f"onclick add2: {e2}")

    # Custom event SpawnMore
    try:
        ops.add_blueprint_nodes(
            asset_path=PVE,
            nodes=[{"id": "more", "type": "custom_event", "event_name": "SpawnMore", "x": 0, "y": 500}],
            compile=False,
            save=False,
        )
    except Exception as e:
        log(f"SpawnMore evt: {e}")

    # Component overlaps
    for comp in ("StartTrigger", "SpawnMoreTrigger"):
        try:
            n = ed.add_component_bound_event_node(comp, "OnComponentBeginOverlap")
            log(f"bound {comp}: {n.get_name() if n else None}")
        except Exception as e:
            log(f"bound {comp} fail: {e}")

    SPAWNER_C = "/Game/Zombie/Blueprints/BP_ZombieSpawner.BP_ZombieSpawner_C"

    # Nodes for START path
    created = ops.add_blueprint_nodes(
        asset_path=PVE,
        graph_name="EventGraph",
        nodes=[
            {"id": "cast_pawn", "type": "palette", "palette": "Utilities|Casting|Cast To Pawn", "x": 280, "y": 200},
            {"id": "get_started", "type": "palette", "palette": "Variables|Get bStarted", "x": 280, "y": 360},
            {"id": "not_started", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Not_PreBool", "x": 480, "y": 360},
            {"id": "and_bool", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.BooleanAND", "x": 680, "y": 280},
            {"id": "branch_start", "type": "branch", "x": 900, "y": 200},
            {"id": "set_started", "type": "palette", "palette": "Variables|Set bStarted", "x": 1150, "y": 200},
            {"id": "get_spawner", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetActorOfClass", "x": 1400, "y": 200},
            {"id": "is_valid", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsValid", "x": 1650, "y": 200},
            {"id": "branch_valid", "type": "branch", "x": 1900, "y": 200},
            {"id": "print_start", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 2400, "y": 200,
             "pin_defaults": {"InString": "Stage2 PVE: 2 zombies!", "bPrintToScreen": "true", "Duration": "3.0"}},
            # Spawn more path
            {"id": "get_spawner2", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetActorOfClass", "x": 400, "y": 520},
            {"id": "is_valid2", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsValid", "x": 650, "y": 520},
            {"id": "branch_valid2", "type": "branch", "x": 900, "y": 520},
            {"id": "print_more", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 1500, "y": 520,
             "pin_defaults": {"InString": "Stage2 PVE: +2 zombies", "bPrintToScreen": "true", "Duration": "2.0"}},
        ],
        compile=False,
        save=False,
    )
    log(f"created nodes: {created.get('created')}")

    # Try add StartHorde / Spawn calls via function path on generated class
    for fid, fpath, x, y in (
        ("start_horde", f"{SPAWNER_C}.StartHorde", 2150, 200),
        ("spawn_more", f"{SPAWNER_C}.Spawn", 1200, 520),
    ):
        r = ops.add_blueprint_nodes(
            asset_path=PVE,
            nodes=[{"id": fid, "type": "call", "function_path": fpath, "x": x, "y": y}],
            compile=False,
            save=False,
        )
        log(f"call {fid}: {r.get('created')}")

    # Cast via DynamicCast if palette failed
    ed, _ = ops._editor_for(bp, "EventGraph")
    cast_n = None
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if "Cast" in t and "Pawn" in t:
            cast_n = n
            break
    if cast_n is None:
        try:
            cast_n = ed.create_node_from_name("K2Node_DynamicCast")
            cast_n.set_editor_property("target_type", unreal.Pawn.static_class())
            log("created DynamicCast Pawn")
        except Exception as e:
            log(f"DynamicCast fail: {e}")

    # Resolve nodes by title / recent names
    def N(title):
        return find(ed, title=title)

    overlap = N("Event ActorBeginOverlap")
    clicked = N("Event ActorOnClicked")
    more = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "SpawnMore" or (n.get_class().get_name() == "K2Node_CustomEvent" and "SpawnMore" in ops._node_title(n)):
            more = n
    start_trig = None
    more_trig = None
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if "StartTrigger" in t and "Overlap" in t:
            start_trig = n
        if "SpawnMoreTrigger" in t and "Overlap" in t:
            more_trig = n

    get_spawner = None
    get_spawner2 = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "GetActorOfClass":
            if get_spawner is None:
                get_spawner = n
            else:
                get_spawner2 = n
    branch_start = None
    branch_valid = None
    branch_valid2 = None
    branches = [n for n in ed.list_all_nodes() or [] if ops._node_title(n) == "Branch"]
    if len(branches) >= 1:
        branch_start = branches[0]
    if len(branches) >= 2:
        branch_valid = branches[1]
    if len(branches) >= 3:
        branch_valid2 = branches[2]

    get_started = N("Get bStarted")
    set_started = N("Set bStarted")
    not_started = N("NOT Boolean") or N("Not_PreBool")
    for n in ed.list_all_nodes() or []:
        if "Not" in ops._node_title(n) and "Bool" in ops._node_title(n):
            not_started = n
    and_bool = None
    for n in ed.list_all_nodes() or []:
        if "AND" in ops._node_title(n).upper() and "Boolean" in ops._node_title(n):
            and_bool = n
    is_valid = None
    is_valid2 = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "IsValid":
            if is_valid is None:
                is_valid = n
            else:
                is_valid2 = n
    print_start = None
    print_more = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "PrintString":
            if print_start is None:
                print_start = n
            else:
                print_more = n
    start_horde = None
    spawn_call = None
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t == "StartHorde":
            start_horde = n
        if t == "Spawn" and n.get_class().get_name() == "K2Node_CallFunction":
            spawn_call = n

    wires = []
    # Set ActorClass defaults
    for node in (get_spawner, get_spawner2):
        if node:
            set_default(node, "ActorClass", SPAWNER_C)
            wires.append(f"ActorClass on {node.get_name()}")

    if set_started:
        set_default(set_started, "bStarted", "true")

    # START: ActorBeginOverlap OR StartTrigger overlap
    start_src = start_trig or overlap
    if start_src and cast_n:
        wires.append(connect(start_src, "then", cast_n, "execute"))
        # Other actor pin names vary
        for op in ("OtherActor", "Other Actor", "Other"):
            if pin(start_src, op) and pin(cast_n, "Object"):
                wires.append(connect(start_src, op, cast_n, "Object"))
                break
        # success exec
        for tp in ("then", "CastSucceeded", "execute"):
            if pin(cast_n, tp) and branch_start:
                wires.append(connect(cast_n, tp, branch_start, "execute"))
                break
        # cast bool: use IsValid cast output AsPawn -> treat success via then only
    # Condition: NOT bStarted (cast success already gated by then pin)
    if get_started and not_started and branch_start:
        wires.append(connect(get_started, "bStarted", not_started, "A"))
        wires.append(connect(not_started, "ReturnValue", branch_start, "Condition"))
    if branch_start and set_started:
        wires.append(connect(branch_start, "then", set_started, "execute"))
    if set_started and get_spawner:
        wires.append(connect(set_started, "then", get_spawner, "execute"))
    if get_spawner and is_valid:
        wires.append(connect(get_spawner, "then", is_valid, "execute") if pin(is_valid, "execute") else connect(get_spawner, "then", is_valid, "exec"))
        wires.append(connect(get_spawner, "ReturnValue", is_valid, "InputObject") if pin(is_valid, "InputObject") else connect(get_spawner, "ReturnValue", is_valid, "Object"))
    # IsValid macro has Is Valid exec out
    if is_valid and branch_valid:
        for tp in ("Is Valid", "then"):
            if pin(is_valid, tp):
                wires.append(connect(is_valid, tp, branch_valid, "execute"))
                break
        # force condition true if needed
        set_default(branch_valid, "Condition", "true")
    if branch_valid and start_horde:
        wires.append(connect(branch_valid, "then", start_horde, "execute"))
        wires.append(connect(get_spawner, "ReturnValue", start_horde, "self"))
    if start_horde and print_start:
        wires.append(connect(start_horde, "then", print_start, "execute"))
    elif branch_valid and print_start and not start_horde:
        wires.append(connect(branch_valid, "then", print_start, "execute"))

    # MORE: SpawnMore custom event, OnClicked, SpawnMoreTrigger
    more_srcs = [x for x in (more, clicked, more_trig) if x]
    if more_srcs and get_spawner2:
        wires.append(connect(more_srcs[0], "then", get_spawner2, "execute"))
        # Fan-in: also connect other sources if possible (may need separate gets; for test, wire all to get_spawner2 execute)
        for src in more_srcs[1:]:
            wires.append(connect(src, "then", get_spawner2, "execute"))
    if get_spawner2 and is_valid2:
        wires.append(connect(get_spawner2, "then", is_valid2, "execute") if pin(is_valid2, "execute") else connect(get_spawner2, "then", is_valid2, "exec"))
        wires.append(connect(get_spawner2, "ReturnValue", is_valid2, "InputObject") if pin(is_valid2, "InputObject") else connect(get_spawner2, "ReturnValue", is_valid2, "Object"))
    if is_valid2 and branch_valid2:
        for tp in ("Is Valid", "then"):
            if pin(is_valid2, tp):
                wires.append(connect(is_valid2, tp, branch_valid2, "execute"))
                break
        set_default(branch_valid2, "Condition", "true")
    if branch_valid2 and spawn_call:
        wires.append(connect(branch_valid2, "then", spawn_call, "execute"))
        wires.append(connect(get_spawner2, "ReturnValue", spawn_call, "self"))
    if spawn_call and print_more:
        wires.append(connect(spawn_call, "then", print_more, "execute"))
    elif branch_valid2 and print_more:
        wires.append(connect(branch_valid2, "then", print_more, "execute"))

    # If StartHorde call node missing, try palette call on target
    if start_horde is None:
        log("WARNING: StartHorde node missing — will rely on Spawn for first wave too")
        if branch_valid and spawn_call:
            wires.append(connect(branch_valid, "then", spawn_call, "execute"))
            wires.append(connect(get_spawner, "ReturnValue", spawn_call, "self"))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log(f"compile status={bp.status}")
    # list errors
    try:
        errs = list(ed.list_nodes_with_errors() or [])
        log(f"errors={len(errs)}")
        for n in errs[:8]:
            log(f"  err node {ops._node_title(n)}")
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(PVE)
    log({"wires": wires})
    return wires


def place_level():
    els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        els.load_level(LEVEL)
    except Exception as e:
        log(f"load: {e}")

    for a in list(unreal.EditorLevelLibrary.get_all_level_actors() or []):
        if a.get_actor_label().startswith(("Stage2_ZombieSpawner", "Stage2_PVE", "Stage2_ZombieSpawnPt")):
            unreal.EditorLevelLibrary.destroy_actor(a)

    spawner_cls = unreal.EditorAssetLibrary.load_blueprint_class(SPAWNER)
    pve_cls = unreal.EditorAssetLibrary.load_blueprint_class(PVE)

    spawner = unreal.EditorLevelLibrary.spawn_actor_from_class(spawner_cls, CENTER + unreal.Vector(0, 0, 40))
    spawner.set_actor_label("Stage2_ZombieSpawner")
    spawner.set_folder_path("Stages/Stage2/PVE")
    for k, v in (("NumberOfZombies", 2), ("SpawnRadius", 450.0), ("Health", 8.0), ("Attack Damage", 1.0), ("bHasStarted", False)):
        try:
            spawner.set_editor_property(k, v)
        except Exception as e:
            log(f"inst {k}: {e}")

    pts = []
    for i, off in enumerate(
        (
            unreal.Vector(420, 220, 5),
            unreal.Vector(-320, 360, 5),
            unreal.Vector(260, -300, 5),
            unreal.Vector(-420, -180, 5),
        )
    ):
        tp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.TargetPoint, CENTER + off)
        tp.set_actor_label(f"Stage2_ZombieSpawnPt_{i+1}")
        tp.set_folder_path("Stages/Stage2/PVE")
        pts.append(tp)
    try:
        spawner.set_editor_property("SpawnPointActors", pts)
    except Exception as e:
        log(f"pts: {e}")

    pve = unreal.EditorLevelLibrary.spawn_actor_from_class(pve_cls, CENTER)
    pve.set_actor_label("Stage2_PVE")
    pve.set_folder_path("Stages/Stage2/PVE")

    try:
        text = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.TextRenderActor, CENTER + unreal.Vector(0, -380, 190)
        )
        text.set_actor_label("Stage2_PVE_ClickLabel")
        text.set_folder_path("Stages/Stage2/PVE")
        tr = text.get_component_by_class(unreal.TextRenderComponent)
        if tr:
            tr.set_editor_property("text", "+2 ZOMBIES (click / touch cube)")
            tr.set_editor_property("world_size", 42.0)
            tr.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    except Exception as e:
        log(f"label: {e}")

    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
    return True


def main():
    configure_spawner()
    ensure_components()
    wires = wire_graph()
    place_level()
    return {"log": LOG, "wires": wires}


RESULT = main()
