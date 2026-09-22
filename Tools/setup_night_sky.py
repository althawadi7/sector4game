"""
Night scene for sector4v2 — Fab Moon + starry sky.

Uses marketplace asset:
  /Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/setup_night_sky.py"
"""

import unreal

FAB_MESH = "/Engine/BasicShapes/Sphere"
FAB_MAT = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Materials/Material_26"
)
SKY_MAT = "/Game/CursorTest/Materials/M_Sector4_NightSky"
STAR_TEX = "/Game/ParagonRampage/Characters/Global/Textures/Noise/T_Starfield_Noise02"
MAP_CENTER = unreal.Vector(200.0, 600.0, 0.0)
MOON_LOC = unreal.Vector(200.0, 600.0, 14000.0)
MOON_SCALE = unreal.Vector(116.0, 116.0, 116.0)
MOON_ROT = unreal.Rotator(pitch=-15.0, yaw=35.0, roll=0.0)
MOON_LIT_MAT = "/Game/CursorTest/Materials/M_Sector4_MoonLit"
MOON_TEX_0 = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_0"
)
MOON_TEX_1 = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_1"
)
MOON_TEX_2 = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_2"
)


def find_actor(label):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def destroy_actor(label):
    actor = find_actor(label)
    if actor:
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)


def ensure_star_material():
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/CursorTest/Materials"):
        unreal.EditorAssetLibrary.make_directory("/Game/CursorTest/Materials")
    if not unreal.EditorAssetLibrary.does_asset_exist(SKY_MAT):
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(
            "M_Sector4_NightSky",
            "/Game/CursorTest/Materials",
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    else:
        mat = unreal.EditorAssetLibrary.load_asset(SKY_MAT)

    mel = unreal.MaterialEditingLibrary
    mel.delete_all_material_expressions(mat)
    tex = unreal.EditorAssetLibrary.load_asset(STAR_TEX)
    alt_tex = unreal.EditorAssetLibrary.load_asset(
        "/Game/FootPrintsFX/Resources/other_texture/T_Star"
    )

    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    uv2 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1100, 260)
    uv_scale = mel.create_material_expression(mat, unreal.MaterialExpressionConstant2Vector, -950, 80)
    uv_scale.set_editor_property("r", 6.0)
    uv_scale.set_editor_property("g", 6.0)
    uv_mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -850, 20)
    mel.connect_material_expressions(uv, "", uv_mul, "A")
    mel.connect_material_expressions(uv_scale, "", uv_mul, "B")

    sample = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -650, 20)
    sample.set_editor_property("texture", tex)
    mel.connect_material_expressions(uv_mul, "", sample, "UVs")
    sample2 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -650, 260)
    sample2.set_editor_property("texture", alt_tex)
    mel.connect_material_expressions(uv2, "", sample2, "UVs")

    p1 = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -650, 140)
    p1.set_editor_property("r", 8.0)
    s1 = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -450, 40)
    mel.connect_material_expressions(sample, "", s1, "Base")
    mel.connect_material_expressions(p1, "", s1, "Exp")
    p2 = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -450, 280)
    p2.set_editor_property("r", 3.0)
    s2 = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -250, 260)
    mel.connect_material_expressions(sample2, "", s2, "Base")
    mel.connect_material_expressions(p2, "", s2, "Exp")

    combined = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -50, 120)
    mel.connect_material_expressions(s1, "", combined, "A")
    mel.connect_material_expressions(s2, "", combined, "B")
    sat = mel.create_material_expression(mat, unreal.MaterialExpressionSaturate, 120, 120)
    mel.connect_material_expressions(combined, "", sat, "")

    white = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, 120, 240)
    white.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    stars = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, 320, 140)
    mel.connect_material_expressions(sat, "", stars, "A")
    mel.connect_material_expressions(white, "", stars, "B")
    bright = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, 320, 260)
    bright.set_editor_property("r", 25.0)
    stars_bright = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, 520, 160)
    mel.connect_material_expressions(stars, "", stars_bright, "A")
    mel.connect_material_expressions(bright, "", stars_bright, "B")

    mel.connect_material_property(stars_bright, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(SKY_MAT)

    return mat


def setup_night_sky(sky_mat):
    destroy_actor("Sector4_SkyDome")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = find_actor("Sector4_NightSky")
    if not actor:
        bp = unreal.EditorAssetLibrary.load_blueprint_class("/Engine/EngineSky/BP_Sky_Sphere")
        actor = eas.spawn_actor_from_class(bp, MAP_CENTER, unreal.Rotator(0, 0, 0))
        actor.set_actor_label("Sector4_NightSky")
    actor.set_actor_location(MAP_CENTER, False, False)
    actor.set_actor_scale3d(unreal.Vector(1000.0, 1000.0, 1000.0))
    actor.set_folder_path("Env/NightSky")
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        comp.set_material(0, sky_mat)
        comp.set_cast_shadow(False)


def create_moon_lit_material():
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/CursorTest/Materials"):
        unreal.EditorAssetLibrary.make_directory("/Game/CursorTest/Materials")
    mel = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(MOON_LIT_MAT):
        mat = unreal.EditorAssetLibrary.load_asset(MOON_LIT_MAT)
        mel.delete_all_material_expressions(mat)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(
            "M_Sector4_MoonLit", "/Game/CursorTest/Materials", unreal.Material, unreal.MaterialFactoryNew()
        )

    albedo_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_0)
    detail_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_1)
    normal_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_2)
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1000, 0)
    albedo = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -720, -60)
    albedo.set_editor_property("texture", albedo_tex)
    mel.connect_material_expressions(uv, "", albedo, "UVs")
    detail = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -720, 180)
    detail.set_editor_property("texture", detail_tex)
    detail.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    mel.connect_material_expressions(uv, "", detail, "UVs")
    blend = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -480, 40)
    mel.connect_material_expressions(albedo, "", blend, "A")
    mel.connect_material_expressions(detail, "", blend, "B")
    normal = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -720, 380)
    normal.set_editor_property("texture", normal_tex)
    normal.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    mel.connect_material_expressions(uv, "", normal, "UVs")
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -480, -180)
    tint.set_editor_property("constant", unreal.LinearColor(1.0, 0.97, 0.9, 1.0))
    tinted = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -280, 20)
    mel.connect_material_expressions(blend, "", tinted, "A")
    mel.connect_material_expressions(tint, "", tinted, "B")
    em_scale = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -280, 200)
    em_scale.set_editor_property("r", 1.15)
    emissive = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -80, 60)
    mel.connect_material_expressions(tinted, "", emissive, "A")
    mel.connect_material_expressions(em_scale, "", emissive, "B")
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -80, 260)
    rough.set_editor_property("r", 1.0)
    mel.connect_material_property(tinted, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mat.set_editor_property("two_sided", True)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(MOON_LIT_MAT)
    return mat


def setup_fab_moon():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = unreal.EditorAssetLibrary.load_asset(FAB_MESH)
    moon_mat = create_moon_lit_material()
    if not mesh:
        raise RuntimeError("Fab Moon mesh not found — import the Fab asset first.")

    destroy_actor("Sector4_MoonHalo")

    actor = find_actor("Sector4_Moon")
    if not actor:
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, MOON_LOC, MOON_ROT)
        actor.set_actor_label("Sector4_Moon")

    actor.set_actor_location(MOON_LOC, False, False)
    actor.set_actor_rotation(MOON_ROT, False)
    actor.set_actor_scale3d(MOON_SCALE)
    sm = actor.static_mesh_component
    sm.set_static_mesh(mesh)
    sm.set_material(0, moon_mat)
    sm.set_cast_shadow(False)
    sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    actor.set_folder_path("Env/NightSky")


def setup_lights():
    moon_light = find_actor("Env_MoonLight") or find_actor("Env_Sun")
    if moon_light:
        moon_light.set_actor_label("Env_MoonLight")
        moon_light.set_actor_rotation(unreal.Rotator(pitch=-89.0, yaw=35.0, roll=0.0), False)
        comp = moon_light.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_editor_property("intensity", 2.2)
        comp.set_editor_property("light_color", unreal.Color(175, 195, 255, 255))
        comp.set_editor_property("cast_shadows", True)
        comp.set_editor_property("atmosphere_sun_light", True)

    sky = find_actor("Env_SkyLight")
    if sky:
        comp = sky.get_component_by_class(unreal.SkyLightComponent)
        comp.set_editor_property("intensity", 0.55)
        comp.set_editor_property("light_color", unreal.Color(90, 110, 160, 255))
        comp.set_editor_property("real_time_capture", True)

    fog = find_actor("Env_HeightFog")
    if fog:
        comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", 0.012)
        comp.set_editor_property("start_distance", 1500.0)


def setup_post_process():
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


def main():
    unreal.EditorLoadingAndSavingUtils.load_map("/Game/XRFramework/Levels/L_XRTemplate")
    sky_mat = ensure_star_material()
    setup_night_sky(sky_mat)
    setup_fab_moon()
    setup_lights()
    setup_post_process()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("Sector4 night scene ready (Fab Moon + stars).")


main()
