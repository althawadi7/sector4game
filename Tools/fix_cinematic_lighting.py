"""Cinematic zombie-night lighting — balanced pools, no hot spots.

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_cinematic_lighting.py"
"""
from __future__ import annotations

import unreal

MAP = "/Game/XRFramework/Levels/L_XRTemplate"

# Uniform motivated pools (lumens). Avoid 10+ blowouts.
SPOT_LEVELS = {
    "Spot_PlayerStart": 2.2,
    "Spot_PlayerStart2": 2.0,
    "Spot_PlayerCombat": 2.4,
    "Spot_ZombieArena": 2.6,
    "Spot_ZombieGate": 2.2,
    "Spot_CreatureCapsule": 1.9,
    "Spot_HoloProjector": 1.7,
    "Spot_CenterPath": 1.8,
    "Spot_GunTable2": 1.6,
    "Spot_GunTable3": 1.6,
    "Spot_GunTable4": 1.5,
    "Spot_GunTable5": 1.5,
    "Spot_GunTable6": 1.5,
    "Spot_GunTable7": 1.5,
    "Spot_GunTable8": 1.5,
    "SpotLight": 1.8,
    "SpotLight2": 1.8,
    "SpotLight3": 1.8,
    "SpotLight4": 1.6,
    "SpotLight5": 2.4,
    "CapsuleSpot_SM_LabCapsule05_Capsule": 2.0,
    "CapsuleSpot_SM_LabCapsule05_Capsule2": 2.0,
    "CapsuleSpot_SM_LabCapsule05_Capsule3": 2.0,
    "ZombieRim_ArenaRight": 1.8,
    "ZombieRim_Gate": 1.8,
    "ZombieRim_Gate2": 1.8,
}

POINT_LEVELS = {
    "Zombie_Ambient_Dim": 1.8,
    "Fill_CharacterReadability": 2.8,
    "DecorFill_CapsuleRow": 1.2,
    "DecorFill_HoloCorner": 1.0,
    "DecorFill_LabDesks_Back": 1.4,
    "DecorFill_LabDesks_Front": 1.2,
    "DecorFill_OldCapsule": 1.0,
    "CapsuleFill_SM_LabCapsule05_Capsule": 1.2,
    "CapsuleFill_SM_LabCapsule05_Capsule2": 1.2,
    "CapsuleFill_SM_LabCapsule05_Capsule3": 1.2,
}

# Hide micro-fills that stack with spots and cause uneven hotspots.
HIDE_POINT_LABELS = set()


def find_actor(label: str):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def tune_spot(label: str, intensity: float, radius: float = 1100.0, outer: float = 42.0) -> None:
    actor = find_actor(label)
    if not actor:
        return
    comp = actor.get_component_by_class(unreal.SpotLightComponent)
    if not comp:
        return
    comp.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    comp.set_editor_property("intensity", float(intensity))
    comp.set_editor_property("attenuation_radius", float(radius))
    comp.set_editor_property("inner_cone_angle", 18.0)
    comp.set_editor_property("outer_cone_angle", float(outer))
    comp.set_editor_property("soft_source_radius", 8.0)
    comp.set_editor_property("use_temperature", True)
    comp.set_editor_property("temperature", 4200.0)
    comp.set_editor_property("visible", True)
    comp.set_editor_property("cast_shadows", True)


def tune_point(label: str, intensity: float, radius: float = 1400.0, hide: bool = False) -> None:
    actor = find_actor(label)
    if not actor:
        return
    comp = actor.get_component_by_class(unreal.PointLightComponent)
    if not comp:
        return
    comp.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    comp.set_editor_property("intensity", float(intensity))
    comp.set_editor_property("attenuation_radius", float(radius))
    comp.set_editor_property("soft_source_radius", 120.0)
    comp.set_editor_property("use_temperature", True)
    comp.set_editor_property("temperature", 3800.0)
    comp.set_editor_property("visible", not hide)
    comp.set_editor_property("cast_shadows", False)


def setup_global() -> None:
    moon = find_actor("Env_MoonLight") or find_actor("Env_Sun")
    if moon:
        moon.set_actor_label("Env_MoonLight")
        comp = moon.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)
        comp.set_editor_property("intensity", 1.35)
        comp.set_editor_property("light_color", unreal.Color(160, 185, 255, 255))
        comp.set_editor_property("cast_shadows", True)
        comp.set_editor_property("atmosphere_sun_light", True)
        comp.set_editor_property("visible", True)

    sky = find_actor("Env_SkyLight")
    if sky:
        comp = sky.get_component_by_class(unreal.SkyLightComponent)
        comp.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)
        comp.set_editor_property("intensity", 0.42)
        comp.set_editor_property("light_color", unreal.Color(80, 100, 150, 255))
        comp.set_editor_property("real_time_capture", True)
        comp.set_editor_property("visible", True)
        try:
            comp.recapture_sky()
        except Exception:
            pass

    fog = find_actor("Env_HeightFog")
    if fog:
        fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        fc.set_editor_property("fog_density", 0.009)
        fc.set_editor_property("start_distance", 1800.0)
        fc.set_editor_property("fog_height_falloff", 0.25)


def setup_post() -> None:
    ppv = find_actor("PPV_Indoor_Lab")
    if not ppv:
        return
    s = ppv.settings
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_HISTOGRAM
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 0.08
    s.override_auto_exposure_min_brightness = True
    s.auto_exposure_min_brightness = 0.45
    s.override_auto_exposure_max_brightness = True
    s.auto_exposure_max_brightness = 2.2
    s.override_bloom_intensity = True
    s.bloom_intensity = 0.45
    s.override_bloom_threshold = True
    s.bloom_threshold = 0.85
    s.override_vignette_intensity = True
    s.vignette_intensity = 0.35
    ppv.settings = s


def main() -> None:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    setup_global()
    for label, intensity in SPOT_LEVELS.items():
        tune_spot(label, intensity)
    for label, intensity in POINT_LEVELS.items():
        tune_point(label, intensity, hide=label in HIDE_POINT_LABELS)
    setup_post()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("fix_cinematic_lighting: balanced cinematic night applied.")


if __name__ == "__main__":
    main()
