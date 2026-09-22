"""Grenade step 2b: add RIGHT trigger + OR (run after step2a)."""
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
poll = bo._find_node(ed, "PollReload")
br = None
for n in ed.list_all_nodes() or []:
    if bo._node_title(n) != "Branch":
        continue
    ex = bo._bel().find_execute_pin(n)
    for pin in pl.list_connected_pins(ex) or []:
        if pin.get_owning_node() == poll:
            br = n
            break
pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
cond = p(br, "Condition")
and_l_pin = None
for pin in pl.list_connected_pins(cond) or []:
    on = pin.get_owning_node()
    if bo._node_title(on) == "AND Boolean":
        and_l_pin = p(on, "ReturnValue", True)
        break
pl.break_pin_links(cond)
ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
bo._set_node_pos(ax2, 1100, 1100)
pl.set_pin_value(p(ax2, "Key"), AXIS_R)
ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
pl.set_pin_value(p(ge2, "B"), "0.55")
link(pl, p(pc, "ReturnValue", True), p(ax2, "self"))
link(pl, p(ax2, "ReturnValue", True), p(ge2, "A"))
td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
pl.set_pin_value(p(td2, "Key"), AXIS_R)
lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
pl.set_pin_value(p(lt2, "B"), "0.12")
link(pl, p(pc, "ReturnValue", True), p(td2, "self"))
link(pl, p(td2, "ReturnValue", True), p(lt2, "A"))
and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
link(pl, p(ge2, "ReturnValue", True), p(and_r, "A"))
link(pl, p(lt2, "ReturnValue", True), p(and_r, "B"))
or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
link(pl, and_l_pin, p(or_n, "A"))
link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
ok = link(pl, p(or_n, "ReturnValue", True), cond)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(PATH)
unreal.log("grenade step2b OR cond=" + str(ok) + " " + str(bp.status))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
