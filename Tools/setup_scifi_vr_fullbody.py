"""
Finish SciFi VR full-body attachment on BP_XRPawn.

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/setup_scifi_vr_fullbody.py"
"""

import unreal

PAWN = "/Game/XRFramework/Blueprints/BP_XRPawn"
BODY_MESH = "/Game/SciFiCharacterPack/SciFiSoldier/Meshes/SK_SciFiSoldier"
BODY_MAT = "/Game/SciFiCharacterPack/SciFiSoldier/Materials/MI_SciFiSoldier"
ABP = "/Game/SciFiCharacterPack/VR/ABP_SciFiVRFullBody"


def _comps(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = subsys.k2_gather_subobject_data_for_blueprint(bp)
    out = {}
    for h in handles:
        data = subsys.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or "")
        obj = lib.get_object(data)
        if name and name not in out and obj:
            out[name] = (h, obj)
    return out, subsys


def main():
    bp = unreal.load_asset(PAWN)
    abp = unreal.load_asset(ABP)
    mesh = unreal.load_asset(BODY_MESH)
    mat = unreal.load_asset(BODY_MAT)
    if not bp or not abp or not mesh:
        unreal.log_error("Missing pawn / ABP / body mesh")
        return

    comps, subsys = _comps(bp)
    body = comps.get("PlayerBody", (None, None))[1]
    vro_h = comps.get("VROrigin", (None, None))[0]
    body_h = comps.get("PlayerBody", (None, None))[0]

    if body_h and vro_h:
        try:
            subsys.attach_subobject(vro_h, body_h)
        except Exception as exc:
            unreal.log_warning(f"attach: {exc}")

    if body:
        body.set_skeletal_mesh_asset(mesh)
        body.set_editor_property("anim_class", abp.generated_class())
        body.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
        body.set_editor_property("hidden_in_game", False)
        body.set_editor_property("visible", True)
        body.set_editor_property("owner_no_see", False)
        body.set_editor_property("cast_shadow", True)
        body.set_editor_property("relative_location", unreal.Vector(0, 0, 0))
        body.set_editor_property("relative_rotation", unreal.Rotator(0, -90, 0))
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        try:
            body.set_material(0, mat)
        except Exception:
            pass
        try:
            body.set_editor_property(
                "visibility_based_anim_tick_option",
                unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES,
            )
        except Exception:
            pass

    for side in ("HandLeft", "HandRight"):
        hand = comps.get(side, (None, None))[1]
        if hand:
            # Keep for grab + IK targets, hide visuals so only full body shows
            hand.set_editor_property("hidden_in_game", True)
            hand.set_editor_property("owner_no_see", True)

    avatar = comps.get("SciFiAvatar", (None, None))[1]
    if avatar:
        avatar.set_editor_property("hidden_in_game", True)
        try:
            avatar.set_editor_property("child_actor_class", None)
        except Exception:
            pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(PAWN)
    unreal.EditorAssetLibrary.save_asset(ABP)
    unreal.log("SciFi VR full body ready: PlayerBody=SK_SciFiSoldier + ABP_SciFiVRFullBody (hand IK + walk/idle).")


main()
