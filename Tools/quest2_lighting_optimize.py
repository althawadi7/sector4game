"""
Meta Quest 2 lighting + SciFiWorld material optimization for L_XRTemplate.

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/quest2_lighting_optimize.py"
"""

import unreal


def find_actor(label):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def set_light_static(comp, intensity=None, shadows=True):
    comp.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    comp.set_editor_property("cast_shadows", shadows)
    try:
        comp.set_editor_property("cast_dynamic_shadows", False)
    except Exception:
        pass
    try:
        comp.set_editor_property("cast_static_shadows", shadows)
    except Exception:
        pass
    if intensity is not None:
        comp.set_editor_property("intensity", float(intensity))


def optimize_lights():
    sun = find_actor("Env_Sun")
    if sun:
        set_light_static(sun.get_component_by_class(unreal.DirectionalLightComponent), 3.2, True)

    sky = find_actor("Env_SkyLight")
    if sky:
        sc = sky.get_component_by_class(unreal.SkyLightComponent)
        sc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        sc.set_editor_property("intensity", 0.65)
        sc.set_editor_property("cast_shadows", False)
        sc.set_editor_property("real_time_capture", False)
        try:
            sc.recapture_sky()
        except Exception:
            pass

    spots = {
        "Spot_GunTable": 2.8,
        "Spot_PlayerStart": 2.6,
        "Spot_ZombieGate": 3.2,
        "Spot_CreatureCapsule": 2.4,
        "Spot_HoloProjector": 2.2,
        "Spot_CenterPath": 2.0,
        "Spot_ZombieArena": 3.8,
        "Spot_PlayerCombat": 3.4,
    }
    for label, intensity in spots.items():
        actor = find_actor(label)
        if not actor:
            continue
        comp = actor.get_component_by_class(unreal.SpotLightComponent)
        set_light_static(comp, intensity, True)
        comp.set_editor_property("attenuation_radius", 900.0)

    ambient = find_actor("Zombie_Ambient_Dim")
    if ambient:
        set_light_static(ambient.get_component_by_class(unreal.PointLightComponent), 0.35, False)


def optimize_fog():
    fog = find_actor("Env_HeightFog")
    if not fog:
        return
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.028)
    fc.set_editor_property("fog_height_falloff", 0.18)
    fc.set_editor_property("start_distance", 1200.0)
    fc.set_editor_property("fog_cutoff_distance", 6500.0)


def optimize_lightmass():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = world.get_world_settings()
    lm = ws.get_editor_property("lightmass_settings")
    lm.set_editor_property("static_lighting_level_scale", 1.0)
    lm.set_editor_property("num_indirect_lighting_bounces", 2)
    lm.set_editor_property("num_sky_lighting_bounces", 2)
    lm.set_editor_property("indirect_lighting_quality", 2.0)
    lm.set_editor_property("indirect_lighting_smoothness", 0.75)
    lm.set_editor_property("use_ambient_occlusion", True)
    lm.set_editor_property("direct_illumination_occlusion_fraction", 0.6)
    lm.set_editor_property("indirect_illumination_occlusion_fraction", 0.85)
    lm.set_editor_property("max_occlusion_distance", 260.0)
    ws.set_editor_property("lightmass_settings", lm)


def simplify_scifiworld_materials():
    mel = unreal.MaterialEditingLibrary
    parents = [
        "/Game/SciFiWorld/Shared/Materials/M_Base_PBR",
        "/Game/SciFiWorld/Shared/Materials/M_Base_PBR_Emissive",
        "/Game/SciFiWorld/Shared/Materials/M_Base_PBR_EmissiveA",
        "/Game/SciFiWorld/Shared/Materials/M_Base_PBR_EmissiveB",
        "/Game/SciFiWorld/Shared/Materials/M_Base_PBR_Alpha_Emissive",
    ]
    for path in parents:
        mat = unreal.EditorAssetLibrary.load_asset(path)
        if not mat:
            continue
        names = [
            e.get_editor_property("parameter_name")
            for e in mel.get_material_expressions(mat)
            if "ScalarParameter" in e.get_class().get_name()
        ]
        if "Roughness" not in names:
            rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -420, 260)
            rough.set_editor_property("parameter_name", "Roughness")
            rough.set_editor_property("default_value", 0.58)
            met = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -420, 380)
            met.set_editor_property("parameter_name", "Metallic")
            met.set_editor_property("default_value", 0.06)
            mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
            mel.connect_material_property(met, "", unreal.MaterialProperty.MP_METALLIC)
            unreal.EditorAssetLibrary.save_asset(path)

    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.scan_paths_synchronous(["/Game/SciFiWorld"], True)
    count = 0
    for asset in reg.get_assets_by_path("/Game/SciFiWorld", recursive=True):
        if str(asset.asset_class_path.asset_name) != "MaterialInstanceConstant":
            continue
        pkg = str(asset.package_name)
        name = str(asset.asset_name)
        mi = unreal.EditorAssetLibrary.load_asset(f"{pkg}.{name}")
        if not mi:
            continue
        parent = mi.get_editor_property("parent")
        if not parent or "M_Base_PBR" not in parent.get_path_name():
            continue
        if any(x in parent.get_path_name() for x in ("Glass", "Hologram", "Screen", "Water", "Particle")):
            continue
        mel.set_material_instance_scalar_parameter_value(mi, "Roughness", 0.58)
        mel.set_material_instance_scalar_parameter_value(mi, "Metallic", 0.06)
        try:
            mel.set_material_instance_texture_parameter_value(mi, "MaskMap", None)
        except Exception:
            pass
        unreal.EditorAssetLibrary.save_asset(f"{pkg}.{name}")
        count += 1
    unreal.log(f"Updated {count} SciFiWorld material instances.")


def main():
    unreal.EditorLoadingAndSavingUtils.load_map("/Game/XRFramework/Levels/L_XRTemplate")
    optimize_lights()
    optimize_fog()
    optimize_lightmass()
    simplify_scifiworld_materials()
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.build_light_maps()
    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("Quest 2 lighting optimization complete.")


main()
