"""Project init script — starts CursorUnrealBridge on editor launch."""

from __future__ import annotations

import sys
from pathlib import Path

import unreal


def _plugin_python_dir() -> Path:
    # <Project>/Plugins/CursorUnrealBridge/Content/Python
    project_dir = Path(unreal.Paths.project_dir())
    return project_dir / "Plugins" / "CursorUnrealBridge" / "Content" / "Python"


def main() -> None:
    plugin_py = _plugin_python_dir()
    if not plugin_py.exists():
        unreal.log_warning(f"[CursorUnrealBridge] Plugin Python folder missing: {plugin_py}")
        return

    path_str = str(plugin_py.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

    try:
        # Prefer explicit start module
        import start_bridge  # noqa: F401
    except Exception as exc:
        unreal.log_error(f"[CursorUnrealBridge] init failed: {exc}")


main()
