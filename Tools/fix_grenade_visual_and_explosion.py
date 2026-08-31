"""Grenade: nozzle-sized dark round, ground collision, light explosion, no debug spam."""
import sys
from pathlib import Path

import unreal

PLUGIN_PY = Path(__file__).resolve().parents[1] / "Plugins/CursorUnrealBridge/Content/Python"
if str(PLUGIN_PY) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PY))

import cursor_unreal_bridge.blueprint_ops as bo  # noqa: E402

GRENADE_BP = "/Game/XRFramework/Blueprints/BP_BombProjectile"
GUN_BP = "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"
GRENADE_MESH = "/Game/Weapons/GrenadeLauncher/Meshes/FirstPersonProjectileMesh.FirstPersonProjectileMesh"
GRENADE_MAT = "/Game/Weapons/GrenadeLauncher/Materials/M_GrenadeLauncher.M_GrenadeLauncher"
EXPLOSION_FX = "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_02.FXS_NS_ShotBurst_02"
SMOKE_FX = "/Game/NiagaraExamples/Utilities/SpriteGeneration/SmokePuffLight/NS_SmokePuffLight.NS_SmokePuffLight"

MESH_SCALE = unreal.Vector(0.025, 0.025, 0.025)
SPHERE_RADIUS = 0.045
EXPLOSION_SCALE = "0.45,0.45,0.45"
SMOKE_SCALE = "0.35,0.35,0.35"
EXPLOSION_Z = 40.0


def find_node(ed, name):
    for node in ed.list_all_nodes() or []:
        if node.get_name() == name:
            return node
    return None


def find_pin(node, pin_name):
    for pin in bo._bel().list_all_pins(node) or []:
        if str(bo._pinlib().get_pin_name(pin)) == pin_name:
            return pin
    return None


def break_pin(pin):
    if pin:
        bo._pinlib().break_pin_links(pin)


def connect(a, b):
    if a and b:
        return bo._pinlib().try_create_connection(a, b)
    return False


def bypass_vrshoot_prints(ed):
    pinlib = bo._pinlib()
    removed = []
    for node in list(ed.list_all_nodes() or []):
        if "PrintString" not in bo._node_title(node):
            continue
        msg = pinlib.get_pin_value(find_pin(node, "InString")) or ""
        if "VRSHOOT" not in msg:
            continue
        ex = find_pin(node, "execute")
        then = find_pin(node, "then")
        up = pinlib.list_connected_pins(ex) or []
        down = pinlib.list_connected_pins(then) or []
        break_pin(ex)
        break_pin(then)
        if up and down:
            connect(up[0], down[0])
        removed.append(msg[:48])
    return removed


def fix_components(bp):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    mesh_asset = unreal.load_asset(GRENADE_MESH)
    mat_asset = unreal.load_asset(GRENADE_MAT)
    sphere_obj = None
    pmc_obj = None
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(handle)
        name = str(lib.get_display_name(data))
        obj = lib.get_object(data)
        if not obj:
            continue
        if name.endswith("StaticMesh_GEN_VARIABLE"):
            obj.set_editor_property("StaticMesh", mesh_asset)
            obj.set_editor_property("RelativeScale3D", MESH_SCALE)
            if mat_asset:
                obj.set_editor_property("OverrideMaterials", [mat_asset])
        elif name.endswith("SphereCollision_GEN_VARIABLE"):
            sphere_obj = obj
            obj.set_editor_property("SphereRadius", SPHERE_RADIUS)
            body = obj.get_editor_property("BodyInstance")
            body.set_editor_property("bUseCCD", True)
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_STATIC, unreal.CollisionResponseType.ECR_BLOCK
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_WORLD_DYNAMIC, unreal.CollisionResponseType.ECR_BLOCK
            )
            obj.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_BLOCK
            )
        elif name.endswith("ProjectileMovement_GEN_VARIABLE"):
            pmc_obj = obj
            obj.set_editor_property("InitialSpeed", 780.0)
            obj.set_editor_property("MaxSpeed", 1100.0)
            obj.set_editor_property("ProjectileGravityScale", 1.15)
            obj.set_editor_property("bShouldBounce", True)
            obj.set_editor_property("Bounciness", 0.55)
            obj.set_editor_property("Friction", 0.45)
            obj.set_editor_property("bForceSubStepping", True)
    if sphere_obj and pmc_obj:
        try:
            pmc_obj.set_editor_property("UpdatedComponent", sphere_obj)
        except Exception:
            pass
    return sphere_obj, pmc_obj


def fix_event_graph(bp):
    ed, _ = bo._editor_for(bp, "EventGraph")
    pinlib = bo._pinlib()
    bel = bo._bel()

    velocity = find_node(ed, "K2Node_CallFunction_34")
    spawn_fx = find_node(ed, "K2Node_CallFunction_30")
    actor_loc = find_node(ed, "K2Node_CallFunction_27")
    add = find_node(ed, "K2Node_PromotableOperator_5")
    pmc_get = find_node(ed, "K2Node_VariableGet_0")
    sphere_get = find_node(ed, "K2Node_VariableGet_3")
    setup = find_node(ed, "K2Node_CallFunction_38")
    if not setup:
        setup = ed.add_call_function_node("/Script/Engine.MovementComponent.SetUpdatedComponent")
        bo._set_node_pos(setup, 200, 120)
        connect(find_pin(pmc_get, "ProjectileMovement"), find_pin(setup, "self"))
        connect(find_pin(sphere_get, "SphereCollision"), find_pin(setup, "NewUpdatedComponent"))

    break_pin(find_pin(velocity, "then"))
    connect(find_pin(velocity, "then"), find_pin(setup, "execute"))

    pinlib.set_pin_value(find_pin(spawn_fx, "SystemTemplate"), EXPLOSION_FX)
    pinlib.set_pin_value(find_pin(spawn_fx, "Scale"), EXPLOSION_SCALE)
    if add:
        pinlib.set_pin_value(find_pin(add, "B"), f"X=0.0,Y=0.0,Z={EXPLOSION_Z}")
        break_pin(find_pin(add, "A"))
        connect(find_pin(actor_loc, "ReturnValue"), find_pin(add, "A"))

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(GRENADE_BP)


def main():
    grenade = unreal.load_asset(GRENADE_BP + ".BP_BombProjectile")
    fix_components(grenade)
    fix_event_graph(grenade)

    gun = unreal.load_asset(GUN_BP + ".BP_GrenadeLauncher")
    ged, _ = bo._editor_for(gun, "EventGraph")
    removed = bypass_vrshoot_prints(ged)
    unreal.BlueprintEditorLibrary.compile_blueprint(gun)
    unreal.EditorAssetLibrary.save_asset(GUN_BP)
    print("removed VRSHOOT prints:", removed)
    print("grenade status:", grenade.status)


if __name__ == "__main__":
    main()
