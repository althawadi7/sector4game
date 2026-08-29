"""
Fix ABP_SciFiVRFullBody compile errors (broken cast / HandLeft / HandRight / VROrigin).

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_abp_scifi_vr_fullbody.py"
"""
import unreal

ABP = "/Game/SciFiCharacterPack/VR/ABP_SciFiVRFullBody"
PAWN = "/Game/XRFramework/Blueprints/BP_XRPawn"


def _po(node, name, out=False):
    return blueprint_ops._find_pin(node, name, "output" if out else "input")


def _link(pinlib, a, b):
    if a and b:
        return pinlib.try_create_connection(a, b)
    return False


def _pal(ed, name, x=0, y=0):
    return ed.create_node_from_name(name, unreal.Vector2D(float(x), float(y)), [])


def main():
    bp = unreal.load_asset(ABP)
    if not bp:
        unreal.log_error(f"Missing {ABP}")
        return

    ed, _ = blueprint_ops._editor_for(bp, "EventGraph")
    pinlib = blueprint_ops._pinlib()
    bel = blueprint_ops._bel()

    keep = blueprint_ops._find_node(ed, "Event BlueprintUpdateAnimation")
    if not keep:
        unreal.log_error("BlueprintUpdateAnimation event not found")
        return

    ed.remove_nodes([n for n in (ed.list_all_nodes() or []) if n != keep])

    pawn_owner = ed.add_call_function_node("/Script/Engine.AnimInstance.TryGetPawnOwner")
    cast = _pal(ed, "Utilities|Casting|CastToBP_XRPawn", 280, 0)
    get_hl = _pal(ed, "Class|BPXRPawn|GetHandLeft", 560, -120)
    get_hr = _pal(ed, "Class|BPXRPawn|GetHandRight", 560, 40)
    get_vr = _pal(ed, "Class|BPXRPawn|GetVROrigin", 560, 200)
    loc_l = ed.add_call_function_node("/Script/Engine.SceneComponent.K2_GetComponentLocation")
    loc_r = ed.add_call_function_node("/Script/Engine.SceneComponent.K2_GetComponentLocation")
    loc_v = ed.add_call_function_node("/Script/Engine.SceneComponent.K2_GetComponentLocation")
    set_left = ed.add_set_member_variable_node("LeftHandLoc")
    set_right = ed.add_set_member_variable_node("RightHandLoc")
    lerp_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.VLerp")
    lerp_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.VLerp")
    set_le = ed.add_set_member_variable_node("LeftElbowHint")
    set_re = ed.add_set_member_variable_node("RightElbowHint")
    get_vel = ed.add_call_function_node("/Script/Engine.Actor.GetVelocity")
    vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.VSize")
    gt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    set_speed = ed.add_set_member_variable_node("Speed")
    set_move = ed.add_set_member_variable_node("bIsMoving")

    pinlib.set_pin_value(_po(lerp_l, "Alpha"), "0.5")
    pinlib.set_pin_value(_po(lerp_r, "Alpha"), "0.5")
    pinlib.set_pin_value(_po(gt, "B"), "10.0")

    _link(pinlib, _po(pawn_owner, "ReturnValue", True), _po(cast, "Object"))
    _link(pinlib, _po(cast, "AsBP XRPawn", True), _po(get_hl, "self"))
    _link(pinlib, _po(cast, "AsBP XRPawn", True), _po(get_hr, "self"))
    _link(pinlib, _po(cast, "AsBP XRPawn", True), _po(get_vr, "self"))
    _link(pinlib, _po(get_hl, "HandLeft", True), _po(loc_l, "self"))
    _link(pinlib, _po(get_hr, "HandRight", True), _po(loc_r, "self"))
    _link(pinlib, _po(get_vr, "VROrigin", True), _po(loc_v, "self"))
    _link(pinlib, _po(loc_l, "ReturnValue", True), _po(set_left, "LeftHandLoc"))
    _link(pinlib, _po(loc_r, "ReturnValue", True), _po(set_right, "RightHandLoc"))
    _link(pinlib, _po(loc_v, "ReturnValue", True), _po(lerp_l, "A"))
    _link(pinlib, _po(loc_l, "ReturnValue", True), _po(lerp_l, "B"))
    _link(pinlib, _po(lerp_l, "ReturnValue", True), _po(set_le, "LeftElbowHint"))
    _link(pinlib, _po(loc_v, "ReturnValue", True), _po(lerp_r, "A"))
    _link(pinlib, _po(loc_r, "ReturnValue", True), _po(lerp_r, "B"))
    _link(pinlib, _po(lerp_r, "ReturnValue", True), _po(set_re, "RightElbowHint"))
    _link(pinlib, _po(cast, "AsBP XRPawn", True), _po(get_vel, "self"))
    _link(pinlib, _po(get_vel, "ReturnValue", True), _po(vsize, "A"))
    _link(pinlib, _po(vsize, "ReturnValue", True), _po(set_speed, "Speed"))
    _link(pinlib, _po(vsize, "ReturnValue", True), _po(gt, "A"))
    _link(pinlib, _po(gt, "ReturnValue", True), _po(set_move, "bIsMoving"))

    _link(pinlib, _po(keep, "then", True), _po(cast, "execute"))
    _link(pinlib, _po(cast, "then", True), _po(set_left, "execute"))
    _link(pinlib, _po(set_left, "then", True), _po(set_right, "execute"))
    _link(pinlib, _po(set_right, "then", True), _po(set_le, "execute"))
    _link(pinlib, _po(set_le, "then", True), _po(set_re, "execute"))
    _link(pinlib, _po(set_re, "then", True), _po(set_speed, "execute"))
    _link(pinlib, _po(set_speed, "then", True), _po(set_move, "execute"))

    bel.compile_blueprint(bp)
    unreal.log(f"ABP_SciFiVRFullBody compile status: {bp.status}")

    errs = ed.list_nodes_with_errors() or []
    for n in errs:
        try:
            unreal.log_warning(f"Node error: {blueprint_ops._node_title(n)} — {n.get_editor_property('ErrorMsg')}")
        except Exception:
            unreal.log_warning(f"Node error: {blueprint_ops._node_title(n)}")

    unreal.EditorAssetLibrary.save_asset(ABP)

    # Re-wire PlayerBody on pawn if needed
    pawn_bp = unreal.load_asset(PAWN)
    if pawn_bp and bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE:
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for h in subsys.k2_gather_subobject_data_for_blueprint(pawn_bp):
            data = subsys.k2_find_subobject_data_from_handle(h)
            name = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            if name == "PlayerBody" and isinstance(obj, unreal.SkeletalMeshComponent):
                obj.set_editor_property("anim_class", bp.generated_class())
                unreal.log("PlayerBody anim_class -> ABP_SciFiVRFullBody")
        unreal.BlueprintEditorLibrary.compile_blueprint(pawn_bp)
        unreal.EditorAssetLibrary.save_asset(PAWN)

    unreal.log("fix_abp_scifi_vr_fullbody DONE")


main()
