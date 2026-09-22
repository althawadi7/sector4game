"""MINIMAL shoot fix — small node add, one compile. Do not run twice."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"
PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
POLL = "PollReload"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"
KEY_L = "OculusTouch_Left_Trigger_Click"
KEY_R = "OculusTouch_Right_Trigger_Click"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def L(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


def U(pl, pin):
    if pin:
        pl.break_pin_links(pin)


bp = unreal.load_asset(GUN + ".BP_GunVR_UMP45")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
U(pl, spawn_exec)

# --- grab chain + timer ---
grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
en = bo._find_node(ed, "K2Node_CallFunction_4")
hide = bo._find_node(ed, "K2Node_Message_1")
add = bo._find_node(ed, "K2Node_CallFunction_13")
sel = bo._find_node(ed, "K2Node_Select_1")
if sel and add:
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    U(pl, p(add, "MappingContext"))
    L(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")

if grab and en and hide and add:
    U(pl, p(grab, "then", True))
    L(pl, p(grab, "then", True), p(en, "execute"))
    L(pl, p(en, "then", True), p(hide, "execute"))
    L(pl, p(hide, "then", True), p(add, "execute"))
    U(pl, p(add, "then", True))

grab_get = bo._find_node(ed, "K2Node_VariableGet_0")
get_owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
bo._set_node_pos(get_owner, 2050, 80)
L(pl, p(grab_get, "GrabComponentSnap", True), p(get_owner, "self"))

timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
bo._set_node_pos(timer, 2150, 200)
pl.set_pin_value(p(timer, "FunctionName"), POLL)
pl.set_pin_value(p(timer, "Time"), "0.05")
pl.set_pin_value(p(timer, "bLooping"), "true")
U(pl, p(timer, "Object"))
L(pl, p(get_owner, "ReturnValue", True), p(timer, "Object"))
timer_exec = bel.find_execute_pin(timer)
if timer_exec:
    L(pl, p(add, "then", True), timer_exec)

# --- PollReload + Quest axis branch -> spawn ---
poll = bo._find_node(ed, POLL)
if not poll:
    poll = ed.add_custom_event_node(POLL)
    bo._set_node_pos(poll, 900, 400)

br = ed.add_branch_node()
bo._set_node_pos(br, 1300, 400)
U(pl, p(poll, "then", True))
L(pl, p(poll, "then", True), bel.find_execute_pin(br))
L(pl, bel.find_then_pin(br), spawn_exec)

pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
if not pc:
    pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
    pl.set_pin_value(p(pc, "PlayerIndex"), "0")

# Quest axis edge (left)
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

# right hand
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
U(pl, p(br, "Condition"))
L(pl, p(or_n, "ReturnValue", True), p(br, "Condition"))

# --- drop clear timer ---
drop = bo._find_node(ed, "K2Node_ComponentBoundEvent_1")
show = bo._find_node(ed, "K2Node_Message_0")
dis = bo._find_node(ed, "K2Node_CallFunction_12")
rem = bo._find_node(ed, "K2Node_CallFunction_14")
clear = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_ClearTimer")
pl.set_pin_value(p(clear, "FunctionName"), POLL)
L(pl, p(get_owner, "ReturnValue", True), p(clear, "Object"))
if drop and show:
    U(pl, p(drop, "then", True))
    L(pl, p(drop, "then", True), p(show, "execute"))
    clear_exec = bel.find_execute_pin(clear)
    if dis and rem and clear_exec:
        L(pl, p(show, "then", True), p(dis, "execute"))
        L(pl, p(dis, "then", True), p(rem, "execute"))
        L(pl, p(rem, "then", True), clear_exec)
    elif clear_exec:
        L(pl, p(show, "then", True), clear_exec)

# IA triggers asset fix
for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
    path = "/Game/XRFramework/Input/Actions/" + name
    ia = unreal.load_asset(path + "." + name)
    if ia:
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t]
        if not triggers:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)

# ONE compile
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(GUN)
print("STATUS", bp.status)
spawn_in = [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(spawn_exec) or [])]
print("spawn<-", spawn_in)
then = bel.find_then_pin(add)
print("add->", [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(then) or [])])
