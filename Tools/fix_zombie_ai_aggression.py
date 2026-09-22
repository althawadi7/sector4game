"""Zombie AI fixes for sector4v2 — conservative locomotion + blackboard boot.

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_zombie_ai_aggression.py"
"""
from __future__ import annotations

import unreal
import cursor_unreal_bridge.blueprint_ops as bo

# Stock-ish values — avoid strafe skating and huge stop radii.
MOVE_ACCEPT_RADIUS = 5.0
ATTACK_RANGE = 100.0
NAV_BOUNDS_SCALE = unreal.Vector(1.15, 1.0, 8.0)


def restore_behavior_tree() -> None:
    btd = unreal.load_asset("/Game/Zombie/Blueprints/Behavior/BTD_IsInRange.BTD_IsInRange")
    unreal.get_default_object(btd.generated_class()).set_editor_property("AcceptanceRadius", ATTACK_RANGE)
    unreal.EditorAssetLibrary.save_asset("/Game/Zombie/Blueprints/Behavior/BTD_IsInRange")

    bt = unreal.load_asset("/Game/Zombie/Blueprints/Behavior/BT_Zombie.BT_Zombie")

    def walk(comp):
        if not comp:
            return
        for ch in comp.children or []:
            for dec in ch.decorators or []:
                if "IsInRange" in dec.get_class().get_name():
                    dec.set_editor_property("AcceptanceRadius", ATTACK_RANGE)
            if ch.child_task:
                task = ch.child_task
                if task.get_class().get_name() == "BTTask_MoveTo":
                    radius = task.get_editor_property("AcceptableRadius")
                    radius.set_editor_property("DefaultValue", MOVE_ACCEPT_RADIUS)
                    task.set_editor_property("AcceptableRadius", radius)
                    strafe = task.get_editor_property("bAllowStrafe")
                    strafe.set_editor_property("DefaultValue", False)
                    task.set_editor_property("bAllowStrafe", strafe)
            if ch.child_composite:
                walk(ch.child_composite)

    walk(bt.root_node)
    unreal.EditorAssetLibrary.save_asset("/Game/Zombie/Blueprints/Behavior/BT_Zombie")

    btt = unreal.load_asset("/Game/Zombie/Blueprints/Behavior/BTT_PlayMontage.BTT_PlayMontage")
    ed, _ = bo._editor_for(btt, "EventGraph")
    pinlib = bo._pinlib()
    for node in ed.list_all_nodes() or []:
        if node.get_name() == "K2Node_PromotableOperator_0":
            for pin in bo._bel().list_all_pins(node) or []:
                if str(pin.get_pin_name()) == "B":
                    pinlib.set_pin_value(pin, str(ATTACK_RANGE))
    bo._bel().compile_blueprint(btt)
    unreal.EditorAssetLibrary.save_asset("/Game/Zombie/Blueprints/Behavior/BTT_PlayMontage")


def restore_pawn_movement() -> None:
    pawn_bp = unreal.load_asset("/Game/Zombie/Blueprints/BP_Zombie_Pawn.BP_Zombie_Pawn")
    cdo = unreal.get_default_object(pawn_bp.generated_class())
    mc = cdo.get_editor_property("character_movement")
    mc.set_editor_property("bUseRVOAvoidance", False)
    mc.set_editor_property("bOrientRotationToMovement", True)
    mc.set_editor_property("bUseControllerDesiredRotation", False)
    props = mc.nav_agent_props
    props.agent_radius = -1.0
    props.agent_height = -1.0
    mc.set_editor_property("nav_agent_props", props)
    unreal.EditorAssetLibrary.save_asset("/Game/Zombie/Blueprints/BP_Zombie_Pawn")


def restore_nav_bounds() -> None:
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_class().get_name() == "NavMeshBoundsVolume":
            actor.set_actor_scale3d(NAV_BOUNDS_SCALE)


def fix_run_behavior_tree_wiring() -> None:
    path = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
    aic = unreal.load_asset(path + ".BP_Zombie_AiController_Base")
    ed, _ = bo._editor_for(aic, "EventGraph")
    pinlib = bo._pinlib()

    def node(name: str):
        return next(n for n in ed.list_all_nodes() if n.get_name() == name)

    run_exec = bo._find_pin(node("K2Node_CallFunction_24"), "execute")
    if not pinlib.list_connected_pins(run_exec):
        pinlib.break_pin_links(bo._find_pin(node("K2Node_AddDelegate_1"), "then", prefer_direction="output"))
        pinlib.try_create_connection(
            bo._find_pin(node("K2Node_AddDelegate_1"), "then", prefer_direction="output"),
            bo._find_pin(node("K2Node_CallFunction_24"), "execute"),
        )

    seq0 = node("K2Node_ExecutionSequence_0")
    for pin in bo._bel().list_all_pins(seq0) or []:
        if str(pin.get_pin_name()) == "then_2":
            pinlib.break_pin_links(pin)

    bo._bel().compile_blueprint(aic)
    unreal.EditorAssetLibrary.save_asset(path)


def fix_blackboard_boot_order() -> None:
    path = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
    aic = unreal.load_asset(path + ".BP_Zombie_AiController_Base")
    ed, _ = bo._editor_for(aic, "EventGraph")
    pinlib = bo._pinlib()
    bel = bo._bel()

    run = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_24")
    tryup = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_23")
    set_vec = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_2")
    set_bool = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_14")
    timer = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_5")

    pinlib.break_pin_links(bo._find_pin(run, "then", prefer_direction="output"))
    pinlib.break_pin_links(bo._find_pin(tryup, "execute"))
    pinlib.break_pin_links(bo._find_pin(set_vec, "execute"))
    pinlib.try_create_connection(
        bo._find_pin(run, "then", prefer_direction="output"),
        bo._find_pin(set_vec, "execute"),
    )
    pinlib.try_create_connection(
        bo._find_pin(set_vec, "then", prefer_direction="output"),
        bo._find_pin(set_bool, "execute"),
    )
    pinlib.try_create_connection(
        bo._find_pin(set_bool, "then", prefer_direction="output"),
        bel.find_execute_pin(timer),
    )

    ed_fn, _ = bo._editor_for(aic, "TryUpdateTargetActorIfNotSet")
    set_obj = next(n for n in ed_fn.list_all_nodes() if n.get_name() == "K2Node_CallFunction_38")
    pinlib.break_pin_links(bel.find_execute_pin(set_obj))

    bel.compile_blueprint(aic)
    unreal.EditorAssetLibrary.save_asset(path)


def fix_ai_controller() -> None:
    path = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
    aic = unreal.load_asset(path + ".BP_Zombie_AiController_Base")
    ed, _ = bo._editor_for(aic, "EventGraph")
    pinlib = bo._pinlib()
    bel = bo._bel()

    set_vec = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_2")
    set_bool = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_14")
    key_spawn = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_VariableGet_6")
    key_roam = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_VariableGet_0")

    for target, key_node in ((set_vec, key_spawn), (set_bool, key_roam)):
        kn = bo._find_pin(target, "KeyName")
        pinlib.break_pin_links(kn)
        key_out = next(p for p in bel.list_all_pins(key_node) or [] if str(p.get_pin_name()) != "self")
        pinlib.try_create_connection(key_out, kn)

    aggro = next((n for n in ed.list_all_nodes() if bo._node_title(n) == "AggroScanPlayer"), None)
    if aggro is None:
        aggro = ed.add_custom_event_node("AggroScanPlayer")
        bo._set_node_pos(aggro, 3000, 3600)

    get_pawn = next((n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_1"), None)
    if get_pawn is None:
        get_pawn = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerPawn")
        bo._set_node_pos(get_pawn, 3200, 3750)

    try_update = next(
        (
            n
            for n in ed.list_all_nodes()
            if bo._node_title(n) == "TryUpdateTargetActorByLowestPathCost"
            and bo._find_pin(n, "execute") is not None
            and n.get_name() != "K2Node_CallFunction_45"
        ),
        None,
    )
    if try_update is None:
        try_update = ed.add_call_function_node(
            "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base.BP_Zombie_AiController_Base:TryUpdateTargetActorByLowestPathCost"
        )
        bo._set_node_pos(try_update, 3450, 3600)

    pinlib.try_create_connection(bel.find_then_pin(aggro), bel.find_execute_pin(try_update))
    pinlib.try_create_connection(bel.find_result_pin(get_pawn), bel.find_input_pin(try_update, "Actor"))

    timer = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_5")
    for pin_name, value in {
        "FunctionName": "AggroScanPlayer",
        "Time": "0.75",
        "bLooping": "true",
        "InitialStartDelay": "0.35",
    }.items():
        pin = bo._find_pin(timer, pin_name)
        pinlib.break_pin_links(pin)
        pinlib.set_pin_value(pin, value)

    bel.compile_blueprint(aic)
    unreal.EditorAssetLibrary.save_asset(path)


def rebuild_nav_mesh() -> None:
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")


def main() -> None:
    fix_run_behavior_tree_wiring()
    fix_blackboard_boot_order()
    restore_behavior_tree()
    restore_pawn_movement()
    restore_nav_bounds()
    fix_ai_controller()
    rebuild_nav_mesh()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("fix_zombie_ai_aggression: locomotion restored, blackboard boot kept.")


if __name__ == "__main__":
    main()
