"""
Blueprint graph helpers for CursorUnrealBridge (UE 5.8+).

Local Aura-like Blueprint power: inspect, create, add nodes, wire pins,
variables, compile, save — no Aura login required.
"""

from __future__ import annotations

from typing import Any

import unreal


def _bel():
    return unreal.BlueprintEditorLibrary


def _pinlib():
    return unreal.BlueprintGraphPinLibrary


def _load_bp(asset_path: str):
    bp = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not bp:
        raise RuntimeError(f"Blueprint not found: {asset_path}")
    if not isinstance(bp, unreal.Blueprint):
        raise RuntimeError(f"Asset is not a Blueprint: {asset_path} ({type(bp).__name__})")
    return bp


def _status_str(bp) -> str:
    try:
        return str(bp.status)
    except Exception:
        return "unknown"


def _node_title(node) -> str:
    try:
        return str(_bel().get_node_title(node) or "")
    except Exception:
        try:
            return str(node.get_name())
        except Exception:
            return "?"


def _pin_name(pin) -> str:
    try:
        return str(_pinlib().get_pin_name(pin) or "")
    except Exception:
        return "?"


def _list_pins(node) -> list[dict[str, Any]]:
    bel = _bel()
    pinlib = _pinlib()
    out: list[dict[str, Any]] = []
    try:
        pins = list(bel.list_all_pins(node) or [])
    except Exception:
        pins = []
    for p in pins:
        try:
            direction = str(pinlib.get_pin_direction(p))
        except Exception:
            direction = "?"
        try:
            ptype = str(pinlib.get_pin_type_display_string(p))
        except Exception:
            ptype = "?"
        out.append({"name": _pin_name(p), "direction": direction, "type": ptype})
    return out


def _event_graph(bp):
    bel = _bel()
    graph = None
    for name in ("find_event_graph", "get_event_graph"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                graph = fn(bp)
                if graph:
                    return graph
            except Exception:
                pass
    # Fallback: first graph
    names = []
    for name in ("list_graph_names", "get_graph_names"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                names = list(fn(bp) or [])
                break
            except Exception:
                pass
    if names:
        for finder in ("find_graph", "get_graph"):
            fn = getattr(bel, finder, None)
            if callable(fn):
                try:
                    graph = fn(bp, names[0])
                    if graph:
                        return graph
                except Exception:
                    pass
    raise RuntimeError("Could not resolve Blueprint event graph")


def _editor_for(bp, graph_name: str = ""):
    bel = _bel()
    if graph_name:
        graph = None
        for finder in ("find_graph", "get_graph"):
            fn = getattr(bel, finder, None)
            if callable(fn):
                try:
                    graph = fn(bp, graph_name)
                    if graph:
                        break
                except Exception:
                    pass
        if not graph:
            raise RuntimeError(f"Graph not found: {graph_name}")
    else:
        graph = _event_graph(bp)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    return editor, graph


def _find_node(editor, name_or_title: str):
    needle = (name_or_title or "").strip()
    if not needle:
        return None
    nodes = list(editor.list_all_nodes() or [])
    # Exact title
    for n in nodes:
        if _node_title(n) == needle:
            return n
    low = needle.lower()
    for n in nodes:
        if _node_title(n).lower() == low:
            return n
    for n in nodes:
        if low in _node_title(n).lower():
            return n
    for n in nodes:
        try:
            if n.get_name() == needle or needle in n.get_name():
                return n
        except Exception:
            pass
    # Event member name e.g. ReceiveBeginPlay
    try:
        ev = editor.find_event_node(needle)
        if ev:
            return ev
    except Exception:
        pass
    # Friendly aliases
    aliases = {
        "beginplay": "ReceiveBeginPlay",
        "event beginplay": "ReceiveBeginPlay",
        "tick": "ReceiveTick",
        "event tick": "ReceiveTick",
        "actorbeginoverlap": "ReceiveActorBeginOverlap",
    }
    alt = aliases.get(low)
    if alt:
        try:
            ev = editor.find_event_node(alt)
            if ev:
                return ev
        except Exception:
            pass
    return None


def _find_pin(node, pin_name: str, prefer_direction: str = ""):
    bel = _bel()
    pinlib = _pinlib()
    raw = (pin_name or "").strip()
    key = raw.replace(" ", "").lower()

    helper_map = {
        "then": "find_then_pin",
        "execute": "find_execute_pin",
        "exec": "find_execute_pin",
        "self": "find_self_pin",
        "condition": "find_condition_pin",
        "else": "find_else_pin",
        "returnvalue": "find_result_pin",
        "return_value": "find_result_pin",
    }
    helper_name = helper_map.get(key)
    if helper_name:
        helper = getattr(bel, helper_name, None)
        if callable(helper):
            try:
                pin = helper(node)
                if pin:
                    return pin
            except Exception:
                pass

    for finder in ("find_input_pin", "find_output_pin"):
        fn = getattr(bel, finder, None)
        if callable(fn):
            try:
                pin = fn(node, raw)
                if pin:
                    return pin
            except Exception:
                pass

    try:
        pins = list(bel.list_all_pins(node) or [])
    except Exception:
        pins = []

    for p in pins:
        if _pin_name(p) == raw:
            if prefer_direction:
                try:
                    d = str(pinlib.get_pin_direction(p)).lower()
                    if prefer_direction.lower() not in d:
                        continue
                except Exception:
                    pass
            return p
    for p in pins:
        if _pin_name(p).lower() == key:
            return p
    return None


def _set_node_pos(node, x: int, y: int) -> None:
    bel = _bel()
    for args in (
        (node, unreal.IntPoint(int(x), int(y))),
        (node, int(x), int(y)),
    ):
        for name in ("set_node_pos", "set_node_position"):
            fn = getattr(bel, name, None)
            if callable(fn):
                try:
                    fn(*args)
                    return
                except Exception:
                    continue


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inspect_blueprint(asset_path: str, graph_name: str = "") -> dict[str, Any]:
    bp = _load_bp(asset_path)
    bel = _bel()

    graphs = []
    for name in ("list_graph_names", "get_graph_names"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                graphs = [str(x) for x in (fn(bp) or [])]
                break
            except Exception:
                pass

    variables = []
    for name in ("list_member_variable_names", "get_member_variable_names"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                for vname in list(fn(bp) or []):
                    variables.append({"name": str(vname)})
                break
            except Exception as exc:
                variables = [{"error": str(exc)}]

    functions = []
    for name in ("list_functions", "get_functions"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                functions = [str(x) for x in (fn(bp) or [])]
                break
            except Exception:
                pass

    events = []
    for name in ("list_events", "get_events"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                events = [str(x) for x in (fn(bp) or [])]
                break
            except Exception:
                pass

    editor, graph = _editor_for(bp, graph_name)
    nodes_out = []
    for n in list(editor.list_all_nodes() or []):
        pos = None
        for getter in ("get_node_pos", "get_node_position"):
            fn = getattr(bel, getter, None)
            if callable(fn):
                try:
                    p = fn(n)
                    pos = {"x": int(getattr(p, "x", 0)), "y": int(getattr(p, "y", 0))}
                    break
                except Exception:
                    pass
        nodes_out.append(
            {
                "title": _node_title(n),
                "name": n.get_name(),
                "class": n.get_class().get_name(),
                "pos": pos,
                "pins": _list_pins(n),
            }
        )

    parent = None
    for name in ("get_blueprint_parent_class", "get_parent_class"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                parent = str(fn(bp))
                break
            except Exception:
                pass

    return {
        "success": True,
        "path": asset_path,
        "parent": parent,
        "status": _status_str(bp),
        "graphs": graphs,
        "active_graph": str(graph.get_name()) if graph else graph_name,
        "variables": variables,
        "functions": functions,
        "events": events,
        "nodes": nodes_out,
        "node_count": len(nodes_out),
    }


def create_blueprint(
    asset_path: str,
    parent_class: str = "Actor",
    overwrite: bool = False,
) -> dict[str, Any]:
    bel = _bel()
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        if not overwrite:
            return {"success": True, "already_exists": True, "path": asset_path}
        unreal.EditorAssetLibrary.delete_asset(asset_path)

    raw = (parent_class or "Actor").strip()
    parent = None
    used_default = False
    if raw.startswith("/"):
        parent = unreal.EditorAssetLibrary.load_blueprint_class(raw) or unreal.load_class(None, raw)
    if parent is None:
        obj = getattr(unreal, raw, None)
        if obj is not None:
            parent = obj.static_class() if hasattr(obj, "static_class") else obj
    if parent is None:
        parent = unreal.Actor.static_class()
        used_default = True

    if "/" in asset_path:
        unreal.EditorAssetLibrary.make_directory(asset_path.rsplit("/", 1)[0])

    bp = None
    for name in ("create_blueprint_asset_with_parent", "create_blueprint_with_parent"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                bp = fn(asset_path, parent)
                if bp:
                    break
            except Exception:
                continue
    if not bp:
        return {"success": False, "error": f"Failed to create Blueprint at {asset_path}"}

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(asset_path)
    return {
        "success": True,
        "path": asset_path,
        "parent": raw,
        "used_default_parent": used_default,
        "status": _status_str(bp),
    }


def add_blueprint_nodes(
    asset_path: str,
    nodes: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    nodes item example:
      {
        "id": "print1",
        "type": "call" | "branch" | "custom_event" | "palette",
        "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
        "palette": "Development|PrintString",
        "event_name": "MyEvent",
        "x": 400, "y": 0,
        "pin_defaults": {"InString": "hi"}
      }
    """
    bp = _load_bp(asset_path)
    bel = _bel()
    pinlib = _pinlib()
    editor, _graph = _editor_for(bp, graph_name)
    created: list[dict[str, Any]] = []

    for spec in nodes or []:
        ntype = (spec.get("type") or "call").lower()
        x = int(spec.get("x", 0))
        y = int(spec.get("y", 0))
        node = None
        how = ""

        try:
            if ntype in ("branch", "if"):
                node = editor.add_branch_node()
                how = "branch"
            elif ntype in ("custom_event", "event"):
                ename = spec.get("event_name") or spec.get("name") or "CustomEvent"
                node = editor.add_custom_event_node(ename)
                how = f"custom_event:{ename}"
            elif ntype == "palette" or (not spec.get("function_path") and spec.get("palette")):
                palette = spec.get("palette") or spec.get("name") or ""
                node = editor.create_node_from_name(
                    palette, unreal.Vector2D(float(x), float(y)), []
                )
                how = f"palette:{palette}"
            else:
                fpath = (
                    spec.get("function_path")
                    or spec.get("path")
                    or spec.get("function")
                    or "/Script/Engine.KismetSystemLibrary.PrintString"
                )
                node = editor.add_call_function_node(fpath)
                how = f"call:{fpath}"
        except Exception as exc:
            created.append({"id": spec.get("id"), "success": False, "error": str(exc), "how": how})
            continue

        if not node:
            created.append({"id": spec.get("id"), "success": False, "error": f"Failed to create ({how})"})
            continue

        _set_node_pos(node, x, y)

        set_pins = []
        defaults = spec.get("pin_defaults") or spec.get("defaults") or {}
        for pname, pval in defaults.items():
            pin = _find_pin(node, pname)
            if pin is None:
                set_pins.append({"pin": pname, "ok": False, "error": "pin not found"})
                continue
            try:
                pinlib.set_pin_value(pin, str(pval))
                set_pins.append({"pin": pname, "ok": True, "value": str(pval)})
            except Exception as exc:
                set_pins.append({"pin": pname, "ok": False, "error": str(exc)})

        created.append(
            {
                "id": spec.get("id"),
                "success": True,
                "title": _node_title(node),
                "name": node.get_name(),
                "how": how,
                "pins_set": set_pins,
            }
        )

    if compile:
        bel.compile_blueprint(bp)
    if save:
        unreal.EditorAssetLibrary.save_asset(asset_path)

    return {
        "success": all(c.get("success") for c in created) if created else False,
        "path": asset_path,
        "created": created,
        "status": _status_str(bp),
    }


def connect_blueprint_pins(
    asset_path: str,
    links: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    links item:
      {"from_node": "Event BeginPlay", "from_pin": "then", "to_node": "PrintString", "to_pin": "execute"}
    """
    bp = _load_bp(asset_path)
    bel = _bel()
    pinlib = _pinlib()
    editor, _graph = _editor_for(bp, graph_name)
    results: list[dict[str, Any]] = []

    for link in links or []:
        a = _find_node(editor, link.get("from_node", ""))
        b = _find_node(editor, link.get("to_node", ""))
        if not a or not b:
            results.append(
                {
                    "success": False,
                    "error": f"Node not found from={link.get('from_node')} to={link.get('to_node')}",
                    "from_found": bool(a),
                    "to_found": bool(b),
                }
            )
            continue
        pa = _find_pin(a, link.get("from_pin", "then"), prefer_direction="output")
        pb = _find_pin(b, link.get("to_pin", "execute"), prefer_direction="input")
        if not pa or not pb:
            results.append(
                {
                    "success": False,
                    "error": "Pin not found",
                    "from_pin": link.get("from_pin"),
                    "to_pin": link.get("to_pin"),
                    "from_pin_found": bool(pa),
                    "to_pin_found": bool(pb),
                    "from_title": _node_title(a),
                    "to_title": _node_title(b),
                    "from_pins": [p["name"] for p in _list_pins(a)],
                    "to_pins": [p["name"] for p in _list_pins(b)],
                }
            )
            continue
        try:
            ok = bool(pinlib.try_create_connection(pa, pb))
            results.append(
                {
                    "success": ok,
                    "from": _node_title(a),
                    "from_pin": _pin_name(pa),
                    "to": _node_title(b),
                    "to_pin": _pin_name(pb),
                }
            )
        except Exception as exc:
            results.append({"success": False, "error": str(exc)})

    if compile:
        bel.compile_blueprint(bp)
    if save:
        unreal.EditorAssetLibrary.save_asset(asset_path)

    return {
        "success": all(r.get("success") for r in results) if results else False,
        "path": asset_path,
        "links": results,
        "status": _status_str(bp),
    }


def set_blueprint_pin_defaults(
    asset_path: str,
    updates: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    bp = _load_bp(asset_path)
    bel = _bel()
    pinlib = _pinlib()
    editor, _graph = _editor_for(bp, graph_name)
    results: list[dict[str, Any]] = []

    for u in updates or []:
        node = _find_node(editor, u.get("node", ""))
        if not node:
            results.append({"success": False, "error": f"Node not found: {u.get('node')}"})
            continue
        pin = _find_pin(node, u.get("pin", ""))
        if not pin:
            results.append(
                {
                    "success": False,
                    "error": f"Pin not found: {u.get('pin')}",
                    "node": _node_title(node),
                    "available_pins": [p["name"] for p in _list_pins(node)],
                }
            )
            continue
        try:
            pinlib.set_pin_value(pin, str(u.get("value", "")))
            results.append(
                {
                    "success": True,
                    "node": _node_title(node),
                    "pin": _pin_name(pin),
                    "value": str(u.get("value", "")),
                }
            )
        except Exception as exc:
            results.append({"success": False, "error": str(exc)})

    if compile:
        bel.compile_blueprint(bp)
    if save:
        unreal.EditorAssetLibrary.save_asset(asset_path)

    return {
        "success": all(r.get("success") for r in results) if results else False,
        "path": asset_path,
        "updates": results,
        "status": _status_str(bp),
    }


def remove_blueprint_nodes(
    asset_path: str,
    node_names: list[str],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    bp = _load_bp(asset_path)
    bel = _bel()
    editor, _graph = _editor_for(bp, graph_name)
    to_remove = []
    missing = []
    for name in node_names or []:
        n = _find_node(editor, name)
        if n:
            to_remove.append(n)
        else:
            missing.append(name)
    if to_remove:
        editor.remove_nodes(to_remove)
    if compile:
        bel.compile_blueprint(bp)
    if save:
        unreal.EditorAssetLibrary.save_asset(asset_path)
    return {
        "success": len(missing) == 0,
        "path": asset_path,
        "removed": [_node_title(n) for n in to_remove],
        "missing": missing,
        "status": _status_str(bp),
    }


def add_blueprint_variable(
    asset_path: str,
    var_name: str,
    var_type: str = "bool",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    bp = _load_bp(asset_path)
    bel = _bel()
    t = (var_type or "bool").strip().lower()
    type_map = {
        "bool": "bool",
        "boolean": "bool",
        "int": "int",
        "int32": "int",
        "integer": "int",
        "float": "float",
        "double": "double",
        "string": "string",
        "str": "string",
        "name": "name",
        "text": "text",
        "vector": "vector",
        "rotator": "rotator",
        "transform": "transform",
    }
    basic = type_map.get(t, t)
    try:
        if hasattr(bel, "get_basic_type_by_name"):
            pin_type = bel.get_basic_type_by_name(basic)
            bel.add_member_variable(bp, var_name, pin_type)
        else:
            bel.add_member_variable(bp, var_name, var_type)
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "path": asset_path,
            "hint": "Try bool/int/float/string/vector",
        }

    if compile:
        bel.compile_blueprint(bp)
    if save:
        unreal.EditorAssetLibrary.save_asset(asset_path)

    var_list = []
    for name in ("list_member_variable_names", "get_member_variable_names"):
        fn = getattr(bel, name, None)
        if callable(fn):
            try:
                var_list = [str(x) for x in (fn(bp) or [])]
                break
            except Exception:
                pass

    return {
        "success": True,
        "path": asset_path,
        "variable": var_name,
        "type": var_type,
        "status": _status_str(bp),
        "variables": var_list,
    }


def compile_blueprint_detailed(asset_path: str, save_on_success: bool = True) -> dict[str, Any]:
    bp = _load_bp(asset_path)
    bel = _bel()
    editor, _graph = _editor_for(bp, "")
    bel.compile_blueprint(bp)
    status = _status_str(bp)

    errors = []
    warnings = []
    for name, bucket in (
        ("list_nodes_with_errors", errors),
        ("list_nodes_with_warnings", warnings),
    ):
        fn = getattr(editor, name, None)
        if callable(fn):
            try:
                for n in list(fn() or []):
                    bucket.append({"node": _node_title(n), "name": n.get_name()})
            except Exception:
                pass

    up_to_date = "UP_TO_DATE" in status.upper() or status.endswith("3")
    saved = False
    if save_on_success and up_to_date and not errors:
        saved = bool(unreal.EditorAssetLibrary.save_asset(asset_path))

    return {
        "success": up_to_date and not errors,
        "path": asset_path,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "saved": saved,
    }


def add_beginplay_print(
    asset_path: str,
    message: str = "Hello from Cursor Bridge",
    x: int = 400,
    y: int = 0,
) -> dict[str, Any]:
    """Smoke-test helper: BeginPlay -> PrintString."""
    create = add_blueprint_nodes(
        asset_path,
        [
            {
                "id": "print",
                "type": "call",
                "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
                "x": x,
                "y": y,
                "pin_defaults": {"InString": message},
            }
        ],
        compile=False,
        save=False,
    )
    # Also try InString alternate pin name if needed is handled inside defaults
    link = connect_blueprint_pins(
        asset_path,
        [
            {
                "from_node": "ReceiveBeginPlay",
                "from_pin": "then",
                "to_node": "PrintString",
                "to_pin": "execute",
            }
        ],
        compile=True,
        save=True,
    )
    return {
        "success": bool(create.get("success") and link.get("success")),
        "path": asset_path,
        "create": create,
        "link": link,
    }
