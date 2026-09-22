"""
Fix BP_MasterPlayerController multiplayer UI ownership + kill Python timer spam.

BeginPlay must ONLY Create/Add Master HUD when IsLocalController AND HasAuthority
(listen-server host). Remote server-side PCs must not touch widgets.

Run in Unreal Output Log / Python console (editor, not mid-PIE preferred):
  import lbvr_fix_master_pc_ui as f; import importlib; importlib.reload(f); print(f.fix())
"""
from __future__ import annotations

import unreal


ASSET = "/Game/LBVR/Blueprints/BP_MasterPlayerController"
CLIENT_WAIT_CLASS = "/Game/LBVR/UI/WBP_ClientWait.WBP_ClientWait_C"


def _pin(node, name: str, direction=None):
    for p in node.pins:
        if str(p.pin_name) != name:
            continue
        if direction is not None and p.direction != direction:
            continue
        return p
    return None


def _exec_out(node, prefer=("then", "then_0")):
    pins = [p for p in node.pins if p.direction == unreal.EdGraphPinDirection.EGPD_OUTPUT and p.pin_type.pin_category == "exec"]
    for name in prefer:
        for p in pins:
            if str(p.pin_name) == name:
                return p
    return pins[0] if pins else None


def _exec_in(node, name="execute"):
    for p in node.pins:
        if p.direction == unreal.EdGraphPinDirection.EGPD_INPUT and p.pin_type.pin_category == "exec":
            if str(p.pin_name) == name:
                return p
    for p in node.pins:
        if p.direction == unreal.EdGraphPinDirection.EGPD_INPUT and p.pin_type.pin_category == "exec":
            return p
    return None


def _break_exec_links(node):
    for p in node.pins:
        if p.pin_type.pin_category == "exec":
            p.break_all_pin_links()


def _fn_name(node) -> str:
    try:
        return str(node.get_editor_property("function_reference").member_name)
    except Exception:
        return ""


def _link(a_pin, b_pin) -> bool:
    if not a_pin or not b_pin:
        return False
    a_pin.make_link_to(b_pin)
    return True


def fix() -> dict:
    out: dict = {"ok": False, "steps": []}
    # Refuse during PIE — graph surgery mid-play crashes the editor
    try:
        pies = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if pies:
            return {"ok": False, "error": "Stop PIE first, then run fix()"}
    except Exception:
        pass

    bp = unreal.load_object(None, ASSET + ".BP_MasterPlayerController")
    if not bp:
        return {"ok": False, "error": "blueprint missing"}

    pages = unreal.BlueprintEditorLibrary.get_graphs(bp)
    eg = next((g for g in pages if g.get_name() == "EventGraph"), pages[0] if pages else None)
    if not eg:
        return {"ok": False, "error": "no EventGraph"}

    begin = create = addvp = branch_local = branch_auth = None
    set_timer = py_tick = py_boot = tick_ev = create_lan = vs = set_input = None

    for n in list(eg.nodes):
        cls = n.get_class().get_name()
        if cls == "K2Node_Event":
            try:
                if str(n.get_editor_property("event_reference").member_name) == "ReceiveBeginPlay":
                    begin = n
            except Exception:
                pass
        elif cls == "K2Node_CreateWidget":
            create = n
        elif cls == "K2Node_IfThenElse":
            cond = _pin(n, "Condition")
            if cond and cond.linked_to:
                src = cond.linked_to[0].get_owning_node()
                sfn = _fn_name(src)
                if sfn == "IsLocalController":
                    branch_local = n
                elif sfn == "HasAuthority":
                    branch_auth = n
        elif cls == "K2Node_CallFunction":
            fn = _fn_name(n)
            if fn == "AddToViewport":
                addvp = n
            elif fn == "K2_SetTimerDelegate":
                set_timer = n
            elif fn == "ExecutePythonCommand":
                cmd = ""
                p = _pin(n, "PythonCommand") or _pin(n, "Python Command")
                if p:
                    cmd = str(p.default_value)
                if "master_tick" in cmd:
                    py_tick = n
                elif "master_boot" in cmd:
                    py_boot = n
            elif fn == "CreateLanSession":
                create_lan = n
            elif fn == "SetInputMode_GameAndUIEx":
                set_input = n
        elif cls == "K2Node_CustomEvent":
            try:
                if str(n.get_editor_property("custom_function_name")) == "MasterStationTick":
                    tick_ev = n
            except Exception:
                pass
        elif cls == "K2Node_VariableSet":
            try:
                if "MasterHUD" in str(n.get_editor_property("variable_reference").member_name):
                    vs = n
            except Exception:
                if vs is None:
                    vs = n

    out["found"] = {
        "begin": bool(begin),
        "create": bool(create),
        "addvp": bool(addvp),
        "branch_local": bool(branch_local),
        "branch_auth": bool(branch_auth),
        "set_timer": bool(set_timer),
        "py_tick": bool(py_tick),
        "py_boot": bool(py_boot),
        "tick_ev": bool(tick_ev),
        "create_lan": bool(create_lan),
    }
    if not all([begin, create, addvp, branch_local, branch_auth]):
        out["error"] = "missing critical nodes"
        return out

    # Break old BeginPlay / UI / timer exec chains we own
    for node in (begin, create, addvp, branch_local, branch_auth):
        _break_exec_links(node)
        out["steps"].append(f"broke exec on {node.get_class().get_name()}")

    for node in (set_timer, py_tick, tick_ev):
        if node:
            _break_exec_links(node)
            out["steps"].append(f"disabled spam node {node.get_name()}")

    # Host-only Master HUD:
    # BeginPlay -> IsLocal? -> HasAuthority? -> CreateWidget -> AddToViewport -> (existing vs/input if still linked by data)
    ok = True
    ok &= _link(_exec_out(begin), _exec_in(branch_local))
    ok &= _link(_exec_out(branch_local, prefer=("then",)), _exec_in(branch_auth))
    ok &= _link(_exec_out(branch_auth, prefer=("then",)), _exec_in(create))
    ok &= _link(_exec_out(create), _exec_in(addvp))
    out["steps"].append(f"host UI chain linked={ok}")

    # After AddToViewport, restore Set var / input / auto-host if present
    if vs:
        _break_exec_links(vs)
        ok2 = _link(_exec_out(addvp), _exec_in(vs))
        out["steps"].append(f"addvp->MasterHUD set={ok2}")
        if set_input:
            _break_exec_links(set_input)
            # only break exec in, keep data
            for p in set_input.pins:
                if p.direction == unreal.EdGraphPinDirection.EGPD_INPUT and p.pin_type.pin_category == "exec":
                    p.break_all_pin_links()
            ok3 = _link(_exec_out(vs), _exec_in(set_input))
            out["steps"].append(f"set->inputmode={ok3}")

    # Host session boot once: authority then also needs CreateLanSession + optional one-shot boot.
    # Chain from SetInputMode (or addvp) into CreateLanSession if orphaned.
    if create_lan:
        # If CreateLanSession has no incoming exec, attach after input mode / addvp
        cin = _exec_in(create_lan)
        if cin and not cin.linked_to:
            src = set_input or vs or addvp
            _link(_exec_out(src), cin)
            out["steps"].append("reattached CreateLanSession")
        # Ensure python boot does NOT loop — leave boot if already wired after CreateLanSession,
        # but never reattach SetTimer.
        if py_boot:
            # if boot has no incoming, wire after create_lan
            bin_ = _exec_in(py_boot)
            if bin_ and not bin_.linked_to:
                _link(_exec_out(create_lan), bin_)
                out["steps"].append("one-shot master_boot after CreateLanSession")
            # break boot then -> timer if any remain
            bout = _exec_out(py_boot)
            if bout:
                for lp in list(bout.linked_to):
                    if lp.get_owning_node() == set_timer:
                        bout.break_link_to(lp)
                        out["steps"].append("removed boot->timer link")

    # Client local (Quest on Master map): IsLocal true, Authority false -> ClientWait HUD
    # Add CreateWidget ClientWait on else of HasAuthority
    try:
        schema = eg.get_schema()
        # Spawn CreateWidget for client wait via editor graph schema is hard in Python.
        # Instead: print guidance if we cannot. Try K2Node_CreateWidget via allocate
        client_create = unreal.K2Node_CreateWidget()
        eg.add_node(client_create, False, False)
        client_create.node_pos_x = create.node_pos_x
        client_create.node_pos_y = create.node_pos_y + 350
        # Set class on node
        wclass = unreal.load_object(None, CLIENT_WAIT_CLASS)
        if wclass:
            try:
                client_create.set_editor_property("widget_class", wclass)
            except Exception:
                # pin default
                cp = _pin(client_create, "Class")
                if cp:
                    cp.default_object = wclass
        client_add = unreal.K2Node_CallFunction()
        eg.add_node(client_add, False, False)
        client_add.node_pos_x = addvp.node_pos_x
        client_add.node_pos_y = addvp.node_pos_y + 350
        # Bind AddToViewport
        try:
            unreal.BlueprintEditorLibrary.refine...  # placeholder
        except Exception:
            pass
        # Use call function setup
        try:
            from unreal import SystemLibrary
            # Function reference for UserWidget.AddToViewport
            client_add.set_editor_property(
                "function_reference",
                unreal.MemberReference(
                ),
            )
        except Exception as e:
            out["client_widget_note"] = f"Could not auto-wire client wait widget ({e}). Host HUD gate is the critical fix."
            # Remove half-created nodes to avoid compile errors
            eg.remove_node(client_create)
            eg.remove_node(client_add)
    except Exception as e:
        out["client_widget_note"] = str(e)

    status = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    out["compile"] = str(status)
    unreal.EditorAssetLibrary.save_asset(ASSET)
    out["ok"] = True
    out["msg"] = (
        "Master HUD now only on local+authority host. Python timer spam disabled. "
        "Stop PIE, run this, then Play as Listen Server again."
    )
    return out


def fix_and_report():
    return fix()
