"""
Run inside Unreal Editor (Output Log -> py) to verify / finish SciFi VR body setup.

  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/setup_scifi_vr_body.py"
"""

import unreal

VR = "/Game/SciFiCharacterPack/VR"
PAWN = "/Game/XRFramework/Blueprints/BP_XRPawn"
WHITE_MAT = "/Game/SciFiCharacterPack/SciFiSoldier/Materials/MI_SciFiSoldier"

LEFT_MESH = f"{VR}/SKM_SciFiSoldier_XR_left"
RIGHT_MESH = f"{VR}/SKM_SciFiSoldier_XR_right"
ABP = f"{VR}/ABP_SciFiSoldierXR"
BODY_BP = f"{VR}/BP_SciFiBodyVR"


def _ensure_white_arm_materials():
    mat = unreal.EditorAssetLibrary.load_asset(WHITE_MAT)
    for path in (LEFT_MESH, RIGHT_MESH):
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not mesh or not mat:
            unreal.log_warning(f"Missing mesh or material: {path}")
            continue
        sm = unreal.SkeletalMaterial()
        sm.material_interface = mat
        mesh.set_editor_property("materials", [sm])
        unreal.EditorAssetLibrary.save_asset(path)
        unreal.log(f"Applied white SciFi material -> {path}")


def _apply_hand_templates():
    abp_cls = unreal.EditorAssetLibrary.load_blueprint_class(ABP)
    left_mesh = unreal.EditorAssetLibrary.load_asset(LEFT_MESH)
    right_mesh = unreal.EditorAssetLibrary.load_asset(RIGHT_MESH)
    if not abp_cls or not left_mesh or not right_mesh:
        unreal.log_error("SciFi VR assets missing. Re-import /Game/SciFiCharacterPack/VR.")
        return False

    base = f"{PAWN}.{PAWN.split('/')[-1]}_C"
    left = unreal.load_object(None, f"{base}:HandLeft_GEN_VARIABLE")
    right = unreal.load_object(None, f"{base}:HandRight_GEN_VARIABLE")
    for obj, mesh in ((left, left_mesh), (right, right_mesh)):
        obj.set_editor_property("SkeletalMesh", mesh)
        obj.set_editor_property("SkeletalMeshAsset", mesh)
        obj.set_editor_property("AnimClass", abp_cls)

    bp = unreal.EditorAssetLibrary.load_asset(PAWN)
    bp.modify()
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(PAWN)
    unreal.log("BP_XRPawn hands -> white SciFi VR arm meshes (logic unchanged).")
    return True


def _log_manual_body_step():
    unreal.log(
        "Optional torso: open BP_XRPawn -> Add Child Actor Component 'PlayerBody' on VROrigin "
        f"-> Child Actor Class = {BODY_BP} -> Location (0,0,-88) Rotation (0,-90,0) -> Compile."
    )


def main():
    _ensure_white_arm_materials()
    if _apply_hand_templates():
        _log_manual_body_step()


main()
