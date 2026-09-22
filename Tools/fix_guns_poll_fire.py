"""Surgical fix: restore grab chain + Set Timer (correct API) + PollShoot fire.

Root cause: K2_SetTimerByFunctionName returns null; script unlinked AddMappingContext.then
and left it empty, so PollShoot never ran.

Correct timer node: /Script/Engine.KismetSystemLibrary.K2_SetTimer
  -> title "Set Timer by Function Name"

  py via bridge exec
"""
from __future__ import annotations

import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollShoot"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
AXIS_KEYS = [
    "OculusTouch_Left_Trigger_Axis",
    "OculusTouch_Right_Trigger_Axis",
    "MotionController_Left_Trigger_Axis",
    "MotionController_Right_Trigger_Axis",
]
CLICK_KEYS = [
    "OculusTouch_Left_Trigger",
    "OculusTouch_Right_Trigger",
    "MotionController_Left_Trigger",
    "MotionController_Right_Trigger",
    "OculusTouch_Left_Trigger_Click",
    "OculusTouch_Right_Trigger_Click",
]
WEAPONS = [
    "/Game/XRFramework/Blueprints/BP_Rifle",
    "/Game/XRFramework/Blueprints/BP_Pistol",
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
]


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return bool(a and b and pl.try_create_connection(a, b))


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


def title(n):
    try:
        return bo._node_title(n)
    except Exception:
        return n.get_name()


def self_pin(ed):
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_Self":
            return p(n, "self", True)
    return None


def wire_self(ed, pl, node):
    obj = p(node, "Object") or p(node, "self")
    sp = self_pin(ed)
    if obj and sp:
        unlink(pl, obj)
        return link(pl, sp, obj)
    return False


def find_add(ed):
    for n in ed.list_all_nodes() or []:
        t = title(n).replace(" ", "")
        if t == "AddMappingContext":
            return n
    return None


def find_drop(ed):
    for n in ed.list_all_nodes() or []:
        if "OnDropped" in n.get_name() or "On Dropped" in title(n):
            return n
    return None


def find_poll(ed):
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == POLL:
            return n
    return None


def find_spawn_branches(ed, pl):
    bel = bo._bel()
    branches = []
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() != "K2Node_IfThenElse":
            continue
        then = bel.find_then_pin(n)
        for pin in pl.list_connected_pins(then) or []:
            if "SpawnActor" in pin.get_owning_node().get_name():
                branches.append(n)
                break
    return branches


def find_or_make_timer(ed, pl, function_name: str):
    """Use correct API: K2_SetTimer -> 'Set Timer by Function Name'."""
    for n in ed.list_all_nodes() or []:
        if title(n) == "Set Timer by Function Name":
            try:
                if pl.get_pin_value(p(n, "FunctionName")) == function_name:
                    return n
            except Exception:
                pass
    n = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
    if not n:
        raise RuntimeError("Failed to create Set Timer by Function Name")
    bo._set_node_pos(n, 2600, 80)
    return n


def find_or_make_clear(ed, pl, function_name: str):
    for n in ed.list_all_nodes() or []:
        if title(n) == "Clear Timer by Function Name":
            try:
                if pl.get_pin_value(p(n, "FunctionName")) == function_name:
                    return n
            except Exception:
                pass
    # Clear uses same family; try both paths
    n = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_ClearTimer")
    if not n:
        n = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.K2_ClearTimerByFunctionName"
        )
    if not n:
        raise RuntimeError("Failed to create Clear Timer")
    bo._set_node_pos(n, 2600, 280)
    return n


def insert_after_then(ed, pl, after_node, insert_node):
    """after.then -> insert; insert.then -> previous targets."""
    bel = bo._bel()
    then = bel.find_then_pin(after_node)
    old = list(pl.list_connected_pins(then) or [])
    unlink(pl, then)
    link(pl, then, bel.find_execute_pin(insert_node))
    ithen = bel.find_then_pin(insert_node)
    unlink(pl, ithen)
    for pin in old:
        link(pl, ithen, pin)
    return len(old)


def ensure_poll(ed):
    poll = find_poll(ed)
    if poll:
        return poll
    poll = ed.add_custom_event_node(POLL)
    bo._set_node_pos(poll, -1800, 1400)
    return poll


def rebuild_poll_body(ed, pl, poll, branches):
    """OR of JustPressed clicks OR max(axis)>0.7 -> print -> fire all spawn branches."""
    bel = bo._bel()

    # Break existing then from poll (we'll rebuild)
    unlink(pl, bel.find_then_pin(poll))

    pc = ed.add_call_function_node("/Script/Engine.GameplayStatics.GetPlayerController")
    bo._set_node_pos(pc, -1600, 1400)
    pl.set_pin_value(p(pc, "PlayerIndex"), "0")

    # --- Click just-pressed OR ---
    click_bools = []
    y = 1400
    for key in CLICK_KEYS:
        jp = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
        bo._set_node_pos(jp, -1380, y)
        pl.set_pin_value(p(jp, "Key"), key)
        link(pl, p(pc, "ReturnValue", True), p(jp, "self"))
        click_bools.append(jp)
        y += 70

    cur = click_bools[0]
    x = -1100
    for nxt in click_bools[1:]:
        ob = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
        bo._set_node_pos(ob, x, 1400)
        link(pl, p(cur, "ReturnValue", True), p(ob, "A"))
        link(pl, p(nxt, "ReturnValue", True), p(ob, "B"))
        cur = ob
        x += 140
    click_or = cur

    # --- Axis max > 0.7 ---
    axes = []
    y = 1900
    for key in AXIS_KEYS:
        ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
        bo._set_node_pos(ax, -1380, y)
        pl.set_pin_value(p(ax, "Key"), key)
        link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
        axes.append(ax)
        y += 70
    cur_ax = axes[0]
    x = -1100
    for nxt in axes[1:]:
        mx = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.FMax")
        bo._set_node_pos(mx, x, 1900)
        link(pl, p(cur_ax, "ReturnValue", True), p(mx, "A"))
        link(pl, p(nxt, "ReturnValue", True), p(mx, "B"))
        cur_ax = mx
        x += 140
    ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    bo._set_node_pos(ge, x, 1900)
    pl.set_pin_value(p(ge, "B"), "0.70")
    link(pl, p(cur_ax, "ReturnValue", True), p(ge, "A"))

    # Rising-ish: also require TimeDown < 0.12 on ANY click key (for axis-only, use GetInputKeyTimeDown on axis keys)
    # Combine: fire if click_or OR (axis>0.7 AND any axis TimeDown < 0.15)
    td_oks = []
    y = 2300
    for key in AXIS_KEYS + CLICK_KEYS[:4]:
        td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
        bo._set_node_pos(td, -1380, y)
        pl.set_pin_value(p(td, "Key"), key)
        link(pl, p(pc, "ReturnValue", True), p(td, "self"))
        lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
        bo._set_node_pos(lt, -1100, y)
        pl.set_pin_value(p(lt, "B"), "0.15")
        link(pl, p(td, "ReturnValue", True), p(lt, "A"))
        # also require that key is actually down: analog>0.5 OR just pressed already covered
        td_oks.append(lt)
        y += 60
        if len(td_oks) >= 4:
            break

    cur_td = td_oks[0]
    x = -900
    for nxt in td_oks[1:]:
        ob = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
        bo._set_node_pos(ob, x, 2300)
        link(pl, p(cur_td, "ReturnValue", True), p(ob, "A"))
        link(pl, p(nxt, "ReturnValue", True), p(ob, "B"))
        cur_td = ob
        x += 140

    axis_edge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    bo._set_node_pos(axis_edge, -500, 2000)
    link(pl, p(ge, "ReturnValue", True), p(axis_edge, "A"))
    link(pl, p(cur_td, "ReturnValue", True), p(axis_edge, "B"))

    fire = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    bo._set_node_pos(fire, -320, 1600)
    link(pl, p(click_or, "ReturnValue", True), p(fire, "A"))
    link(pl, p(axis_edge, "ReturnValue", True), p(fire, "B"))

    br = ed.add_branch_node()
    bo._set_node_pos(br, -120, 1600)
    link(pl, bel.find_then_pin(poll), bel.find_execute_pin(br))
    unlink(pl, p(br, "Condition"))
    link(pl, p(fire, "ReturnValue", True), p(br, "Condition"))

    pr = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
    bo._set_node_pos(pr, 120, 1600)
    pl.set_pin_value(p(pr, "InString"), "VRSHOOT POLL FIRE")
    pl.set_pin_value(p(pr, "bPrintToScreen"), "true")
    pl.set_pin_value(p(pr, "bPrintToLog"), "true")
    pl.set_pin_value(p(pr, "Duration"), "1.5")
    link(pl, bel.find_then_pin(br), bel.find_execute_pin(pr))

    # Force spawn branches true and fire them from print
    for b in branches:
        cp = p(b, "Condition")
        if cp:
            unlink(pl, cp)
            pl.set_pin_value(cp, "true")

    if not branches:
        return {"fire_targets": 0}

    # Sequence macro to fan out, else first branch only
    macro = None
    try:
        macro = ed.add_macro_node("StandardMacros:Sequence")
    except Exception:
        pass
    if not macro:
        try:
            macro = ed.create_node_from_name("Sequence", unreal.Vector2D(360, 1600))
        except Exception:
            pass

    if macro:
        bo._set_node_pos(macro, 360, 1600)
        link(pl, bel.find_then_pin(pr), bel.find_execute_pin(macro))
        then_pins = [
            pp
            for pp in bel.list_all_pins(macro) or []
            if str(pp.get_direction()) == "EGPD_Output"
            and "then" in str(pp.get_pin_name()).lower()
        ]
        # fallback: any output exec
        if not then_pins:
            then_pins = [
                pp
                for pp in bel.list_all_pins(macro) or []
                if str(pp.get_direction()) == "EGPD_Output" and pp.is_exec_pin()
            ]
        for i, b in enumerate(branches):
            if i < len(then_pins):
                link(pl, then_pins[i], bel.find_execute_pin(b))
        return {"fire_targets": min(len(branches), len(then_pins)), "seq": True}

    # No sequence: fire first spawn branch (still shoots)
    link(pl, bel.find_then_pin(pr), bel.find_execute_pin(branches[0]))
    return {"fire_targets": 1, "seq": False}


def fix_weapon(path: str):
    name = path.split("/")[-1]
    bp = unreal.load_asset(f"{path}.{name}")
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()
    report = {"weapon": name}

    add = find_add(ed)
    if not add:
        report["error"] = "no AddMappingContext"
        return report

    if p(add, "Options"):
        pl.set_pin_value(p(add, "Options"), GOOD)
    if p(add, "Priority"):
        pl.set_pin_value(p(add, "Priority"), "10")

    # Timer start after AddMappingContext (restores broken empty then)
    timer = find_or_make_timer(ed, pl, POLL)
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    if p(timer, "bLooping"):
        pl.set_pin_value(p(timer, "bLooping"), "true")
    wire_self(ed, pl, timer)
    restored = insert_after_then(ed, pl, add, timer)
    report["timer_after_imc"] = True
    report["restored_links"] = restored

    # Clear on drop
    drop = find_drop(ed)
    if drop:
        clear = find_or_make_clear(ed, pl, POLL)
        pl.set_pin_value(p(clear, "FunctionName"), POLL)
        wire_self(ed, pl, clear)
        insert_after_then(ed, pl, drop, clear)
        report["clear_on_drop"] = True

    poll = ensure_poll(ed)
    branches = find_spawn_branches(ed, pl)
    report["branches"] = len(branches)
    report["poll"] = rebuild_poll_body(ed, pl, poll, branches)

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    report["status"] = str(bp.status)
    unreal.log(f"fix_guns_timer: {report}")
    return report


def main():
    results = []
    for path in WEAPONS:
        try:
            results.append(fix_weapon(path))
        except Exception as exc:
            import traceback

            unreal.log_error(f"{path}: {exc}\n{traceback.format_exc()}")
            results.append({"weapon": path, "error": str(exc)})
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("DONE — FULLY stop VR Preview, start again, grab, squeeze trigger")
    global RESULT
    RESULT = results


if __name__ == "__main__":
    main()
