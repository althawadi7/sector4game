"""Grenade = bouncing physics projectile. Bullets = larger visible mesh/collision."""
import sys
from pathlib import Path

import unreal

PLUGIN_PY = Path(__file__).resolve().parents[1] / "Plugins/CursorUnrealBridge/Content/Python"
if str(PLUGIN_PY) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PY))

import cursor_unreal_bridge.blueprint_ops as bo  # noqa: E402

BULLET = "/Game/XRFramework/Blueprints/BP_Projectile"
GRENADE = "/Game/XRFramework/Blueprints/BP_BombProjectile"

BULLET_MESH_SCALE = unreal.Vector(0.38, 0.38, 0.38)
BULLET_RADIUS = 0.18

# Short-range VR launcher toss (~3-5 m from nozzle; Unreal units are cm).
GRENADE_LAUNCH_SPEED = 780.0
GRENADE_SETTINGS = {
    "InitialSpeed": GRENADE_LAUNCH_SPEED,
    "MaxSpeed": 1100.0,
    "ProjectileGravityScale": 1.15,
    "bShouldBounce": True,
    "Bounciness": 0.62,
    "Friction": 0.35,
}


def subobject(bp, suffix):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(handle)
        name = str(lib.get_display_name(data))
        if name.endswith(suffix):
            return lib.get_object(data), name
    return None, None


def set_subobject_props(asset_path, suffix, props):
    bp = unreal.load_asset(asset_path)
    obj, name = subobject(bp, suffix)
    if not obj:
        raise RuntimeError(f"{asset_path}: missing {suffix}")
    for prop, value in props.items():
        obj.set_editor_property(prop, value)
    return name


def set_velocity_pin(asset_path, speed):
    bp = unreal.load_asset(asset_path)
    editor, _ = bo._editor_for(bp, "EventGraph")
    pinlib = unreal.BlueprintGraphPinLibrary
    for node in editor.list_all_nodes() or []:
        if bo._node_title(node) != "SetVelocityInLocalSpace":
            continue
        for pin in unreal.BlueprintEditorLibrary.list_all_pins(node) or []:
            if str(pinlib.get_pin_name(pin)) == "NewVelocity":
                pinlib.set_pin_value(pin, f"X={speed},Y=0.0,Z=0.0")
                return True
    return False


def verify_spawn(asset_path):
    bp = unreal.load_asset(asset_path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        bp.generated_class(), unreal.Vector(0, 0, 6000)
    )
    out = {}
    for comp in actor.get_components_by_class(
        unreal.load_class(None, "/Script/Engine.ProjectileMovementComponent")
    ):
        out["gravity"] = comp.get_editor_property("ProjectileGravityScale")
        out["bounce"] = comp.get_editor_property("bShouldBounce")
        out["bounciness"] = comp.get_editor_property("Bounciness")
        out["speed"] = comp.get_editor_property("InitialSpeed")
    for comp in actor.get_components_by_class(
        unreal.load_class(None, "/Script/Engine.SphereComponent")
    ):
        out["radius"] = comp.get_editor_property("SphereRadius")
    for comp in actor.get_components_by_class(
        unreal.load_class(None, "/Script/Engine.StaticMeshComponent")
    ):
        out["scale"] = comp.get_editor_property("RelativeScale3D")
    unreal.EditorLevelLibrary.destroy_actor(actor)
    return out


def main():
    bel = unreal.BlueprintEditorLibrary

    bullet_mesh = set_subobject_props(
        BULLET + ".BP_Projectile",
        "StaticMesh_GEN_VARIABLE",
        {"RelativeScale3D": BULLET_MESH_SCALE},
    )
    bullet_sphere = set_subobject_props(
        BULLET + ".BP_Projectile",
        "SphereCollision_GEN_VARIABLE",
        {"SphereRadius": BULLET_RADIUS},
    )

    grenade_pmc = set_subobject_props(
        GRENADE + ".BP_BombProjectile",
        "ProjectileMovement_GEN_VARIABLE",
        GRENADE_SETTINGS,
    )
    set_velocity_pin(GRENADE + ".BP_BombProjectile", GRENADE_LAUNCH_SPEED)

    for path in (BULLET, GRENADE):
        bp = unreal.load_asset(path + "." + path.split("/")[-1])
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(path)

    print("bullet mesh", bullet_mesh, "scale", BULLET_MESH_SCALE)
    print("bullet sphere", bullet_sphere, "radius", BULLET_RADIUS)
    print("grenade pmc", grenade_pmc, GRENADE_SETTINGS)
    print("verify bullet", verify_spawn(BULLET + ".BP_Projectile"))
    print("verify grenade", verify_spawn(GRENADE + ".BP_BombProjectile"))


if __name__ == "__main__":
    main()
