"""
Cursor MCP server for CursorUnrealBridge.

Talks to Unreal Editor over localhost HTTP (default http://127.0.0.1:27182).
Requires Unreal Editor open with CursorUnrealBridge started.

Includes Aura-like Blueprint tools (local, no Aura login).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

BRIDGE_URL = "http://127.0.0.1:27182"

mcp = FastMCP(
    "cursor_unreal",
    instructions=(
        "Local Unreal Editor bridge (no Aura login). "
        "Unreal must be open with CursorUnrealBridge on localhost:27182. "
        "Prefer dedicated tools for Blueprints, Materials, Widgets, Niagara, "
        "Behavior Trees, and Blackboards. "
        "For protected gameplay assets (BP_Pistol, BP_Zombie_*, /Game/Zombie/, etc.) "
        "inspect first, then pass force=True for minimal edits. "
        "Prototype freely under /Game/CursorTest/. "
        "Use execute_unreal_python only when no dedicated tool fits."
    ),
)


def _get(path: str) -> dict[str, Any]:
    req = urllib.request.Request(f"{BRIDGE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"success": False, "error": body or str(exc)}
    except urllib.error.URLError as exc:
        return {
            "success": False,
            "error": (
                f"Cannot reach Unreal bridge at {BRIDGE_URL}. "
                f"Open sector4v2 in Unreal Editor and confirm Output Log shows "
                f"[CursorUnrealBridge] Started. Details: {exc}"
            ),
        }


def _cmd(command: str, **args: Any) -> dict[str, Any]:
    return _post("/command", {"command": command, "args": args})


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

@mcp.tool()
def unreal_status() -> dict[str, Any]:
    """Check if Unreal Editor bridge is running and return project info."""
    try:
        return _get("/status")
    except Exception as exc:
        return {
            "ok": False,
            "error": (
                f"Bridge offline ({exc}). Open Unreal with CursorUnrealBridge enabled."
            ),
        }


@mcp.tool()
def execute_unreal_python(code: str) -> dict[str, Any]:
    """
    Execute Python inside the Unreal Editor (game/editor thread).

    Use the `unreal` module. Optionally set RESULT = ... to return a value.
    blueprint_ops is also injected for advanced Blueprint helpers.
    """
    return _post("/execute_python", {"code": code})


@mcp.tool()
def list_unreal_actors(class_filter: str = "", label_filter: str = "") -> dict[str, Any]:
    """List actors in the current level. Optional substring filters for class/label."""
    return _cmd("list_actors", class_filter=class_filter, label_filter=label_filter)


@mcp.tool()
def spawn_unreal_actor(
    class_path: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    label: str = "",
    scale: list[float] | None = None,
) -> dict[str, Any]:
    """
    Spawn an actor. class_path examples:
    - /Game/Zombie/Blueprints/BP_Zombie_Pawn
    - PointLight
    - StaticMeshActor
    """
    return _cmd(
        "spawn_actor",
        class_path=class_path,
        location=location or [0, 0, 0],
        rotation=rotation or [0, 0, 0],
        label=label,
        scale=scale or [1, 1, 1],
    )


@mcp.tool()
def set_unreal_actor_property(
    actor_label: str, property_name: str, value: Any
) -> dict[str, Any]:
    """Set an editor property on an actor by label."""
    return _cmd(
        "set_actor_property",
        actor_label=actor_label,
        property_name=property_name,
        value=value,
    )


@mcp.tool()
def destroy_unreal_actor(actor_label: str) -> dict[str, Any]:
    """Destroy an actor by editor label."""
    return _cmd("destroy_actor", actor_label=actor_label)


@mcp.tool()
def save_unreal_asset(asset_path: str) -> dict[str, Any]:
    """Save an asset by soft path, e.g. /Game/XRFramework/Blueprints/BP_Pistol."""
    return _cmd("save_asset", asset_path=asset_path)


@mcp.tool()
def save_unreal_level() -> dict[str, Any]:
    """Save the currently open level."""
    return _cmd("save_current_level")


@mcp.tool()
def load_unreal_asset(asset_path: str) -> dict[str, Any]:
    """Load an asset and return basic metadata."""
    return _cmd("load_asset", asset_path=asset_path)


# ---------------------------------------------------------------------------
# Blueprint power (Aura-like, local)
# ---------------------------------------------------------------------------

@mcp.tool()
def inspect_blueprint(asset_path: str, graph_name: str = "") -> dict[str, Any]:
    """
    Inspect a Blueprint: graphs, variables, functions, events, nodes, pins.
    Example asset_path: /Game/XRFramework/Blueprints/BP_Pistol
    """
    return _cmd("inspect_blueprint", asset_path=asset_path, graph_name=graph_name)


@mcp.tool()
def create_blueprint(
    asset_path: str,
    parent_class: str = "Actor",
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Create a new Blueprint asset.
    parent_class: Actor, Pawn, Character, or /Game/... Blueprint path.
    """
    return _cmd(
        "create_blueprint",
        asset_path=asset_path,
        parent_class=parent_class,
        overwrite=overwrite,
    )


@mcp.tool()
def add_blueprint_nodes(
    asset_path: str,
    nodes: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    Add nodes to a Blueprint graph.

    nodes example:
    [
      {
        "id": "print1",
        "type": "call",
        "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
        "x": 400,
        "y": 0,
        "pin_defaults": {"InString": "Hello"}
      },
      {"type": "branch", "x": 700, "y": 0},
      {"type": "custom_event", "event_name": "OnHit", "x": 0, "y": 300},
      {"type": "palette", "palette": "Development|PrintString", "x": 400, "y": 200}
    ]
    """
    return _cmd(
        "add_blueprint_nodes",
        asset_path=asset_path,
        nodes=nodes,
        graph_name=graph_name,
        compile=compile,
        save=save,
    )


@mcp.tool()
def connect_blueprint_pins(
    asset_path: str,
    links: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    Wire Blueprint pins.

    links example:
    [
      {
        "from_node": "ReceiveBeginPlay",
        "from_pin": "then",
        "to_node": "PrintString",
        "to_pin": "execute"
      }
    ]
    Node names can be titles, substrings, or event member names.
    """
    return _cmd(
        "connect_blueprint_pins",
        asset_path=asset_path,
        links=links,
        graph_name=graph_name,
        compile=compile,
        save=save,
    )


@mcp.tool()
def set_blueprint_pin_defaults(
    asset_path: str,
    updates: list[dict[str, Any]],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    Set pin default values.

    updates example:
    [{"node": "PrintString", "pin": "InString", "value": "Ready"}]
    """
    return _cmd(
        "set_blueprint_pin_defaults",
        asset_path=asset_path,
        updates=updates,
        graph_name=graph_name,
        compile=compile,
        save=save,
    )


@mcp.tool()
def remove_blueprint_nodes(
    asset_path: str,
    node_names: list[str],
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """Remove nodes from a Blueprint graph by title/name substring."""
    return _cmd(
        "remove_blueprint_nodes",
        asset_path=asset_path,
        node_names=node_names,
        graph_name=graph_name,
        compile=compile,
        save=save,
    )


@mcp.tool()
def add_blueprint_variable(
    asset_path: str,
    var_name: str,
    var_type: str = "bool",
    compile: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """
    Add a Blueprint member variable.
    var_type: bool, int, float, string, name, vector, rotator, transform
    """
    return _cmd(
        "add_blueprint_variable",
        asset_path=asset_path,
        var_name=var_name,
        var_type=var_type,
        compile=compile,
        save=save,
    )


@mcp.tool()
def compile_unreal_blueprint(asset_path: str) -> dict[str, Any]:
    """Compile a Blueprint and return detailed status/errors. Saves on success."""
    return _cmd("compile_blueprint", asset_path=asset_path)


@mcp.tool()
def add_beginplay_print(
    asset_path: str,
    message: str = "Hello from Cursor Bridge",
    x: int = 400,
    y: int = 0,
    force: bool = False,
) -> dict[str, Any]:
    """Convenience smoke test: Event BeginPlay -> PrintString. Protected BPs need force=True."""
    return _cmd(
        "add_beginplay_print",
        asset_path=asset_path,
        message=message,
        x=x,
        y=y,
        force=force,
    )


# ---------------------------------------------------------------------------
# Aura extras (local): materials / widgets / Niagara / AI / assets
# ---------------------------------------------------------------------------

@mcp.tool()
def create_material(
    asset_path: str,
    base_color: list[float] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a Material with optional base color [R,G,B,A]."""
    return _cmd(
        "create_material",
        asset_path=asset_path,
        base_color=base_color,
        overwrite=overwrite,
    )


@mcp.tool()
def inspect_material(asset_path: str) -> dict[str, Any]:
    """Inspect a Material's expressions."""
    return _cmd("inspect_material", asset_path=asset_path)


@mcp.tool()
def create_material_instance(
    asset_path: str, parent_path: str, overwrite: bool = False
) -> dict[str, Any]:
    """Create a Material Instance Constant from a parent material."""
    return _cmd(
        "create_material_instance",
        asset_path=asset_path,
        parent_path=parent_path,
        overwrite=overwrite,
    )


@mcp.tool()
def set_material_instance_params(
    asset_path: str,
    scalars: dict | None = None,
    vectors: dict | None = None,
    textures: dict | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Set MIC scalar/vector/texture parameters."""
    return _cmd(
        "set_material_instance_params",
        asset_path=asset_path,
        scalars=scalars,
        vectors=vectors,
        textures=textures,
        force=force,
    )


@mcp.tool()
def create_widget_blueprint(
    asset_path: str, parent_class: str = "UserWidget", overwrite: bool = False
) -> dict[str, Any]:
    """
    Create a Widget Blueprint. EventGraph is editable via Blueprint tools.
    UMG designer WidgetTree hierarchy is not exposed to Python.
    """
    return _cmd(
        "create_widget_blueprint",
        asset_path=asset_path,
        parent_class=parent_class,
        overwrite=overwrite,
    )


@mcp.tool()
def inspect_widget_blueprint(asset_path: str, graph_name: str = "") -> dict[str, Any]:
    """Inspect a Widget Blueprint EventGraph (includes complexity safety flags)."""
    return _cmd(
        "inspect_widget_blueprint", asset_path=asset_path, graph_name=graph_name
    )


@mcp.tool()
def create_niagara_system(asset_path: str, overwrite: bool = False) -> dict[str, Any]:
    """Create an empty Niagara System asset."""
    return _cmd("create_niagara_system", asset_path=asset_path, overwrite=overwrite)


@mcp.tool()
def inspect_niagara_system(asset_path: str) -> dict[str, Any]:
    """Inspect a Niagara System asset (module graphs still need Niagara editor)."""
    return _cmd("inspect_niagara_system", asset_path=asset_path)


@mcp.tool()
def spawn_niagara_actor(
    system_path: str,
    location: list[float] | None = None,
    label: str = "",
) -> dict[str, Any]:
    """Spawn a NiagaraActor in the level and assign a Niagara System."""
    return _cmd(
        "spawn_niagara_actor",
        system_path=system_path,
        location=location,
        label=label,
    )


@mcp.tool()
def create_blackboard(asset_path: str, overwrite: bool = False) -> dict[str, Any]:
    """Create a BlackboardData asset."""
    return _cmd("create_blackboard", asset_path=asset_path, overwrite=overwrite)


@mcp.tool()
def inspect_blackboard(asset_path: str) -> dict[str, Any]:
    """List Blackboard keys."""
    return _cmd("inspect_blackboard", asset_path=asset_path)


@mcp.tool()
def add_blackboard_keys(
    asset_path: str, keys: list | None = None, force: bool = False
) -> dict[str, Any]:
    """
    Add Blackboard keys.
    keys example: [{"name": "TargetActor", "type": "object"}, {"name": "bAlive", "type": "bool"}]
    Types: bool, int, float, string, name, vector, object, class, enum, rotator
    """
    return _cmd(
        "add_blackboard_keys", asset_path=asset_path, keys=keys or [], force=force
    )


@mcp.tool()
def create_behavior_tree(
    asset_path: str, blackboard_path: str = "", overwrite: bool = False
) -> dict[str, Any]:
    """Create a Behavior Tree (root selector) and optionally link a Blackboard."""
    return _cmd(
        "create_behavior_tree",
        asset_path=asset_path,
        blackboard_path=blackboard_path,
        overwrite=overwrite,
    )


@mcp.tool()
def inspect_behavior_tree(asset_path: str) -> dict[str, Any]:
    """Inspect a Behavior Tree structure (root + children summary)."""
    return _cmd("inspect_behavior_tree", asset_path=asset_path)


@mcp.tool()
def link_behavior_tree_blackboard(
    bt_path: str, blackboard_path: str, force: bool = False
) -> dict[str, Any]:
    """Link a Behavior Tree to a Blackboard asset. Protected assets need force=True."""
    return _cmd(
        "link_behavior_tree_blackboard",
        bt_path=bt_path,
        blackboard_path=blackboard_path,
        force=force,
    )


@mcp.tool()
def add_behavior_tree_wait_task(
    asset_path: str, wait_seconds: float = 1.0, force: bool = False
) -> dict[str, Any]:
    """Add a BTTask_Wait under the BT root. Protected BTs need force=True."""
    return _cmd(
        "add_behavior_tree_wait_task",
        asset_path=asset_path,
        wait_seconds=wait_seconds,
        force=force,
    )


@mcp.tool()
def find_unreal_assets(
    class_name: str = "",
    path_prefix: str = "/Game",
    name_contains: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Find assets by class/name under a path prefix."""
    return _cmd(
        "find_assets",
        class_name=class_name,
        path_prefix=path_prefix,
        name_contains=name_contains,
        limit=limit,
    )


@mcp.tool()
def duplicate_unreal_asset(source_path: str, dest_path: str) -> dict[str, Any]:
    """Duplicate an asset to a new path."""
    return _cmd("duplicate_asset", source_path=source_path, dest_path=dest_path)


@mcp.tool()
def delete_unreal_asset(asset_path: str, force: bool = False) -> dict[str, Any]:
    """Delete an asset. Protected gameplay paths require force=True."""
    return _cmd("delete_asset", asset_path=asset_path, force=force)


if __name__ == "__main__":
    mcp.run(transport="stdio")
