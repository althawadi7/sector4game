"""Wire complete Quest3 shoot chain on BP_GunVR_UMP45 from scratch.

WARNING: Do NOT run via bridge automation — can crash Unreal (BlueprintEditorLibrary AV).
Fix shoot manually in BP_GunVR_UMP45 Event Graph instead.
"""
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


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


bp = unreal.load_asset(GUN + ".BP_GunVR_UMP45")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

# --- spawn ---
spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
unlink(pl, spawn_exec)

# --- poll + quest3 branch -> spawn ---
poll = bo._find_node(ed, POLL)
if not poll:
    poll = ed.add_custom_event_node(POLL)
    bo._set_node_pos(poll, 900, 400)

br = ed.add_branch_node()
bo._set_node_pos(br, 1200, 400)
unlink(pl, p(poll, "then", True))
link(pl, p(poll, "then", True), bel.find_execute_pin(br))
link(pl, bel.find_then_pin(br), spawn_exec)

pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
if not pc:
    pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
    pl.set_pin_value(p(pc, "PlayerIndex"), "0")

ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
pl.set_pin_value(p(ax, "Key"), AXIS_L)
ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
pl.set_pin_value(p(ge, "B"), "0.55")
link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
link(pl, p(ax, "ReturnValue", True), p(ge, "A"))

td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
pl.set_pin_value(p(td, "Key"), AXIS_L)
lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
pl.set_pin_value(p(lt, "B"), "0.12")
link(pl, p(pc, "ReturnValue", True), p(td, "self"))
link(pl, p(td, "ReturnValue", True), p(lt, "A"))

and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
link(pl, p(ge, "ReturnValue", True), p(and_l, "A"))
link(pl, p(lt, "ReturnValue", True), p(and_l, "B"))

ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
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
link(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
unlink(pl, p(br, "Condition"))
link(pl, p(or_n, "ReturnValue", True), p(br, "Condition"))

# --- IMC on grab ---
sel = bo._find_node(ed, "K2Node_Select_1")
add = bo._find_node(ed, "K2Node_CallFunction_13")
if sel and add:
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    unlink(pl, p(add, "MappingContext"))
    link(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")

# --- grab -> timer ---
grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
en = bo._find_node(ed, "K2Node_CallFunction_4")
hide = bo._find_node(ed, "K2Node_Message_1")
if grab and en and hide and add:
    unlink(pl, p(grab, "then", True))
    link(pl, p(grab, "then", True), p(en, "execute"))
    link(pl, p(en, "then", True), p(hide, "execute"))
    link(pl, p(hide, "then", True), p(add, "execute"))

grab_get = bo._find_node(ed, "K2Node_VariableGet_0")
get_owner = None
if grab_get:
    get_owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
    link(pl, p(grab_get, "GrabComponentSnap", True), p(get_owner, "self"))

timer_ok = False
if add and get_owner:
    timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
    bo._set_node_pos(timer, 2100, 200)
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    unlink(pl, p(timer, "Object"))
    link(pl, p(get_owner, "ReturnValue", True), p(timer, "Object"))
    unlink(pl, p(add, "then", True))
    timer_exec = bel.find_execute_pin(timer)
    if timer_exec:
        timer_ok = link(pl, p(add, "then", True), timer_exec)

# --- drop -> clear timer ---
drop = bo._find_node(ed, "K2Node_ComponentBoundEvent_1")
show = bo._find_node(ed, "K2Node_Message_0")
dis = bo._find_node(ed, "K2Node_CallFunction_12")
rem = bo._find_node(ed, "K2Node_CallFunction_14")
clear = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_ClearTimer")
bo._set_node_pos(clear, 2100, 350)
pl.set_pin_value(p(clear, "FunctionName"), POLL)
if get_owner:
    unlink(pl, p(clear, "Object"))
    link(pl, p(get_owner, "ReturnValue", True), p(clear, "Object"))
if drop and show:
    unlink(pl, p(drop, "then", True))
    link(pl, p(drop, "then", True), p(show, "execute"))
    if dis and rem:
        link(pl, p(show, "then", True), p(dis, "execute"))
        link(pl, p(dis, "then", True), p(rem, "execute"))
        clear_exec = bel.find_execute_pin(clear)
        if clear_exec:
            link(pl, p(rem, "then", True), clear_exec)
    else:
        clear_exec = bel.find_execute_pin(clear)
        if clear_exec:
            link(pl, p(show, "then", True), clear_exec)

# --- IA triggers ---
for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
    path = "/Game/XRFramework/Input/Actions/" + name
    ia = unreal.load_asset(path + "." + name)
    if ia:
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t]
        if not triggers:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(GUN)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

spawn_in = [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(spawn_exec) or [])]
poll_out = [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(p(poll, "then", True)) or [])]
print("status", bp.status)
print("spawn<-", spawn_in)
print("poll->", poll_out)
print("timer_ok", timer_ok)

n = grab
for i in range(6):
    then = bel.find_then_pin(n)
    dest = [bo._node_title(c.get_owning_node()) for c in (pl.list_connected_pins(then) or [])]
    print(bo._node_title(n), "->", dest)
    if not pl.list_connected_pins(then):
        break
    n = pl.list_connected_pins(then)[0].get_owning_node()
