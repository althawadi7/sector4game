"""Reliable Stage2 auto zombies: proximity Tick spawns 2 BP_Zombie_Pawn via SpawnActorFromClass.
No click box. Teleport-safe (Tick distance, not BeginOverlap).
"""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
ZOMBIE = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
ZOMBIE_C = "/Game/Zombie/Blueprints/BP_Zombie_Pawn.BP_Zombie_Pawn_C"
LEVEL = "/Game/XRFramework/Levels/L_XRTemplate"
CENTER = unreal.Vector(9000.0, 1700.0, 20.0)
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[S2Z] {m}")


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
        return f"fail:{ap}->{bp}"
    return "ok" if pinlib.try_create_connection(pa, pb) else f"no:{ap}->{bp}"


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


def disable_click_comps(bp):
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in subsys.k2_gather_subobject_data_for_blueprint(bp) or []:
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object(data)
        if not obj:
            continue
        if name in ("ClickMesh", "SpawnMoreTrigger"):
            try:
                obj.set_visibility(False)
                obj.set_hidden_in_game(True)
                obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                obj.set_editor_property("generate_overlap_events", False)
            except Exception:
                pass


def rebuild():
    # End PIE if needed
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        les.editor_request_end_play()

    bp = ops._load_bp(PVE)
    disable_click_comps(bp)

    for vn, vt in (("bStarted", "bool"), ("TriggerDist", "float")):
        try:
            ops.add_blueprint_variable(asset_path=PVE, var_name=vn, var_type=vt, compile=False, save=False)
        except Exception as e:
            log(f"var {vn}: {e}")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("bStarted", False)
        cdo.set_editor_property("TriggerDist", 1200.0)
    except Exception as e:
        log(f"cdo {e}")

    ed, _ = ops._editor_for(bp, "EventGraph")
    remove = []
    for n in list(ed.list_all_nodes() or []):
        t = ops._node_title(n)
        if n.get_class().get_name() == "K2Node_Event" and t in (
            "Event BeginPlay",
            "Event Tick",
            "Event ActorBeginOverlap",
        ):
            continue
        remove.append(n)
    if remove:
        ed.remove_nodes(remove)
        log(f"cleared {len(remove)}")

    # Tick -> Branch(!bStarted) -> GetPlayerPawn -> IsValid -> Branch
    # -> dist check -> Set bStarted -> SpawnActor x2 -> Print
    created = ops.add_blueprint_nodes(
        asset_path=PVE,
        graph_name="EventGraph",
        nodes=[
            {"id": "get_started", "type": "palette", "palette": "Variables|Get bStarted", "x": 200, "y": 500},
            {"id": "notb", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Not_PreBool", "x": 400, "y": 500},
            {"id": "br0", "type": "branch", "x": 600, "y": 400},
            {"id": "get_pawn", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetPlayerPawn", "x": 850, "y": 400,
             "pin_defaults": {"PlayerIndex": "0"}},
            {"id": "isv", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsValid", "x": 1100, "y": 400},
            {"id": "br1", "type": "branch", "x": 1350, "y": 400},
            {"id": "pawn_loc", "type": "call", "function_path": "/Script/Engine.Actor.K2_GetActorLocation", "x": 1350, "y": 560},
            {"id": "self_loc", "type": "call", "function_path": "/Script/Engine.Actor.K2_GetActorLocation", "x": 1350, "y": 700},
            {"id": "sub", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Subtract_VectorVector", "x": 1600, "y": 600},
            {"id": "vsize", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.VSizeXY", "x": 1850, "y": 600},
            {"id": "lte", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble", "x": 2100, "y": 600},
            {"id": "br2", "type": "branch", "x": 2350, "y": 400},
            {"id": "set_started", "type": "palette", "palette": "Variables|Set bStarted", "x": 2600, "y": 400},
            {"id": "spawn1", "type": "call", "function_path": "/Script/Engine.GameplayStatics.BeginSpawningActorFromClass", "x": 2900, "y": 300},
            {"id": "spawn2", "type": "call", "function_path": "/Script/Engine.GameplayStatics.BeginSpawningActorFromClass", "x": 2900, "y": 550},
            {"id": "fin1", "type": "call", "function_path": "/Script/Engine.GameplayStatics.FinishSpawningActor", "x": 3300, "y": 300},
            {"id": "fin2", "type": "call", "function_path": "/Script/Engine.GameplayStatics.FinishSpawningActor", "x": 3300, "y": 550},
            {"id": "mk1", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.MakeTransform", "x": 2600, "y": 650},
            {"id": "mk2", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.MakeTransform", "x": 2600, "y": 850},
            {"id": "print", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 3700, "y": 400,
             "pin_defaults": {"InString": "Stage2 PVE: 2 zombies AUTO", "bPrintToScreen": "true", "Duration": "5.0"}},
        ],
        compile=False,
        save=False,
    )
    log(str(created.get("created"))[:500])

    # If BeginSpawningActorFromClass failed name, try SpawnActorFromClass
    ed, _ = ops._editor_for(bp, "EventGraph")
    has_spawn = any(ops._node_title(n).startswith("BeginSpawn") or ops._node_title(n) == "SpawnActor from Class" or "SpawnActor" in ops._node_title(n) for n in ed.list_all_nodes() or [])
    if not has_spawn:
        r = ops.add_blueprint_nodes(
            asset_path=PVE,
            nodes=[
                {"id": "sa1", "type": "call", "function_path": "/Script/Engine.GameplayStatics.SpawnActorFromClass", "x": 2900, "y": 300},
                {"id": "sa2", "type": "call", "function_path": "/Script/Engine.GameplayStatics.SpawnActorFromClass", "x": 2900, "y": 550},
                {"id": "mk1b", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.MakeTransform", "x": 2600, "y": 650},
                {"id": "mk2b", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.MakeTransform", "x": 2600, "y": 850},
            ],
            compile=False,
            save=False,
        )
        log("fallback spawn " + str(r.get("created"))[:300])

    ed, _ = ops._editor_for(bp, "EventGraph")

    def find_all(title_substr=None, title_exact=None):
        out = []
        for n in ed.list_all_nodes() or []:
            t = ops._node_title(n)
            if title_exact and t == title_exact:
                out.append(n)
            elif title_substr and title_substr in t:
                out.append(n)
        return out

    # Ensure get/set bStarted
    gets = find_all(title_exact="Get bStarted")
    sets = find_all(title_exact="Set bStarted")
    get_started = gets[0] if gets else ed.add_get_member_variable_node("bStarted")
    set_started = sets[0] if sets else ed.add_set_member_variable_node("bStarted")
    setdef(set_started, "bStarted", "true")

    tick = find_all(title_exact="Event Tick")[0]
    notb = find_all(title_exact="NOT Boolean")[0]
    branches = find_all(title_exact="Branch")
    br0, br1, br2 = (branches + [None, None, None])[:3]
    get_pawn = find_all(title_exact="GetPlayerPawn")[0]
    isv = find_all(title_exact="IsValid")[0]
    locs = find_all(title_exact="Get Actor Location")
    pawn_loc = locs[0] if len(locs) > 0 else None
    self_loc = locs[1] if len(locs) > 1 else None
    sub = find_all(title_exact="vector - vector")[0] if find_all(title_exact="vector - vector") else None
    vsize = find_all(title_substr="Vector Length XY")[0] if find_all(title_substr="Vector Length XY") else None
    lte = find_all(title_substr="float <= float")[0] if find_all(title_substr="float <= float") else None
    printn = find_all(title_exact="PrintString")[0] if find_all(title_exact="PrintString") else None
    spawns = find_all(title_substr="SpawnActor")
    if not spawns:
        spawns = find_all(title_substr="BeginSpawning")
    mks = find_all(title_exact="Make Transform") or find_all(title_substr="MakeTransform")

    wires = []
    # Tick -> br0 (!started)
    wires.append(connect(tick, "then", br0, "execute"))
    wires.append(connect(get_started, "bStarted", notb, "A"))
    wires.append(connect(notb, "ReturnValue", br0, "Condition"))
    # br0 -> get_pawn is pure; br0.then -> br1, condition IsValid(pawn)
    wires.append(connect(br0, "then", br1, "execute"))
    wires.append(connect(get_pawn, "ReturnValue", isv, "Object") if pin(isv, "Object") else connect(get_pawn, "ReturnValue", isv, "InputObject"))
    wires.append(connect(isv, "ReturnValue", br1, "Condition"))
    # distance pure into br2 condition
    wires.append(connect(br1, "then", br2, "execute"))
    if get_pawn and pawn_loc:
        wires.append(connect(get_pawn, "ReturnValue", pawn_loc, "self"))
    if pawn_loc and sub:
        wires.append(connect(pawn_loc, "ReturnValue", sub, "A"))
    if self_loc and sub:
        wires.append(connect(self_loc, "ReturnValue", sub, "B"))
    if sub and vsize:
        wires.append(connect(sub, "ReturnValue", vsize, "A"))
    if vsize and lte:
        wires.append(connect(vsize, "ReturnValue", lte, "A"))
    if lte:
        setdef(lte, "B", "1200.0")
        wires.append(connect(lte, "ReturnValue", br2, "Condition"))
    # br2 -> set started -> spawn1 -> spawn2 -> print
    wires.append(connect(br2, "then", set_started, "execute"))

    # Setup transforms: self_loc + offsets
    # MakeTransform Location defaults
    if len(mks) >= 2 and self_loc:
        # Use vector + vector nodes — or hardcode spawn locations near Stage2
        setdef(mks[0], "Location", "9420.0,1920.0,98.0")
        setdef(mks[1], "Location", "8680.0,2060.0,98.0")
        setdef(mks[0], "Rotation", "0.0,180.0,0.0")
        setdef(mks[1], "Rotation", "0.0,180.0,0.0")
        setdef(mks[0], "Scale", "1.0,1.0,1.0")
        setdef(mks[1], "Scale", "1.0,1.0,1.0")

    if len(spawns) >= 2:
        for i, sp in enumerate(spawns[:2]):
            setdef(sp, "Class", ZOMBIE_C)
            setdef(sp, "ActorClass", ZOMBIE_C)
            # Collision handling
            for pn in ("CollisionHandlingOverride", "SpawnCollisionHandlingOverride"):
                if pin(sp, pn):
                    setdef(sp, pn, "AlwaysSpawn")
            if i < len(mks):
                # SpawnTransform or Transform pin
                for pn in ("SpawnTransform", "Transform"):
                    if pin(sp, pn) and pin(mks[i], "ReturnValue"):
                        wires.append(connect(mks[i], "ReturnValue", sp, pn))
        wires.append(connect(set_started, "then", spawns[0], "execute"))
        wires.append(connect(spawns[0], "then", spawns[1], "execute"))
        if printn:
            wires.append(connect(spawns[1], "then", printn, "execute"))
    elif len(spawns) == 1:
        setdef(spawns[0], "Class", ZOMBIE_C)
        setdef(spawns[0], "ActorClass", ZOMBIE_C)
        wires.append(connect(set_started, "then", spawns[0], "execute"))
        if printn:
            wires.append(connect(spawns[0], "then", printn, "execute"))
    else:
        log("NO SPAWN NODES")

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    log(f"status={bp.status}")
    try:
        for n in ed.list_nodes_with_errors() or []:
            log(f"ERR {ops._node_title(n)}")
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(PVE)

    # Level: ensure PVE at center, remove stale auto zombies (runtime spawn instead), hide click
    try:
        les.load_level(LEVEL)
    except Exception:
        pass

    for a in list(unreal.EditorLevelLibrary.get_all_level_actors() or []):
        lab = a.get_actor_label()
        if lab.startswith("Stage2_AutoZombie") or lab == "Stage2_PVE_ClickLabel":
            unreal.EditorLevelLibrary.destroy_actor(a)
            log(f"destroyed {lab}")
        if lab == "Stage2_PVE":
            for c in a.get_components_by_class(unreal.PrimitiveComponent):
                if "Click" in c.get_name() or "SpawnMore" in c.get_name():
                    try:
                        c.set_visibility(False)
                        c.set_hidden_in_game(True)
                        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                    except Exception:
                        pass

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
        log("spawned Stage2_PVE")
    else:
        pve.set_actor_location(CENTER, False, True)

    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log({"wires": wires})
    return wires


RESULT = {"log": LOG, "wires": rebuild()}
