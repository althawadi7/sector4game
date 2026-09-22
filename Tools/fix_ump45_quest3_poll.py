"""Quest 3 poll fix + IA shoot backup for BP_GunVR_UMP45. One compile."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def L(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


def exec_out_pin(bel, pl, node, pin_name):
    for pin in bel.list_all_pins(node) or []:
        if bo._pin_name(pin) == pin_name:
            return pin
    return p(node, pin_name, True)


bp = unreal.load_asset(GUN + ".BP_GunVR_UMP45")
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

poll = bo._find_node(ed, "PollReload")
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
  br = bo._find_node(ed, "K2Node_IfThenElse_2")

# Quest axis edge -> branch condition
cond = p(br, "Condition")
pl.break_pin_links(cond)

pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
if not pc:
    pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
    pl.set_pin_value(p(pc, "PlayerIndex"), "0")

ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
pl.set_pin_value(p(ax, "Key"), AXIS_L)
ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
pl.set_pin_value(p(ge, "B"), "0.55")
L(pl, p(pc, "ReturnValue", True), p(ax, "self"))
L(pl, p(ax, "ReturnValue", True), p(ge, "A"))

td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
pl.set_pin_value(p(td, "Key"), AXIS_L)
lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
pl.set_pin_value(p(lt, "B"), "0.12")
L(pl, p(pc, "ReturnValue", True), p(td, "self"))
L(pl, p(td, "ReturnValue", True), p(lt, "A"))

and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
L(pl, p(ge, "ReturnValue", True), p(and_l, "A"))
L(pl, p(lt, "ReturnValue", True), p(and_l, "B"))

ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
pl.set_pin_value(p(ax2, "Key"), AXIS_R)
ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
pl.set_pin_value(p(ge2, "B"), "0.55")
L(pl, p(pc, "ReturnValue", True), p(ax2, "self"))
L(pl, p(ax2, "ReturnValue", True), p(ge2, "A"))

td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
pl.set_pin_value(p(td2, "Key"), AXIS_R)
lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
pl.set_pin_value(p(lt2, "B"), "0.12")
L(pl, p(pc, "ReturnValue", True), p(td2, "self"))
L(pl, p(td2, "ReturnValue", True), p(lt2, "A"))

and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
L(pl, p(ge2, "ReturnValue", True), p(and_r, "A"))
L(pl, p(lt2, "ReturnValue", True), p(and_r, "B"))

or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
L(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
L(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
L(pl, p(or_n, "ReturnValue", True), cond)

# IA -> hand branch -> call fire (use raw pins)
ia1 = bo._find_node(ed, "K2Node_EnhancedInputAction_1")
ia2 = bo._find_node(ed, "K2Node_EnhancedInputAction_2")
br0 = bo._find_node(ed, "K2Node_IfThenElse_0")
br1 = bo._find_node(ed, "K2Node_IfThenElse_1")
calls = [n for n in ed.list_all_nodes() or [] if bo._node_title(n) == "FireWeapon" and "CallFunction" in n.get_class().get_name()]
call_l = calls[0] if calls else None
call_r = calls[1] if len(calls) > 1 else None

if ia1 and br0:
    pl.break_pin_links(bel.find_execute_pin(br0))
    t_pin = exec_out_pin(bel, pl, ia1, "Triggered")
    e_pin = bel.find_execute_pin(br0)
    print("IA1 wire", L(pl, t_pin, e_pin))
if ia2 and br1:
    pl.break_pin_links(bel.find_execute_pin(br1))
    t_pin = exec_out_pin(bel, pl, ia2, "Triggered")
    e_pin = bel.find_execute_pin(br1)
    print("IA2 wire", L(pl, t_pin, e_pin))

# Also IA Triggered -> call fire direct backup
if ia1 and call_l:
    t_pin = exec_out_pin(bel, pl, ia1, "Triggered")
    # can't dual-wire Triggered to two targets - skip

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("STATUS", bp.status)
if bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE:
    unreal.EditorAssetLibrary.save_asset(GUN)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print("SAVED")
