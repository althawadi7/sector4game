"""Clean Quest shoot path: poll+timer+branch->spawn only. Fixes compile errors."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"
PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"

bp = unreal.load_asset("/Game/GunVR/BP_GunVR_UMP45.BP_GunVR_UMP45")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(a, b):
    return pl.try_create_connection(a, b) if a and b else False


def find_poll_branch(poll):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) != "Branch":
            continue
        ex = bel.find_execute_pin(n)
        for pin in pl.list_connected_pins(ex) or []:
            if pin.get_owning_node() == poll:
                return n
    return None


def wire_quest3_edge(br):
    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
    if not pc:
        pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
        pl.set_pin_value(p(pc, "PlayerIndex"), "0")

    ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    pl.set_pin_value(p(ax, "Key"), AXIS_L)
    ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    pl.set_pin_value(p(ge, "B"), "0.55")
    link(p(pc, "ReturnValue", True), p(ax, "self"))
    link(p(ax, "ReturnValue", True), p(ge, "A"))

    td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    pl.set_pin_value(p(td, "Key"), AXIS_L)
    lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    pl.set_pin_value(p(lt, "B"), "0.12")
    link(p(pc, "ReturnValue", True), p(td, "self"))
    link(p(td, "ReturnValue", True), p(lt, "A"))

    and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    link(p(ge, "ReturnValue", True), p(and_l, "A"))
    link(p(lt, "ReturnValue", True), p(and_l, "B"))

    ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    pl.set_pin_value(p(ax2, "Key"), AXIS_R)
    ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    pl.set_pin_value(p(ge2, "B"), "0.55")
    link(p(pc, "ReturnValue", True), p(ax2, "self"))
    link(p(ax2, "ReturnValue", True), p(ge2, "A"))

    td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    pl.set_pin_value(p(td2, "Key"), AXIS_R)
    lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    pl.set_pin_value(p(lt2, "B"), "0.12")
    link(p(pc, "ReturnValue", True), p(td2, "self"))
    link(p(td2, "ReturnValue", True), p(lt2, "A"))

    and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    link(p(ge2, "ReturnValue", True), p(and_r, "A"))
    link(p(lt2, "ReturnValue", True), p(and_r, "B"))

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    link(p(and_l, "ReturnValue", True), p(or_n, "A"))
    link(p(and_r, "ReturnValue", True), p(or_n, "B"))

    cond = p(br, "Condition")
    pl.break_pin_links(cond)
    return link(p(or_n, "ReturnValue", True), cond)


# spawn setup
spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
pl.break_pin_links(spawn_exec)

# remove stray FireWeapon custom event wiring mistakes
fire_evt = bo._find_node(ed, "FireWeapon")
if fire_evt:
    pl.break_pin_links(p(fire_evt, "then", True))
    ed.remove_nodes([fire_evt])

# poll + branch -> spawn ONLY
poll = bo._find_node(ed, POLL)
if not poll:
    poll = ed.add_custom_event_node(POLL)
br = find_poll_branch(poll)
if not br:
    br = ed.add_branch_node()
    pl.break_pin_links(p(poll, "then", True))
    link(p(poll, "then", True), bel.find_execute_pin(br))

pl.break_pin_links(bel.find_then_pin(br))
link(bel.find_then_pin(br), spawn_exec)
wire_quest3_edge(br)

# disconnect hand branches from spawn / fire
for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
    brh = bo._find_node(ed, br_id)
    if brh:
        pl.break_pin_links(bel.find_then_pin(brh))
        pl.break_pin_links(bel.find_execute_pin(brh))

# grab -> timer
add = bo._find_node(ed, "K2Node_CallFunction_13")
grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
en = bo._find_node(ed, "K2Node_CallFunction_4")
hide = bo._find_node(ed, "K2Node_Message_1")
if grab and en and hide and add:
    pl.break_pin_links(p(grab, "then", True))
    link(p(grab, "then", True), p(en, "execute"))
    link(p(en, "then", True), p(hide, "execute"))
    link(p(hide, "then", True), p(add, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")

grab_get = bo._find_node(ed, "K2Node_VariableGet_0")
get_owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
link(p(grab_get, "GrabComponentSnap", True), p(get_owner, "self"))

timer = None
for n in ed.list_all_nodes() or []:
    if bo._node_title(n) == "Set Timer by Function Name":
        timer = n
        break
if not timer:
    timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
pl.set_pin_value(p(timer, "FunctionName"), POLL)
pl.set_pin_value(p(timer, "Time"), "0.05")
pl.set_pin_value(p(timer, "bLooping"), "true")
pl.break_pin_links(p(timer, "Object"))
link(p(get_owner, "ReturnValue", True), p(timer, "Object"))
pl.break_pin_links(p(add, "then", True))
link(p(add, "then", True), bel.find_execute_pin(timer))

# IA triggers fix
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
print("status", bp.status)
unreal.EditorAssetLibrary.save_asset("/Game/GunVR/BP_GunVR_UMP45")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

spawn_ins = pl.list_connected_pins(spawn_exec) or []
print("spawn<-", [bo._node_title(x.get_owning_node()) for x in spawn_ins])
print("poll->", [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(p(poll, "then", True)) or [])])

n = grab
for i in range(6):
    then = bel.find_then_pin(n)
    dest = [bo._node_title(c.get_owning_node()) for c in (pl.list_connected_pins(then) or [])]
    print(bo._node_title(n), "->", dest)
    if not pl.list_connected_pins(then):
        break
    n = pl.list_connected_pins(then)[0].get_owning_node()
