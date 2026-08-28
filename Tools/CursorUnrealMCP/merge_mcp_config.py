"""Merge cursor_unreal into ~/.cursor/mcp.json"""

from __future__ import annotations

import json
import os
from pathlib import Path

path = Path(os.environ["CURSOR_MCP_PATH"])
python = os.environ["CURSOR_UNREAL_PYTHON"]
server = os.environ["CURSOR_UNREAL_SERVER"]

data: dict = {}
if path.exists():
    data = json.loads(path.read_text(encoding="utf-8"))

servers = data.setdefault("mcpServers", {})
servers["cursor_unreal"] = {
    "command": python,
    "args": [server],
}

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated {path}")
print("Added mcpServers.cursor_unreal")
