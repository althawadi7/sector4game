"""
Quest 3 shoot blocker fix (SAFE — pistol only, minimal nodes).
Blockers found:
  - IA_Shoot triggers empty
  - Poll branch uses broken nested OR (Trigger_Click unreliable on Quest 3)
Fix: axis edge detection -> poll branch condition. FX/spawn chain untouched.

Step 1 — run this (pistol):
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_quest3_blockers.py"

Step 2 — after pistol works, uncomment rifle/grenade at bottom and run again.
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    if a and b:
        return pl.try_create_connection(a, b)
    return False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


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
    """Quest 3: axis pressed + recent edge -> branch condition (~7 nodes)."""
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

    # right hand — same pattern, offset Y
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


def fix_weapon(path):
    name = path.split("/")[-1]
    bp = unreal.load_asset(path + "." + name)
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()

    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if add:
        pl.set_pin_value(p(add, "Options"), GOOD)

    poll = bo._find_node(ed, POLL)
    if not poll:
        unreal.log_error(name + ": no PollReload")
        return False
    br = find_poll_branch(ed, pl, poll)
    if not br:
        unreal.log_error(name + ": no poll branch")
        return False

    ok = wire_quest3_edge(ed, pl, br)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(name + " quest3 cond=" + str(ok) + " status=" + str(bp.status))
    return ok


fix_ia_triggers()
fix_weapon("/Game/XRFramework/Blueprints/BP_Pistol")

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("fix_quest3_blockers DONE (pistol)")
