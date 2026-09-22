"""
Fix BP_GunVR_UMP45 shoot — timer + Quest3 trigger poll + spawn wire.
Run: py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_ump45_shoot_now.py"
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
    if a and b:
        return pl.try_create_connection(a, b)
    return False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


def self_pin(ed):
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_Self":
            return p(n, "self", True)
    return None


def wire_timer_object(ed, pl, timer_node):
    obj = p(timer_node, "Object")
    sp = self_pin(ed)
    if not obj or not sp:
        return False
    unlink(pl, obj)
    return link(pl, sp, obj)


def fix_ia_triggers():
    for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
        path = "/Game/XRFramework/Input/Actions/" + name
        ia = unreal.load_asset(path + "." + name)
        if not ia:
            continue
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t is not None]
        if len(triggers) < 1:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)


def find_poll_branch(ed, pl, poll):
    bel = bo._bel()
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) != "Branch":
            continue
        ex = bel.find_execute_pin(n)
        for pin in pl.list_connected_pins(ex) or []:
            if pin.get_owning_node() == poll:
                return n
    return None


def wire_quest3_edge(ed, pl, br):
    bel = bo._bel()
    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
    if not pc:
        pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
        bo._set_node_pos(pc, 1000, 500)
        pl.set_pin_value(p(pc, "PlayerIndex"), "0")

    ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    bo._set_node_pos(ax, 1100, 480)
    pl.set_pin_value(p(ax, "Key"), AXIS_L)
    ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    bo._set_node_pos(ge, 1250, 480)
    pl.set_pin_value(p(ge, "B"), "0.55")
    link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
    link(pl, p(ax, "ReturnValue", True), p(ge, "A"))

    td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    bo._set_node_pos(td, 1100, 560)
    pl.set_pin_value(p(td, "Key"), AXIS_L)
    lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    bo._set_node_pos(lt, 1250, 560)
    pl.set_pin_value(p(lt, "B"), "0.12")
    link(pl, p(pc, "ReturnValue", True), p(td, "self"))
    link(pl, p(td, "ReturnValue", True), p(lt, "A"))

    and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    bo._set_node_pos(and_l, 1400, 520)
    link(pl, p(ge, "ReturnValue", True), p(and_l, "A"))
    link(pl, p(lt, "ReturnValue", True), p(and_l, "B"))

    ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    bo._set_node_pos(ax2, 1100, 680)
    pl.set_pin_value(p(ax2, "Key"), AXIS_R)
    ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    bo._set_node_pos(ge2, 1250, 680)
    pl.set_pin_value(p(ge2, "B"), "0.55")
    link(pl, p(pc, "ReturnValue", True), p(ax2, "self"))
    link(pl, p(ax2, "ReturnValue", True), p(ge2, "A"))

    td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    bo._set_node_pos(td2, 1100, 760)
    pl.set_pin_value(p(td2, "Key"), AXIS_R)
    lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    bo._set_node_pos(lt2, 1250, 760)
    pl.set_pin_value(p(lt2, "B"), "0.12")
    link(pl, p(pc, "ReturnValue", True), p(td2, "self"))
    link(pl, p(td2, "ReturnValue", True), p(lt2, "A"))

    and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    bo._set_node_pos(and_r, 1400, 720)
    link(pl, p(ge2, "ReturnValue", True), p(and_r, "A"))
    link(pl, p(lt2, "ReturnValue", True), p(and_r, "B"))

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    bo._set_node_pos(or_n, 1550, 620)
    link(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
    link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))

    cond = p(br, "Condition")
    unlink(pl, cond)
    return link(pl, p(or_n, "ReturnValue", True), cond)


def fix_grab_timer(ed, pl):
    bel = bo._bel()
    grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
    en = bo._find_node(ed, "K2Node_CallFunction_4")
    hide = bo._find_node(ed, "K2Node_Message_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not all([grab, en, hide, add]):
        unreal.log_error("grab chain nodes missing")
        return False

    unlink(pl, p(grab, "then", True))
    link(pl, p(grab, "then", True), p(en, "execute"))
    link(pl, p(en, "then", True), p(hide, "execute"))
    link(pl, p(hide, "then", True), p(add, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")

    timer = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Set Timer by Function Name":
            fn = bo._pinlib().get_pin_value(p(n, "FunctionName"))
            if fn == POLL:
                timer = n
                break
    if not timer:
        timer = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.K2_SetTimerByFunctionName"
        )
        bo._set_node_pos(timer, 2000, 200)

    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    wire_timer_object(ed, pl, timer)

    unlink(pl, p(add, "then", True))
    ok = link(pl, p(add, "then", True), bel.find_execute_pin(timer))

  # clear timer on drop
    drop = bo._find_node(ed, "K2Node_ComponentBoundEvent_1")
    show = bo._find_node(ed, "K2Node_Message_0")
    dis = bo._find_node(ed, "K2Node_CallFunction_12")
    rem = bo._find_node(ed, "K2Node_CallFunction_14")
    if drop and show:
        clear = None
        for n in ed.list_all_nodes() or []:
            if bo._node_title(n) == "Clear Timer by Function Name":
                fn = bo._pinlib().get_pin_value(p(n, "FunctionName"))
                if fn == POLL:
                    clear = n
                    break
        if not clear:
            clear = ed.add_call_function_node(
                "/Script/Engine.KismetSystemLibrary.K2_ClearTimerByFunctionName"
            )
            bo._set_node_pos(clear, 2000, 350)
        pl.set_pin_value(p(clear, "FunctionName"), POLL)
        wire_timer_object(ed, pl, clear)
        unlink(pl, p(drop, "then", True))
        link(pl, p(drop, "then", True), p(show, "execute"))
        if dis and rem:
            link(pl, p(show, "then", True), p(dis, "execute"))
            link(pl, p(dis, "then", True), p(rem, "execute"))
            link(pl, p(rem, "then", True), bel.find_execute_pin(clear))
        else:
            link(pl, p(show, "then", True), bel.find_execute_pin(clear))

    return ok


def fix_imc(ed, pl):
    sel = bo._find_node(ed, "K2Node_Select_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not sel or not add:
        return
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    unlink(pl, p(add, "MappingContext"))
    link(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))


def fix_poll_spawn(ed, pl):
    bel = bo._bel()
    poll = bo._find_node(ed, POLL)
    if not poll:
        poll = ed.add_custom_event_node(POLL)
        bo._set_node_pos(poll, 900, 400)

    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if not spawn:
        unreal.log_error("no spawn node")
        return False
    spawn_exec = bel.find_execute_pin(spawn)
    pl.set_pin_value(p(spawn, "Class"), PROJECTILE)

    br = find_poll_branch(ed, pl, poll)
    if not br:
        br = ed.add_branch_node()
        bo._set_node_pos(br, 1450, 400)
        unlink(pl, p(poll, "then", True))
        link(pl, p(poll, "then", True), bel.find_execute_pin(br))

    unlink(pl, bel.find_then_pin(br))
    unlink(pl, spawn_exec)
    shoot_ok = link(pl, bel.find_then_pin(br), spawn_exec)
    cond_ok = wire_quest3_edge(ed, pl, br)
    return shoot_ok and cond_ok


def main():
    fix_ia_triggers()
    bp = unreal.load_asset(GUN + ".BP_GunVR_UMP45")
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()

    fix_imc(ed, pl)
    timer_ok = fix_grab_timer(ed, pl)
    poll_ok = fix_poll_spawn(ed, pl)

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(GUN)
    unreal.log(
        "UMP45 shoot fix timer=" + str(timer_ok) + " poll=" + str(poll_ok) + " status=" + str(bp.status)
    )
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


main()
