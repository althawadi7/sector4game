"""Step 2: BP_GrenadeLauncher — wire Quest 3 axis edge to poll branch condition."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"
PATH = "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


bp = unreal.load_asset(PATH + ".BP_GrenadeLauncher")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

poll = bo._find_node(ed, POLL)
br = None
for n in ed.list_all_nodes() or []:
    if bo._node_title(n) != "Branch":
        continue
    ex = bel.find_execute_pin(n)
    for pin in pl.list_connected_pins(ex) or []:
        if pin.get_owning_node() == poll:
            br = n
            break
if not br:
    unreal.log_error("BP_GrenadeLauncher step2: no poll branch")
else:
    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")

    ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    bo._set_node_pos(ax, 1100, 900)
    pl.set_pin_value(p(ax, "Key"), AXIS_L)
    ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    bo._set_node_pos(ge, 1250, 900)
    pl.set_pin_value(p(ge, "B"), "0.55")
    link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
    link(pl, p(ax, "ReturnValue", True), p(ge, "A"))

    td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    bo._set_node_pos(td, 1100, 980)
    pl.set_pin_value(p(td, "Key"), AXIS_L)
    lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    bo._set_node_pos(lt, 1250, 980)
    pl.set_pin_value(p(lt, "B"), "0.12")
    link(pl, p(pc, "ReturnValue", True), p(td, "self"))
    link(pl, p(td, "ReturnValue", True), p(lt, "A"))

    and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    bo._set_node_pos(and_l, 1400, 940)
    link(pl, p(ge, "ReturnValue", True), p(and_l, "A"))
    link(pl, p(lt, "ReturnValue", True), p(and_l, "B"))

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

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    bo._set_node_pos(or_n, 1550, 1040)
    link(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
    link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
    ok = link(pl, p(or_n, "ReturnValue", True), p(br, "Condition"))
    unreal.log("BP_GrenadeLauncher step2 quest3 cond=" + str(ok))

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(PATH)
unreal.log("BP_GrenadeLauncher step2 compile " + str(bp.status))
