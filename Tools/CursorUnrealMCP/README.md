# Cursor Unreal MCP (VIP Blueprint power)

Local MCP → Unreal Editor via `CursorUnrealBridge` on `http://127.0.0.1:27182`.

Full docs: `E:\unrealengin-agint\README.md`

## Tools

### Core
- `unreal_status`, `execute_unreal_python`
- `list_unreal_actors`, `spawn_unreal_actor`, `set_unreal_actor_property`, `destroy_unreal_actor`
- `load_unreal_asset`, `save_unreal_asset`, `save_unreal_level`

### Blueprint (Aura-like, local)
- `inspect_blueprint`
- `create_blueprint`
- `add_blueprint_nodes`
- `connect_blueprint_pins`
- `set_blueprint_pin_defaults`
- `remove_blueprint_nodes`
- `add_blueprint_variable`
- `compile_unreal_blueprint`
- `add_beginplay_print`

## Setup

```powershell
cd "C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\CursorUnrealMCP"
python -m pip install -r requirements.txt
```

`~\.cursor\mcp.json` must include `cursor_unreal` pointing at this `server.py`.

## Restart bridge

If port 27182 is dead, in Unreal Python console:

```python
exec(open(r'C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python/restart_bridge.py', encoding='utf-8').read())
```

Then restart Cursor MCP / Cursor so new tools appear.
