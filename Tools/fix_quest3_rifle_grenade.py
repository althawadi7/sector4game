"""Apply Quest 3 poll fix to rifle + grenade only (pistol already fixed)."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
PATHS = [
    "/Game/XRFramework/Blueprints/BP_Rifle",
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
]


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    if a and b:
        return pl.try_create_connection(a, b)
    return False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


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


def wire_quest3_edge(ed, pl, br, y=500):
    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
    if not pc:
        pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
        pl.set_pin_value(p(pc, "PlayerIndex"), "0")

    def side(axis, y0):
        ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
        bo._set_node_pos(ax, 1100, y0)
        pl.set_pin_value(p(ax, "Key"), axis)
        ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
        pl.set_pin_value(p(ge, "B"), "0.55")
        link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
        link(pl, p(ax, "ReturnValue", True), p(ge, "A"))
        td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
        pl.set_pin_value(p(td, "Key"), axis)
        lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
        pl.set_pin_value(p(lt, "B"), "0.12")
        link(pl, p(pc, "ReturnValue", True), p(td, "self"))
        link(pl, p(td, "ReturnValue", True), p(lt, "A"))
        and_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
        link(pl, p(ge, "ReturnValue", True), p(and_n, "A"))
        link(pl, p(lt, "ReturnValue", True), p(and_n, "B"))
        return p(and_n, "ReturnValue", True)

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    link(pl, side(AXIS_L, y), p(or_n, "A"))
    link(pl, side(AXIS_R, y + 160), p(or_n, "B"))
    cond = p(br, "Condition")
    unlink(pl, cond)
    return link(pl, p(or_n, "ReturnValue", True), cond)


for path in PATHS:
    name = path.split("/")[-1]
    bp = unreal.load_asset(path + "." + name)
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if add:
        pl.set_pin_value(p(add, "Options"), GOOD)
    poll = bo._find_node(ed, POLL)
    br = find_poll_branch(ed, pl, poll)
    if not poll or not br:
        unreal.log_error(name + " missing poll/branch")
        continue
    ok = wire_quest3_edge(ed, pl, br, 500 if name == "BP_Rifle" else 900)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(name + " quest3=" + str(ok) + " " + str(bp.status))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("rifle+grenade quest3 fix DONE")
