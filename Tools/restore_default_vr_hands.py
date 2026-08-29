"""
Remove SciFi full-body avatar — use default floating XR mannequin hands only.

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/restore_default_vr_hands.py"
"""
import unreal

PAWN = "/Game/XRFramework/Blueprints/BP_XRPawn"
LEFT_MESH = "/Game/XRMannequins/Meshes/SKM_MannyXR_left"
RIGHT_MESH = "/Game/XRMannequins/Meshes/SKM_MannyXR_right"
ABP = "/Game/XRMannequins/Meshes/ABP_MannequinsXR"


def main():
    pawn_bp = unreal.load_asset(PAWN)
    left_mesh = unreal.load_asset(LEFT_MESH)
    right_mesh = unreal.load_asset(RIGHT_MESH)
    abp_bp = unreal.load_asset(ABP)
    unreal.BlueprintEditorLibrary.compile_blueprint(abp_bp)
    abp_cls = abp_bp.generated_class()

    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

    for h in subsys.k2_gather_subobject_data_for_blueprint(pawn_bp):
        data = subsys.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or "")
        obj = lib.get_object(data)

        if name in ("HandLeft", "HandRight") and isinstance(obj, unreal.SkeletalMeshComponent):
            mesh = left_mesh if name == "HandLeft" else right_mesh
            obj.set_skeletal_mesh_asset(mesh)
            obj.set_editor_property("anim_class", abp_cls)
            obj.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
            obj.set_editor_property("hidden_in_game", False)
            obj.set_editor_property("owner_no_see", False)
            obj.set_editor_property("visible", True)

        if name == "PlayerBody" and isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_skeletal_mesh_asset(None)
            obj.set_editor_property("anim_class", None)
            obj.set_editor_property("hidden_in_game", True)
            obj.set_editor_property("visible", False)
            obj.set_editor_property("owner_no_see", True)

        if name == "SciFiAvatar" and isinstance(obj, unreal.ChildActorComponent):
            try:
                obj.set_editor_property("child_actor_class", None)
            except Exception:
                pass
            obj.set_editor_property("hidden_in_game", True)

    unreal.BlueprintEditorLibrary.compile_blueprint(pawn_bp)
    unreal.EditorAssetLibrary.save_asset(PAWN)
    unreal.log("Default VR hands restored. SciFi full body hidden.")


main()
