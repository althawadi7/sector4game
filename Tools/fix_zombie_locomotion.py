"""Restore natural zombie walk — fix skating/sliding and AI rotation.

Root cause: chase BT task forces RunningSpeed (380) while walk/jog anims play.
Also movement acceleration/rotation were too aggressive for foot-sync.

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_zombie_locomotion.py"
"""
from __future__ import annotations

import unreal

PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
AIC = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
BT = "/Game/Zombie/Blueprints/Behavior/BT_Zombie"

WALK_SPEED = 90.0
RUN_SPEED = 150.0
MAX_ACCEL = 480.0
BRAKE = 720.0
ROT_YAW = 180.0


def _walk_bt(comp) -> None:
    if not comp:
        return
    for ch in comp.children or []:
        if ch.child_task:
            task = ch.child_task
            cls = task.get_class().get_name()
            if cls == "BTTask_MoveTo":
                radius = task.get_editor_property("AcceptableRadius")
                radius.set_editor_property("DefaultValue", 5.0)
                task.set_editor_property("AcceptableRadius", radius)
                strafe = task.get_editor_property("bAllowStrafe")
                strafe.set_editor_property("DefaultValue", False)
                task.set_editor_property("bAllowStrafe", strafe)
            elif "SetMovementSpeed" in cls:
                task.set_editor_property("bRunningMode", False)
        if ch.child_composite:
            _walk_bt(ch.child_composite)


def fix_pawn() -> None:
    bp = unreal.load_asset(PAWN + ".BP_Zombie_Pawn")
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("WalkingSpeed", WALK_SPEED)
    cdo.set_editor_property("RunningSpeed", RUN_SPEED)
    cdo.set_editor_property("bUseRunSpeed", False)

    mc = cdo.get_editor_property("character_movement")
    mc.set_editor_property("max_walk_speed", WALK_SPEED)
    mc.set_editor_property("max_acceleration", MAX_ACCEL)
    mc.set_editor_property("braking_deceleration_walking", BRAKE)
    mc.set_editor_property("bUseRVOAvoidance", False)
    mc.set_editor_property("bOrientRotationToMovement", False)
    mc.set_editor_property("bUseControllerDesiredRotation", True)
    mc.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=ROT_YAW, roll=0.0))
    props = mc.nav_agent_props
    props.agent_radius = -1.0
    props.agent_height = -1.0
    mc.set_editor_property("nav_agent_props", props)
    unreal.EditorAssetLibrary.save_asset(PAWN)


def fix_ai_controller() -> None:
    bp = unreal.load_asset(AIC + ".BP_Zombie_AiController_Base")
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("bSetControlRotationFromPawnOrientation", False)
    unreal.EditorAssetLibrary.save_asset(AIC)


def fix_behavior_tree() -> None:
    bt = unreal.load_asset(BT + ".BT_Zombie")
    _walk_bt(bt.root_node)
    unreal.EditorAssetLibrary.save_asset(BT)


def fix_nav_bounds() -> None:
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_class().get_name() == "NavMeshBoundsVolume":
            actor.set_actor_scale3d(unreal.Vector(1.15, 1.0, 8.0))


def rebuild_nav() -> None:
    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")


def main() -> None:
    fix_pawn()
    fix_ai_controller()
    fix_behavior_tree()
    fix_nav_bounds()
    rebuild_nav()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log(
        f"fix_zombie_locomotion: walk={WALK_SPEED} run={RUN_SPEED} chase-run off accel={MAX_ACCEL}"
    )


if __name__ == "__main__":
    main()
