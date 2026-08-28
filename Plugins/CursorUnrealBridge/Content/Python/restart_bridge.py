"""Emergency restart for CursorUnrealBridge HTTP server.

In Unreal Output Log Cmd box, run:

  py.file "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python/restart_bridge.py"

Or restart the Unreal editor (bridge auto-starts).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import unreal

PLUGIN_PY = Path(__file__).resolve().parent
if str(PLUGIN_PY) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PY))


def _reload_all() -> list[str]:
    notes: list[str] = []
    try:
        if "cursor_unreal_bridge.http_server" in sys.modules:
            hs = sys.modules["cursor_unreal_bridge.http_server"]
            if hasattr(hs, "stop_bridge"):
                notes.append(f"stop={hs.stop_bridge()}")
    except Exception as exc:
        notes.append(f"stop_err={exc}")

    for name in [
        "cursor_unreal_bridge.safety",
        "cursor_unreal_bridge.asset_ops",
        "cursor_unreal_bridge.material_ops",
        "cursor_unreal_bridge.widget_ops",
        "cursor_unreal_bridge.niagara_ops",
        "cursor_unreal_bridge.ai_ops",
        "cursor_unreal_bridge.blueprint_ops",
        "cursor_unreal_bridge.commands",
        "cursor_unreal_bridge.game_thread",
        "cursor_unreal_bridge.http_server",
        "cursor_unreal_bridge",
    ]:
        if name in sys.modules:
            try:
                importlib.reload(sys.modules[name])
                notes.append(f"reload:{name}")
            except Exception as exc:
                notes.append(f"reload_fail:{name}:{exc}")
                unreal.log_warning(f"[CursorUnrealBridge] reload {name}: {exc}")
    return notes


_notes = _reload_all()

from cursor_unreal_bridge import commands  # noqa: E402
from cursor_unreal_bridge import get_status, start_bridge  # noqa: E402
from cursor_unreal_bridge.game_thread import ensure_tick  # noqa: E402

ensure_tick()
info = start_bridge()
unreal.log(f"[CursorUnrealBridge] Restarted: {info}")
unreal.log(f"[CursorUnrealBridge] Reload notes: {_notes}")
unreal.log(
    f"[CursorUnrealBridge] Commands ({len(commands.COMMANDS)}): {list(commands.COMMANDS.keys())}"
)
try:
    unreal.log(f"[CursorUnrealBridge] Status: {get_status()}")
except Exception as exc:
    unreal.log_warning(f"[CursorUnrealBridge] Status after restart failed: {exc}")
