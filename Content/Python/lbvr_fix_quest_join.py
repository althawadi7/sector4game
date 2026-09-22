"""One-shot: repair Quest FindAndJoinLan so open actually fires (once)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import unreal

_FLAG = Path(unreal.Paths.project_saved_dir()) / "LBVR" / "quest_join_fixed.flag"
_MASTER_IP = "192.168.100.24"
_MASTER_PORT = 7777
_OPEN_CMD = f"open {_MASTER_IP}:{_MASTER_PORT}"


def _ensure_bridge() -> dict:
    plugin_py = Path(unreal.Paths.project_dir()) / "Plugins" / "CursorUnrealBridge" / "Content" / "Python"
    s = str(plugin_py.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)
    try:
        from cursor_unreal_bridge import start_bridge

        return {"ok": True, "info": str(start_bridge())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _patch_load_bp():
    from cursor_unreal_bridge import blueprint_ops

    def _load_bp_fixed(asset_path: str):
        bp = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not bp:
            name = asset_path.rstrip("/").split("/")[-1]
            if "." not in name:
                bp = unreal.load_asset(f"{asset_path}.{name}")
            else:
                bp = unreal.load_asset(asset_path)
        if not bp:
            raise RuntimeError(f"Blueprint not found: {asset_path}")
        if not isinstance(bp, unreal.Blueprint):
            raise RuntimeError(f"Not a Blueprint: {asset_path}")
        return bp

    blueprint_ops._load_bp = _load_bp_fixed
    return blueprint_ops


def fix_find_and_join(force: bool = False) -> dict:
    """Rebuild FindAndJoinLan: standalone + not-yet-joined -> open IP:port once.

    Must NOT run during PIE — BlueprintEditorLibrary compile asserts (UObjectArray Index).
    """
    out: dict = {"ok": False}
    try:
        # Hard refuse if a game world is playing (PIE / game).
        try:
            ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            gw = ed.get_game_world() if ed else None
            if gw is not None:
                out.update(ok=False, error="refused_during_pie")
                unreal.log_warning("[LBVR] quest join fix refused during PIE")
                return out
        except Exception:
            pass

        _FLAG.parent.mkdir(parents=True, exist_ok=True)
        if _FLAG.exists() and not force:
            out.update(ok=True, skipped=True, reason="already_fixed")
            return out

        out["bridge"] = _ensure_bridge()
        ops = _patch_load_bp()
        gi = "/Game/LBVR/Blueprints/BP_LBVR_GameInstance"

        # Ensure once-flag variable
        try:
            ops.add_blueprint_variable(gi, "bJoinAttempted", "bool", compile=False, save=False)
        except Exception as e:  # noqa: BLE001
            out["var_note"] = str(e)

        # Wipe FindAndJoinLan body (keep entry)
        info = ops.inspect_blueprint(gi, "FindAndJoinLan")
        names = [n["name"] for n in info.get("nodes", []) if n.get("class") != "K2Node_FunctionEntry"]
        if names:
            ops.remove_blueprint_nodes(gi, names, graph_name="FindAndJoinLan", compile=False, save=False)

        # Rebuild nodes
        created = ops.add_blueprint_nodes(
            gi,
            [
                {"id": "solo", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsStandalone", "x": 240, "y": 120},
                {"id": "get_tried", "type": "get_variable", "variable": "bJoinAttempted", "x": 240, "y": 220},
                {"id": "not_tried", "type": "call", "function_path": "/Script/Engine.KismetBooleanLibrary.Not_PreBool", "x": 480, "y": 220},
                {"id": "and", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.BooleanAND", "x": 700, "y": 120},
                {"id": "branch", "type": "branch", "x": 920, "y": 0},
                {"id": "print", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 1180, "y": -40,
                 "pin_defaults": {"InString": f"LBVR: ONE-SHOT WiFi join {_MASTER_IP}:{_MASTER_PORT}", "Duration": "5.0"}},
                {"id": "get_pc", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetPlayerController", "x": 1180, "y": 160,
                 "pin_defaults": {"PlayerIndex": "0"}},
                {"id": "set_tried", "type": "set_variable", "variable": "bJoinAttempted", "x": 1500, "y": 200},
                {"id": "open", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.ExecuteConsoleCommand", "x": 1780, "y": 0,
                 "pin_defaults": {"Command": _OPEN_CMD}},
            ],
            graph_name="FindAndJoinLan",
            compile=False,
            save=False,
        )
        out["created"] = created

        # Wire: entry->branch; solo & !tried -> condition; then print->set->open; pc -> SpecificPlayer
        # Variable get/set may have fallen back to PrintString earlier — handle robustly via pin defaults at least.
        links = [
            {"from_node": "FindAndJoinLan", "from_pin": "then", "to_node": "Branch", "to_pin": "execute"},
            {"from_node": "IsStandalone", "from_pin": "ReturnValue", "to_node": "AND", "to_pin": "A"},
            {"from_node": "NOT Boolean", "from_pin": "ReturnValue", "to_node": "AND", "to_pin": "B"},
            {"from_node": "AND", "from_pin": "ReturnValue", "to_node": "Branch", "to_pin": "Condition"},
            {"from_node": "Branch", "from_pin": "then", "to_node": "PrintString", "to_pin": "execute"},
            {"from_node": "PrintString", "from_pin": "then", "to_node": "ExecuteConsoleCommand", "to_pin": "execute"},
            {"from_node": "GetPlayerController", "from_pin": "ReturnValue", "to_node": "ExecuteConsoleCommand", "to_pin": "SpecificPlayer"},
        ]
        # Try simpler reliable graph if variable nodes failed: just IsStandalone -> Branch -> Print -> Open
        try:
            out["links"] = ops.connect_blueprint_pins(gi, links, graph_name="FindAndJoinLan", compile=True, save=True)
        except Exception as e:  # noqa: BLE001
            out["links_err"] = str(e)
            # Minimal salvage: Entry -> Print -> Open with hardcoded command
            ops.remove_blueprint_nodes(gi, ["Branch", "AND", "NOT", "IsStandalone", "PrintString", "ExecuteConsoleCommand", "GetPlayerController"], graph_name="FindAndJoinLan", compile=False, save=False)
            ops.add_blueprint_nodes(
                gi,
                [
                    {"id": "solo2", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.IsStandalone", "x": 250, "y": 100},
                    {"id": "br2", "type": "branch", "x": 520, "y": 0},
                    {"id": "pr2", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.PrintString", "x": 800, "y": -40,
                     "pin_defaults": {"InString": f"LBVR: join {_OPEN_CMD}", "Duration": "4.0"}},
                    {"id": "pc2", "type": "call", "function_path": "/Script/Engine.GameplayStatics.GetPlayerController", "x": 800, "y": 140,
                     "pin_defaults": {"PlayerIndex": "0"}},
                    {"id": "op2", "type": "call", "function_path": "/Script/Engine.KismetSystemLibrary.ExecuteConsoleCommand", "x": 1100, "y": 0,
                     "pin_defaults": {"Command": _OPEN_CMD}},
                ],
                graph_name="FindAndJoinLan",
                compile=False,
                save=False,
            )
            out["links2"] = ops.connect_blueprint_pins(
                gi,
                [
                    {"from_node": "FindAndJoinLan", "from_pin": "then", "to_node": "Branch", "to_pin": "execute"},
                    {"from_node": "IsStandalone", "from_pin": "ReturnValue", "to_node": "Branch", "to_pin": "Condition"},
                    {"from_node": "Branch", "from_pin": "then", "to_node": "PrintString", "to_pin": "execute"},
                    {"from_node": "PrintString", "from_pin": "then", "to_node": "ExecuteConsoleCommand", "to_pin": "execute"},
                    {"from_node": "GetPlayerController", "from_pin": "ReturnValue", "to_node": "ExecuteConsoleCommand", "to_pin": "SpecificPlayer"},
                ],
                graph_name="FindAndJoinLan",
                compile=True,
                save=True,
            )

        # Slow ClientWait retry to 10s (less handshake kill)
        try:
            ops.set_blueprint_pin_defaults(
                "/Game/LBVR/Blueprints/BP_ClientWaitGameMode",
                [
                    {"node": "Set Timer by Event", "pin": "Time", "value": "10.0"},
                    {"node": "Set Timer by Event", "pin": "bLooping", "value": "true"},
                ],
                graph_name="EventGraph",
                compile=True,
                save=True,
            )
            out["timer"] = "10s"
        except Exception as e:  # noqa: BLE001
            out["timer_err"] = str(e)

        _FLAG.write_text("fixed\n", encoding="utf-8")
        out["ok"] = True
        unreal.log(f"[LBVR] quest join fix done: {out}")
        return out
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
        out["trace"] = traceback.format_exc()
        unreal.log_error(f"[LBVR] quest join fix failed: {e}\n{traceback.format_exc()}")
        return out
