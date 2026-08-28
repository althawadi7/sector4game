"""Plugin entry: start Cursor Unreal Bridge when editor Python loads."""

from __future__ import annotations

import sys
from pathlib import Path

import unreal


def _ensure_plugin_python_path() -> Path | None:
    """Add this plugin's Content/Python to sys.path."""
    plugin_python = Path(__file__).resolve().parent
    path_str = str(plugin_python)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return plugin_python


def start() -> None:
    _ensure_plugin_python_path()
    try:
        from cursor_unreal_bridge import start_bridge

        info = start_bridge()
        unreal.log(f"[CursorUnrealBridge] Started: {info}")
    except OSError as exc:
        # Port in use is fine if a previous session left it up
        unreal.log_warning(f"[CursorUnrealBridge] Could not bind port (maybe already running): {exc}")
    except Exception as exc:
        unreal.log_error(f"[CursorUnrealBridge] Failed to start: {exc}")


# Auto-start when this module is imported / executed
start()
