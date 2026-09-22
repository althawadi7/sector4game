"""
Master station boot helpers for Sector4 LBVR.
PIE-SAFE: never call force_enable_python_at_runtime (asserts/kills editor).
Station HTTP can be re-enabled by setting LBVR_STATION_HTTP=1 in process env later.
"""
from __future__ import annotations

import importlib
import os
import sys
import traceback

import unreal

_CONTENT_PY = unreal.Paths.project_content_dir() + "Python"
if _CONTENT_PY not in sys.path:
    sys.path.insert(0, _CONTENT_PY)

import lbvr_station_http as lbvr  # noqa: E402

importlib.reload(lbvr)

# Default OFF in PIE — Blueprint ExecutePython must not kill the editor.
_STATION_HTTP = os.environ.get("LBVR_STATION_HTTP", "0") == "1"


def _gi():
    try:
        editor_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor_sub.get_game_world() if editor_sub else None
        if world is None and editor_sub:
            world = editor_sub.get_editor_world()
    except Exception:
        world = None
    if world is None:
        try:
            world = unreal.EditorLevelLibrary.get_editor_world()
        except Exception:
            world = None
    if not world:
        return None
    try:
        return unreal.GameplayStatics.get_game_instance(world)
    except Exception:
        return None


def _print(msg: str, color=(0.2, 1, 0.6, 1), seconds=8.0):
    # Prefer log only — PrintString(None) can assert in some PIE contexts.
    try:
        unreal.log(msg)
    except Exception:
        pass
    try:
        unreal.SystemLibrary.print_string(
            None, msg, True, False, unreal.LinearColor(*color), float(seconds)
        )
    except Exception:
        pass


def _prop(gi, name: str, default=None):
    try:
        return gi.get_editor_property(name)
    except Exception:
        return default


def _set(gi, name: str, value) -> None:
    try:
        gi.set_editor_property(name, value)
    except Exception:
        pass


def master_boot() -> dict:
    """Called from Master BeginPlay via ExecutePython — must never assert."""
    try:
        # NEVER compile/edit Blueprints from PIE ExecutePython (UObjectArray assert).
        unreal.log("[LBVR] master_boot (safe mode)")
        if not _STATION_HTTP:
            unreal.log("[MASTER] LAN host ready (station HTTP paused — safe PIE)")
            return {"ok": True, "safe_mode": True, "station_http": False}

        gi = _gi()
        if not gi:
            unreal.log_error("[LBVR] master_boot: no GameInstance")
            return {"ok": False, "error": "no_gi"}

        base = str(_prop(gi, "ApiBaseUrl") or lbvr.DEFAULT_BASE)
        sid = str(_prop(gi, "StationId") or "")
        tok = str(_prop(gi, "StationToken") or "")
        lan_ip = str(_prop(gi, "LanIp") or "127.0.0.1")
        port = int(_prop(gi, "ListenPort") or 7777)
        room = _prop(gi, "RoomIndex", None)

        auth = lbvr.station_auth(base, sid, tok)
        if not auth.get("ok"):
            unreal.log_error(f"[LBVR] StationAuth failed: {auth}")
            _print(f"[MASTER] Station auth FAILED ({auth.get('status')})", (1, 0.2, 0.2, 1), 8.0)
            return auth

        data = auth["json"].get("data") or {}
        access = data.get("access_token") or ""
        _set(gi, "AccessToken", access)
        play_allowed = data.get("play_allowed", True)
        _set(gi, "bPlayAllowed", bool(play_allowed))
        if data.get("branch_id"):
            _set(gi, "BranchId", str(data["branch_id"]))
        if data.get("room_index") is not None:
            _set(gi, "RoomIndex", int(data["room_index"]))
        unreal.log("[LBVR] StationAuth OK")
        _print("[MASTER] Station auth OK", (0.2, 1, 0.6, 1), 6.0)

        lan = lbvr.publish_lan(base, access, lan_ip, port, game_slug="outbreak", status="waiting")
        if lan.get("ok"):
            code = (lan["json"].get("data") or {}).get("session_code") or ""
            _set(gi, "SessionCode", code)
            _print(f"[MASTER] Session code: {code}", (0.2, 0.85, 1, 1), 12.0)

        room_arg = int(room) if room not in (None, 0, "") else None
        poll = lbvr.poll_session(base, access, room_index=room_arg)
        pdata = (poll.get("json") or {}).get("data") or {}
        active = bool(pdata.get("active"))
        _set(gi, "bSessionActive", active)
        _set(gi, "LanStatus", "waiting")
        _set(gi, "bMatchInProgress", False)
        if active:
            _set(gi, "BookingId", str(pdata.get("booking_id") or ""))
            _set(gi, "ActiveGameSlug", str(pdata.get("game_slug") or ""))
            _print(f"[MASTER] Booking READY: {pdata.get('game_slug')}", (0.9, 1, 0.3, 1), 10.0)
        else:
            _print("[MASTER] Waiting for Flutter Unlock…", (1, 0.8, 0.2, 1), 8.0)

        return {
            "ok": True,
            "session_code": _prop(gi, "SessionCode"),
            "active": active,
            "play_allowed": play_allowed,
            "poll": pdata,
        }
    except Exception as e:  # noqa: BLE001
        unreal.log_error(f"[LBVR] master_boot crashed safely: {e}\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}


def master_tick_lan_and_poll() -> dict:
    try:
        if not _STATION_HTTP:
            return {"ok": True, "safe_mode": True}
        gi = _gi()
        if not gi:
            return {"ok": False}
        access = str(_prop(gi, "AccessToken") or "")
        if not access:
            return master_boot()
        # Keep tick minimal while debugging PIE stability
        return {"ok": True, "skipped": True}
    except Exception as e:  # noqa: BLE001
        unreal.log_error(f"[LBVR] master_tick crashed safely: {e}")
        return {"ok": False, "error": str(e)}


def master_session_start(connected_clients: int = 0) -> dict:
    try:
        if not _STATION_HTTP:
            unreal.log("[MASTER] START (safe mode) — travel allowed locally")
            return {"ok": True, "safe_mode": True}
        return {"ok": False, "error": "station_http_disabled"}
    except Exception as e:  # noqa: BLE001
        unreal.log_error(f"[LBVR] master_session_start crashed safely: {e}")
        return {"ok": False, "error": str(e)}


def master_session_end(
    aborted: bool = False,
    duration_seconds: int = 0,
    team_score: int = 0,
    players: list | None = None,
) -> dict:
    try:
        if not _STATION_HTTP:
            unreal.log("[MASTER] END (safe mode)")
            return {"ok": True, "safe_mode": True}
        return {"ok": False, "error": "station_http_disabled"}
    except Exception as e:  # noqa: BLE001
        unreal.log_error(f"[LBVR] master_session_end crashed safely: {e}")
        return {"ok": False, "error": str(e)}


def master_session_abort(reason: str = "operator_end") -> dict:
    return master_session_end(aborted=True)


def quest_discover(session_code: str = "", auto_join: bool = True) -> dict:
    """Do not call from cooked Android. Editor-only helper."""
    try:
        unreal.log("[LBVR] quest_discover ignored (use JoinAtAddress / bat)")
        return {"ok": False, "error": "disabled"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
