"""Fix HoloCorner head-pop + Stage1 floating black air pixels (Quest).

Cause:
- 33 Stationary DecorFill_HoloCorner lights exceed Quest local-light budget;
  facing a light prioritizes it, looking away culls it ("shuts off").
- PPV film grain reads as transparent black pixels floating in air.

Run in Unreal (L_XRTemplate open):
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_holo_lights_vr_cull.py"
"""
from __future__ import annotations

import unreal

KEEP_ALWAYS = {"DecorFill_HoloCorner37", "DecorFill_HoloCorner39"}
LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(str(msg))
    unreal.log(f"[HoloLightFix] {msg}")


def setp(obj, name: str, value) -> bool:
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        return False


def main():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(sub.get_all_level_actors() or [])
    if not actors:
        raise RuntimeError("No level actors — open L_XRTemplate first")

    for a in actors:
        if a.get_actor_label() != "PPV_Indoor_Lab":
            continue
        s = a.settings
        setp(s, "override_film_grain_intensity", True)
        setp(s, "film_grain_intensity", 0.0)
        setp(s, "override_ambient_occlusion_intensity", True)
        setp(s, "ambient_occlusion_intensity", 0.0)
        log("PPV film_grain=0 AO=0")

    holos = sorted(
        [a for a in actors if (a.get_actor_label() or "").startswith("DecorFill_HoloCorner")],
        key=lambda a: a.get_actor_label(),
    )
    kept = hidden = 0
    for i, a in enumerate(holos):
        lb = a.get_actor_label()
        comp = a.get_component_by_class(unreal.PointLightComponent)
        if not comp:
            continue
        keep = lb in KEEP_ALWAYS or (i % 4 == 0)
        setp(comp, "visible", bool(keep))
        if keep:
            setp(comp, "mobility", unreal.ComponentMobility.STATIONARY)
            setp(comp, "intensity", 3.2 if lb in KEEP_ALWAYS else 2.4)
            setp(comp, "attenuation_radius", 900.0)
            setp(comp, "cast_shadows", False)
            setp(comp, "cast_volumetric_shadow", False)
            setp(comp, "volumetric_scattering_intensity", 0.0)
            setp(comp, "soft_source_radius", 160.0)
            setp(comp, "specular_scale", 0.35)
            kept += 1
        else:
            hidden += 1
    log(f"holo kept={kept} hidden={hidden}")

    for a in actors:
        lb = a.get_actor_label() or ""
        loc = a.get_actor_location()
        near = (4000 <= loc.x <= 5600 and -1200 <= loc.y <= 1200) or (
            abs(loc.x) < 900 and abs(loc.y) < 900
        )
        if not near:
            continue
        for cls in (unreal.SpotLightComponent, unreal.PointLightComponent, unreal.RectLightComponent):
            c = a.get_component_by_class(cls)
            if not c:
                continue
            setp(c, "cast_volumetric_shadow", False)
            setp(c, "volumetric_scattering_intensity", 0.0)
            setp(c, "contact_shadow_length", 0.0)
            if lb.startswith("DecorFill_") or "Fill" in lb:
                setp(c, "cast_shadows", False)
            elif isinstance(c, unreal.SpotLightComponent) and (
                "PlayerStart" in lb or lb.startswith("SpotLight")
            ):
                setp(c, "cast_shadows", False)
            break

    for a in actors:
        if a.get_actor_label() == "Env_HeightFog":
            fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            if fc:
                setp(fc, "enable_volumetric_fog", False)
        if a.get_actor_label() in ("Env_MoonLight", "Env_Sun"):
            c = a.get_component_by_class(unreal.DirectionalLightComponent)
            if c:
                setp(c, "cast_volumetric_shadow", False)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("SAVED")
    return {"log": LOG}


RESULT = main()
