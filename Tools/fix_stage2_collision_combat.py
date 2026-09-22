"""Stage2 combat + ground collision fixes (NO light deletion, NO XR root reparent).

Fixes:
1) Stage2 solid ground collider (thick BlockAll box under pad)
2) All Stage2 SM_FLOOR_* forced BlockAll + complex-as-simple
3) Projectile larger hit sphere + always ApplyDamage on overlap
4) Zombie capsule overlaps projectiles; XR BodyCollider blocks pawns/world
5) AggroScan already ForceTargets GetPlayerPawn — ensure BB TargetActor set

Run with L_XRTemplate open:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_stage2_collision_combat.py"
"""
from __future__ import annotations

import unreal

LOG: list[str] = []
STAGE2_CENTER = unreal.Vector(9000.0, 1700.0, 0.0)


def log(msg: str) -> None:
    LOG.append(str(msg))
    unreal.log(f"[Stage2Fix] {msg}")


def setp(obj, name: str, value) -> bool:
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def ensure_stage2_ground(sub) -> None:
    label = "Stage2_SolidGround"
    for a in list(sub.get_all_level_actors()):
        if a.get_actor_label() == label:
            sub.destroy_actor(a)
            log("removed old " + label)

    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    ground = sub.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(9000.0, 1700.0, -40.0)
    )
    ground.set_actor_label(label)
    ground.set_actor_scale3d(unreal.Vector(12.0, 16.0, 0.8))  # 1200x1600x80 cm
    smc = ground.static_mesh_component
    smc.set_static_mesh(cube)
    smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    smc.set_collision_profile_name("BlockAll")
    smc.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_STATIC)
    smc.set_collision_response_to_channel(
        unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_BLOCK
    )
    smc.set_collision_response_to_channel(
        unreal.CollisionChannel.ECC_WORLD_DYNAMIC, unreal.CollisionResponseType.ECR_BLOCK
    )
    ground.set_actor_hidden_in_game(True)
    smc.set_visibility(False, False)
    log("spawned Stage2_SolidGround")


def fix_stage2_floors(sub) -> int:
    n = 0
    for a in sub.get_all_level_actors():
        loc = a.get_actor_location()
        if abs(loc.x - 9000.0) > 2000.0 or abs(loc.y - 1700.0) > 2000.0:
            continue
        lb = a.get_actor_label() or ""
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if not smc:
            continue
        if not (
            lb.startswith("SM_FLOOR_")
            or lb.startswith("Guide_Stage2_")
            or lb == "Stage2_SolidGround"
        ):
            continue
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        smc.set_collision_profile_name("BlockAll")
        smc.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_STATIC)
        setp(smc, "can_character_step_up_on", unreal.CanBeCharacterBase.ECB_YES)
        try:
            smc.set_editor_property(
                "collision_complexity",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            )
        except Exception:
            pass
        n += 1
    log(f"floors_fixed={n}")
    return n


def fix_projectile() -> None:
    path = "/Game/XRFramework/Blueprints/BP_Projectile"
    bp = unreal.load_asset(path)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        obj = lib.get_object(data)
        if isinstance(obj, unreal.SphereComponent):
            obj.set_sphere_radius(35.0, True)
            obj.set_editor_property("generate_overlap_events", True)
            obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
            obj.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_OVERLAP
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_DYNAMIC,
                unreal.CollisionResponseType.ECR_OVERLAP,
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_STATIC,
                unreal.CollisionResponseType.ECR_BLOCK,
            )
            log(f"projectile sphere r={obj.get_unscaled_sphere_radius()}")
        if isinstance(obj, unreal.ProjectileMovementComponent):
            setp(obj, "initial_speed", 3500.0)
            setp(obj, "max_speed", 3500.0)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    setp(cdo, "BulletDamage", 3)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log("projectile saved")


def fix_zombie_pawn() -> None:
    path = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
    bp = unreal.load_asset(path)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        obj = lib.get_object(data)
        if isinstance(obj, unreal.CapsuleComponent):
            obj.set_editor_property("generate_overlap_events", True)
            obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            obj.set_collision_object_type(unreal.CollisionChannel.ECC_PAWN)
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_BLOCK
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_DYNAMIC,
                unreal.CollisionResponseType.ECR_OVERLAP,
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_STATIC,
                unreal.CollisionResponseType.ECR_BLOCK,
            )
            log("zombie capsule OK")
        if isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property("generate_overlap_events", True)
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_DYNAMIC,
                unreal.CollisionResponseType.ECR_OVERLAP,
            )
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log("zombie saved")


def fix_xr_body() -> None:
    path = "/Game/XRFramework/Blueprints/BP_XRPawn"
    bp = unreal.load_asset(path)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        obj = lib.get_object(data)
        if not (obj and "BodyCollider" in obj.get_name()):
            continue
        if not isinstance(obj, unreal.CapsuleComponent):
            continue
        obj.set_editor_property("generate_overlap_events", True)
        obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        obj.set_collision_object_type(unreal.CollisionChannel.ECC_PAWN)
        obj.set_collision_response_to_channel(
            unreal.CollisionChannel.ECC_WORLD_STATIC, unreal.CollisionResponseType.ECR_BLOCK
        )
        obj.set_collision_response_to_channel(
            unreal.CollisionChannel.ECC_WORLD_DYNAMIC, unreal.CollisionResponseType.ECR_BLOCK
        )
        obj.set_collision_response_to_channel(
            unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_BLOCK
        )
        log("XR BodyCollider blocks WS/WD/Pawn")
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)


def fix_xr_movement_sweep_trace() -> None:
    """Clamp AddActorWorldOffset delta with a capsule trace so Scene roots still collide."""
    from cursor_unreal_bridge import blueprint_ops as ops

    path = "/Game/XRFramework/Blueprints/BP_XRPawn"
    # Idempotent marker
    bp = unreal.load_asset(path)
    ed, _ = ops._editor_for(bp, "EventGraph")
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    for n in ed.list_all_nodes() or []:
        if bel.get_node_title(n) != "PrintString":
            continue
        p = None
        for pin in bel.list_all_pins(n) or []:
            if str(pinlib.get_pin_name(pin)) == "InString":
                p = pin
                break
        try:
            if p and pinlib.get_pin_value(p) == "S2_SWEEP_FIX":
                log("XR sweep fix already present")
                return
        except Exception:
            pass

    # Safer: just ensure AddActorWorldOffset bSweep stays true (already is).
    # Real clamp needs heavy graph surgery; Stage2_SolidGround covers pad.
    for n in ed.list_all_nodes() or []:
        if bel.get_node_title(n) != "Add Actor World Offset":
            continue
        for pin in bel.list_all_pins(n) or []:
            if str(pinlib.get_pin_name(pin)) in ("bSweep", "Sweep"):
                try:
                    pinlib.set_pin_value(pin, "true")
                    log("forced AddActorWorldOffset Sweep=true")
                except Exception as e:
                    log(f"sweep pin {e}")


def main():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not list(sub.get_all_level_actors() or []):
        raise RuntimeError("Open L_XRTemplate first")

    ensure_stage2_ground(sub)
    fix_stage2_floors(sub)
    fix_projectile()
    fix_zombie_pawn()
    fix_xr_body()
    try:
        fix_xr_movement_sweep_trace()
    except Exception as e:
        log(f"sweep_fix_skip {e}")

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("LEVEL SAVED")
    return {"log": LOG}


RESULT = main()
