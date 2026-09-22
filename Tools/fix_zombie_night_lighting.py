"""
Restore playable zombie-night lighting in L_XRTemplate.

Many level lights were hidden (visible=False) or set to 0; night-sky script
also crushed sun/sky intensities. This re-enables key lights at a darker-but-readable level.

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_zombie_night_lighting.py"
"""
from __future__ import annotations

import unreal

MAP = "/Game/XRFramework/Levels/L_XRTemplate"

# Spot intensities (lumens) — ~70% of quest2_lighting_optimize for moody night.
SPOT_LEVELS = {
    "Spot_GunTable2": 2.0,
    "Spot_GunTable3": 2.0,
    "Spot_GunTable4": 1.8,
    "Spot_GunTable5": 1.8,
    "Spot_GunTable6": 1.8,
    "Spot_GunTable7": 1.8,
    "Spot_GunTable8": 1.8,
    "Spot_PlayerStart": 2.0,
    "Spot_PlayerStart2": 1.8,
    "Spot_PlayerCombat": 2.6,
    "Spot_ZombieArena": 2.8,
    "Spot_ZombieGate": 2.4,
    "Spot_CreatureCapsule": 1.8,
    "Spot_HoloProjector": 1.6,
    "Spot_CenterPath": 1.5,
    "Spot_CapsuleRow": 1.5,
    "SpotLight": 2.0,
    "SpotLight2": 2.0,
    "SpotLight3": 2.0,
    "SpotLight4": 1.8,
    "SpotLight5": 10.0,
}

POINT_LEVELS = {
    "Zombie_Ambient_Dim": 2.5,
    "Fill_CharacterReadability": 4.0,
    "DecorFill_CapsuleRow": 1.8,
    "DecorFill_HoloCorner": 1.6,
    "DecorFill_LabDesks_Back": 2.2,
    "DecorFill_LabDesks_Front": 2.0,
    "DecorFill_OldCapsule": 1.6,
    "CapsuleFill_SM_LabCapsule05_Capsule": 2.0,
    "CapsuleFill_SM_LabCapsule05_Capsule2": 2.0,
    "CapsuleFill_SM_LabCapsule05_Capsule3": 2.0,
}

SPOT_EXTRA = {
    "CapsuleSpot_SM_LabCapsule05_Capsule": 2.4,
    "CapsuleSpot_SM_LabCapsule05_Capsule2": 2.4,
    "CapsuleSpot_SM_LabCapsule05_Capsule3": 2.4,
    "ZombieRim_ArenaRight": 2.0,
    "ZombieRim_Gate": 2.2,
    "ZombieRim_Gate2": 2.2,
}


def find_actor(label: str):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def enable_spot(label: str, intensity: float, radius: float = 900.0) -> None:
    actor = find_actor(label)
    if not actor:
        return
    comp = actor.get_component_by_class(unreal.SpotLightComponent)
    if not comp:
        return
    comp.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    comp.set_editor_property("intensity", float(intensity))
    comp.set_editor_property("attenuation_radius", float(radius))
    comp.set_editor_property("visible", True)
    comp.set_editor_property("cast_shadows", True)


def enable_point(label: str, intensity: float, radius: float = 1200.0) -> None:
    actor = find_actor(label)
    if not actor:
        return
    comp = actor.get_component_by_class(unreal.PointLightComponent)
    if not comp:
        return
    comp.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    comp.set_editor_property("intensity", float(intensity))
    comp.set_editor_property("attenuation_radius", float(radius))
    comp.set_editor_property("visible", True)
    comp.set_editor_property("cast_shadows", False)


def setup_global_lights() -> None:
    moon = find_actor("Env_MoonLight") or find_actor("Env_Sun")
    if moon:
        moon.set_actor_label("Env_MoonLight")
        comp = moon.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)
        comp.set_editor_property("intensity", 2.2)
        comp.set_editor_property("light_color", unreal.Color(175, 195, 255, 255))
        comp.set_editor_property("cast_shadows", True)
        comp.set_editor_property("atmosphere_sun_light", True)
        comp.set_editor_property("visible", True)

    sky = find_actor("Env_SkyLight")
    if sky:
        comp = sky.get_component_by_class(unreal.SkyLightComponent)
        comp.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)
        comp.set_editor_property("intensity", 0.55)
        comp.set_editor_property("light_color", unreal.Color(90, 110, 160, 255))
        comp.set_editor_property("cast_shadows", False)
        comp.set_editor_property("real_time_capture", True)
        comp.set_editor_property("visible", True)
        try:
            comp.recapture_sky()
        except Exception:
            pass

    fog = find_actor("Env_HeightFog")
    if fog:
        fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        fc.set_editor_property("fog_density", 0.012)
        fc.set_editor_property("start_distance", 1500.0)


def setup_post_process() -> None:
    ppv = find_actor("PPV_Indoor_Lab")
    if not ppv:
        return
    s = ppv.settings
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_HISTOGRAM
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 0.15
    s.override_auto_exposure_min_brightness = True
    s.auto_exposure_min_brightness = 0.35
    s.override_auto_exposure_max_brightness = True
    s.auto_exposure_max_brightness = 2.5
    s.override_bloom_intensity = True
    s.bloom_intensity = 0.35
    s.override_bloom_threshold = True
    s.bloom_threshold = 1.0
    ppv.settings = s


def main() -> None:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    setup_global_lights()
    for label, intensity in SPOT_LEVELS.items():
        enable_spot(label, intensity)
    for label, intensity in SPOT_EXTRA.items():
        enable_spot(label, intensity, radius=750.0)
    for label, intensity in POINT_LEVELS.items():
        enable_point(label, intensity)
    setup_post_process()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("fix_zombie_night_lighting: lights re-enabled for dark playable night.")


if __name__ == "__main__":
    main()
