"""
Fix Sector4_Moon stretch + pixelation — sphere mesh + clean moon material + sharp textures.

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_moon_texture.py"
"""
from __future__ import annotations

import unreal

MOON_LABEL = "Sector4_Moon"
SPHERE_MESH = "/Engine/BasicShapes/Sphere"
MOON_LIT_MAT = "/Game/CursorTest/Materials/M_Sector4_MoonLit"
MOON_TEX_ALBEDO = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_0"
)
MOON_TEX_DETAIL = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_1"
)
MOON_TEX_NORMAL = (
    "/Game/Fab/_FREE___A_large_rock_formation_in_the_middle_of_nowhere_-_Moon/"
    "source/Textures/source_texture_2"
)
# Fab rock mesh radius ~= 414 uu; old actor scale was 14 -> ~5800 uu radius.
# Engine sphere radius = 50 uu.
SPHERE_SCALE = 116.0


def find_actor(label: str):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def tune_texture(path: str, compression: unreal.TextureCompressionSettings, srgb: bool = True) -> None:
    tex = unreal.EditorAssetLibrary.load_asset(path)
    if not tex:
        return
    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_TRILINEAR)
    tex.set_editor_property("lod_bias", -1)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    tex.set_editor_property("never_stream", True)
    unreal.EditorAssetLibrary.save_asset(path)


def rebuild_moon_material() -> unreal.Material:
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/CursorTest/Materials"):
        unreal.EditorAssetLibrary.make_directory("/Game/CursorTest/Materials")

    mel = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(MOON_LIT_MAT):
        mat = unreal.EditorAssetLibrary.load_asset(MOON_LIT_MAT)
        mel.delete_all_material_expressions(mat)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(
            "M_Sector4_MoonLit",
            "/Game/CursorTest/Materials",
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )

    albedo_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_ALBEDO)
    detail_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_DETAIL)
    normal_tex = unreal.EditorAssetLibrary.load_asset(MOON_TEX_NORMAL)

    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1000, 0)
    uv.set_editor_property("coordinate_index", 0)

    albedo = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -720, -60)
    albedo.set_editor_property("texture", albedo_tex)
    mel.connect_material_expressions(uv, "", albedo, "UVs")

    detail = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -720, 180)
    detail.set_editor_property("texture", detail_tex)
    detail.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    mel.connect_material_expressions(uv, "", detail, "UVs")

    # Blend albedo + linear detail for sharper crater read.
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
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(MOON_LIT_MAT)
    return mat


def fix_moon_actor(mat: unreal.Material) -> None:
    actor = find_actor(MOON_LABEL)
    if not actor:
        unreal.log_warning(f"{MOON_LABEL} not found — spawn via setup_night_sky.py first.")
        return

    sphere = unreal.EditorAssetLibrary.load_asset(SPHERE_MESH)
    sm = actor.get_component_by_class(unreal.StaticMeshComponent)
    sm.set_static_mesh(sphere)
    sm.set_material(0, mat)
    sm.set_cast_shadow(False)
    sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

    scale = unreal.Vector(SPHERE_SCALE, SPHERE_SCALE, SPHERE_SCALE)
    actor.set_actor_scale3d(scale)
    actor.set_folder_path("Env/NightSky")


def main() -> None:
    tune_texture(MOON_TEX_ALBEDO, unreal.TextureCompressionSettings.TC_BC7, srgb=True)
    tune_texture(MOON_TEX_DETAIL, unreal.TextureCompressionSettings.TC_BC7, srgb=False)
    tune_texture(MOON_TEX_NORMAL, unreal.TextureCompressionSettings.TC_NORMALMAP, srgb=False)

    mat = rebuild_moon_material()
    fix_moon_actor(mat)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log("fix_moon_texture: Sector4_Moon sphere + sharp textures applied.")


if __name__ == "__main__":
    main()
