"""Grenade step 2b-ADD: right trigger nodes only. NO compile (safe)."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

AXIS_R = "OculusTouch_Right_Trigger_Axis"
PATH = "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


bp = unreal.load_asset(PATH + ".BP_GrenadeLauncher")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")

ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
bo._set_node_pos(ax2, 1100, 1100)
pl.set_pin_value(p(ax2, "Key"), AXIS_R)
ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
bo._set_node_pos(ge2, 1250, 1100)
pl.set_pin_value(p(ge2, "B"), "0.55")
link(pl, p(pc, "ReturnValue", True), p(ax2, "self"))
link(pl, p(ax2, "ReturnValue", True), p(ge2, "A"))

td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
bo._set_node_pos(td2, 1100, 1180)
pl.set_pin_value(p(td2, "Key"), AXIS_R)
lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
bo._set_node_pos(lt2, 1250, 1180)
pl.set_pin_value(p(lt2, "B"), "0.12")
link(pl, p(pc, "ReturnValue", True), p(td2, "self"))
link(pl, p(td2, "ReturnValue", True), p(lt2, "A"))

and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
bo._set_node_pos(and_r, 1400, 1140)
link(pl, p(ge2, "ReturnValue", True), p(and_r, "A"))
link(pl, p(lt2, "ReturnValue", True), p(and_r, "B"))

unreal.EditorAssetLibrary.save_asset(PATH)
unreal.log("grenade step2b-ADD done (no compile)")
