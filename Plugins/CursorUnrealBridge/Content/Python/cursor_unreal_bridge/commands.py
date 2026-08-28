"""High-level Unreal Editor commands exposed over the local bridge."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import Any

import unreal

from . import (
    ai_ops,
    asset_ops,
    blueprint_ops,
    material_ops,
    niagara_ops,
    safety,
    widget_ops,
)
from .game_thread import run_on_game_thread


def _find_actor_by_label(label: str):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in eas.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _guard_bp(asset_path: str, force: bool, action: str) -> dict[str, Any] | None:
    summary = None
    try:
        info = blueprint_ops.inspect_blueprint(asset_path)
        summary = {
            "node_count": info.get("node_count"),
            "graphs": info.get("graphs"),
            "status": info.get("status"),
            "safety": safety.complexity_flags(
                int(info.get("node_count") or len(info.get("nodes") or [])),
                len(info.get("variables") or []),
            ),
        }
    except Exception as exc:
        summary = {"inspect_error": str(exc)}
    return safety.guard_edit(
        asset_path, force=force, action=action, inspect_summary=summary
    )


def get_status() -> dict[str, Any]:
    def _do():
        project = unreal.Paths.get_project_file_path()
        level = ""
        try:
            level = str(unreal.EditorLevelLibrary.get_editor_world())
        except Exception:
            try:
                level = str(
                    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
                )
            except Exception:
                pass
        return {
            "ok": True,
            "bridge": "CursorUnrealBridge",
            "project": project,
            "engine": unreal.SystemLibrary.get_engine_version(),
            "world": level,
            "blueprint_power": True,
            "aura_extras": True,
            "commands": sorted(COMMANDS.keys()),
        }

    return run_on_game_thread(_do)


def execute_python(code: str) -> dict[str, Any]:
    def _do():
        stdout = io.StringIO()
        local_env: dict[str, Any] = {
            "unreal": unreal,
            "__name__": "__bridge__",
            "blueprint_ops": blueprint_ops,
            "material_ops": material_ops,
            "widget_ops": widget_ops,
            "niagara_ops": niagara_ops,
            "ai_ops": ai_ops,
            "asset_ops": asset_ops,
            "safety": safety,
        }
        try:
            with redirect_stdout(stdout):
                exec(code, local_env, local_env)
            return {
                "success": True,
                "stdout": stdout.getvalue(),
                "result": local_env.get("RESULT", local_env.get("result")),
            }
        except Exception as exc:
            return {"success": False, "stdout": stdout.getvalue(), "error": str(exc)}

    return run_on_game_thread(_do)


def list_actors(class_filter: str = "", label_filter: str = "") -> dict[str, Any]:
    def _do():
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        out = []
        for actor in eas.get_all_level_actors():
            label = actor.get_actor_label()
            cls = actor.get_class().get_name()
            if class_filter and class_filter.lower() not in cls.lower():
                continue
            if label_filter and label_filter.lower() not in label.lower():
                continue
            loc = actor.get_actor_location()
            out.append(
                {
                    "label": label,
                    "class": cls,
                    "name": actor.get_name(),
                    "location": {"x": loc.x, "y": loc.y, "z": loc.z},
                }
            )
        return {"success": True, "actors": out, "count": len(out)}

    return run_on_game_thread(_do)


def spawn_actor(
    class_path: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    label: str = "",
    scale: list[float] | None = None,
) -> dict[str, Any]:
    def _do():
        loc = location or [0.0, 0.0, 0.0]
        rot = rotation or [0.0, 0.0, 0.0]
        scl = scale or [1.0, 1.0, 1.0]
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        actor_class = None
        tried: list[str] = []
        raw = (class_path or "").strip()
        candidates = [raw]
        if raw.endswith("_C") and "." in raw:
            candidates.append(raw.rsplit(".", 1)[0])
        if not raw.endswith("_C") and raw.startswith("/Game/"):
            leaf = raw.rstrip("/").rsplit("/", 1)[-1]
            candidates.append(f"{raw}.{leaf}_C")

        for cand in candidates:
            tried.append(cand)
            if cand.startswith("/Game/") and not cand.endswith("_C"):
                actor_class = unreal.EditorAssetLibrary.load_blueprint_class(cand)
            if actor_class is None and (cand.startswith("/Game/") or cand.startswith("/Script/")):
                actor_class = unreal.load_class(None, cand)
            if actor_class is None and cand.startswith("/Game/") and cand.endswith("_C"):
                soft = cand.rsplit(".", 1)[0] if "." in cand else cand[:-2]
                actor_class = unreal.EditorAssetLibrary.load_blueprint_class(soft)
            if actor_class is not None:
                break

        if actor_class is None and not raw.startswith("/"):
            actor_class = getattr(unreal, raw, None)

        if actor_class is None:
            return {"success": False, "error": f"Could not resolve class: {class_path}", "tried": tried}

        actor = eas.spawn_actor_from_class(
            actor_class,
            unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
            unreal.Rotator(float(rot[0]), float(rot[1]), float(rot[2])),
        )
        if not actor:
            return {"success": False, "error": "spawn_actor_from_class returned None"}
        if label:
            actor.set_actor_label(label)
        root = actor.root_component
        if root and scale:
            root.set_editor_property(
                "relative_scale3d",
                unreal.Vector(float(scl[0]), float(scl[1]), float(scl[2])),
            )
        return {
            "success": True,
            "label": actor.get_actor_label(),
            "class": actor.get_class().get_name(),
            "name": actor.get_name(),
        }

    return run_on_game_thread(_do)


def set_actor_property(actor_label: str, property_name: str, value: Any) -> dict[str, Any]:
    def _do():
        actor = _find_actor_by_label(actor_label)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_label}"}
        try:
            actor.set_editor_property(property_name, value)
            return {"success": True, "label": actor_label, "property": property_name}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return run_on_game_thread(_do)


def destroy_actor(actor_label: str) -> dict[str, Any]:
    def _do():
        actor = _find_actor_by_label(actor_label)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_label}"}
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)
        return {"success": True, "destroyed": actor_label}

    return run_on_game_thread(_do)


def save_asset(asset_path: str) -> dict[str, Any]:
    return run_on_game_thread(
        lambda: {"success": bool(unreal.EditorAssetLibrary.save_asset(asset_path)), "path": asset_path}
    )


def save_current_level() -> dict[str, Any]:
    def _do():
        ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return {"success": bool(ok)}

    return run_on_game_thread(_do)


def compile_blueprint(asset_path: str) -> dict[str, Any]:
    return run_on_game_thread(
        lambda: blueprint_ops.compile_blueprint_detailed(asset_path, save_on_success=True)
    )


def load_asset(asset_path: str) -> dict[str, Any]:
    def _do():
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            return {"success": False, "error": f"Asset not found: {asset_path}"}
        return {
            "success": True,
            "path": asset_path,
            "class": asset.get_class().get_name(),
            "name": asset.get_name(),
        }

    return run_on_game_thread(_do)


def inspect_blueprint(asset_path: str, graph_name: str = "") -> dict[str, Any]:
    def _do():
        info = blueprint_ops.inspect_blueprint(asset_path, graph_name)
        if info.get("success"):
            info["safety"] = safety.complexity_flags(
                int(info.get("node_count") or len(info.get("nodes") or [])),
                len(info.get("variables") or []),
            )
            info["protected"] = safety.is_protected(asset_path)
        return info

    return run_on_game_thread(_do)


def create_blueprint(
    asset_path: str, parent_class: str = "Actor", overwrite: bool = False
) -> dict[str, Any]:
    return run_on_game_thread(
        lambda: blueprint_ops.create_blueprint(asset_path, parent_class, overwrite)
    )


def add_blueprint_nodes(
    asset_path: str,
    nodes: list | None = None,
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "add_blueprint_nodes")
        if blocked:
            return blocked
        return blueprint_ops.add_blueprint_nodes(
            asset_path, nodes or [], graph_name, compile, save
        )

    return run_on_game_thread(_do)


def connect_blueprint_pins(
    asset_path: str,
    links: list | None = None,
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "connect_blueprint_pins")
        if blocked:
            return blocked
        return blueprint_ops.connect_blueprint_pins(
            asset_path, links or [], graph_name, compile, save
        )

    return run_on_game_thread(_do)


def set_blueprint_pin_defaults(
    asset_path: str,
    updates: list | None = None,
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "set_blueprint_pin_defaults")
        if blocked:
            return blocked
        return blueprint_ops.set_blueprint_pin_defaults(
            asset_path, updates or [], graph_name, compile, save
        )

    return run_on_game_thread(_do)


def remove_blueprint_nodes(
    asset_path: str,
    node_names: list | None = None,
    graph_name: str = "",
    compile: bool = True,
    save: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "remove_blueprint_nodes")
        if blocked:
            return blocked
        return blueprint_ops.remove_blueprint_nodes(
            asset_path, node_names or [], graph_name, compile, save
        )

    return run_on_game_thread(_do)


def add_blueprint_variable(
    asset_path: str,
    var_name: str,
    var_type: str = "bool",
    compile: bool = True,
    save: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "add_blueprint_variable")
        if blocked:
            return blocked
        return blueprint_ops.add_blueprint_variable(
            asset_path, var_name, var_type, compile, save
        )

    return run_on_game_thread(_do)


def add_beginplay_print(
    asset_path: str,
    message: str = "Hello from Cursor Bridge",
    x: int = 400,
    y: int = 0,
    force: bool = False,
) -> dict[str, Any]:
    def _do():
        blocked = _guard_bp(asset_path, force, "add_beginplay_print")
        if blocked:
            return blocked
        return blueprint_ops.add_beginplay_print(asset_path, message, x, y)

    return run_on_game_thread(_do)


def _gt(fn):
    return run_on_game_thread(fn)


COMMANDS: dict[str, Any] = {
    "get_status": lambda **_: get_status(),
    "execute_python": lambda **kw: execute_python(kw.get("code", "")),
    "list_actors": lambda **kw: list_actors(
        kw.get("class_filter", ""), kw.get("label_filter", "")
    ),
    "spawn_actor": lambda **kw: spawn_actor(
        kw.get("class_path", ""),
        kw.get("location"),
        kw.get("rotation"),
        kw.get("label", ""),
        kw.get("scale"),
    ),
    "set_actor_property": lambda **kw: set_actor_property(
        kw.get("actor_label", ""), kw.get("property_name", ""), kw.get("value")
    ),
    "destroy_actor": lambda **kw: destroy_actor(kw.get("actor_label", "")),
    "save_asset": lambda **kw: save_asset(kw.get("asset_path") or kw.get("asset_path") or ""),
    "save_current_level": lambda **_: save_current_level(),
    "compile_blueprint": lambda **kw: compile_blueprint(kw.get("asset_path") or kw.get("asset_path") or ""),
    "load_asset": lambda **kw: load_asset(kw.get("asset_path") or kw.get("asset_path") or ""),
    "inspect_blueprint": lambda **kw: inspect_blueprint(
        kw.get("asset_path", ""), kw.get("graph_name", "")
    ),
    "create_blueprint": lambda **kw: create_blueprint(
        kw.get("asset_path", ""),
        kw.get("parent_class", "Actor"),
        bool(kw.get("overwrite", False)),
    ),
    "add_blueprint_nodes": lambda **kw: add_blueprint_nodes(
        kw.get("asset_path", ""),
        kw.get("nodes") or [],
        kw.get("graph_name", ""),
        bool(kw.get("compile", True)),
        bool(kw.get("save", True)),
        bool(kw.get("force", False)),
    ),
    "connect_blueprint_pins": lambda **kw: connect_blueprint_pins(
        kw.get("asset_path", ""),
        kw.get("links") or [],
        kw.get("graph_name", ""),
        bool(kw.get("compile", True)),
        bool(kw.get("save", True)),
        bool(kw.get("force", False)),
    ),
    "set_blueprint_pin_defaults": lambda **kw: set_blueprint_pin_defaults(
        kw.get("asset_path", ""),
        kw.get("updates") or [],
        kw.get("graph_name", ""),
        bool(kw.get("compile", True)),
        bool(kw.get("save", True)),
        bool(kw.get("force", False)),
    ),
    "remove_blueprint_nodes": lambda **kw: remove_blueprint_nodes(
        kw.get("asset_path", ""),
        kw.get("node_names") or [],
        kw.get("graph_name", ""),
        bool(kw.get("compile", True)),
        bool(kw.get("save", True)),
        bool(kw.get("force", False)),
    ),
    "add_blueprint_variable": lambda **kw: add_blueprint_variable(
        kw.get("asset_path", ""),
        kw.get("var_name", ""),
        kw.get("var_type", "bool"),
        bool(kw.get("compile", True)),
        bool(kw.get("save", True)),
        bool(kw.get("force", False)),
    ),
    "add_beginplay_print": lambda **kw: add_beginplay_print(
        kw.get("asset_path", ""),
        kw.get("message", "Hello from Cursor Bridge"),
        int(kw.get("x", 400)),
        int(kw.get("y", 0)),
        bool(kw.get("force", False)),
    ),
    # Materials
    "create_material": lambda **kw: _gt(
        lambda: material_ops.create_material(
            kw.get("asset_path", ""),
            kw.get("base_color"),
            bool(kw.get("overwrite", False)),
        )
    ),
    "inspect_material": lambda **kw: _gt(
        lambda: material_ops.inspect_material(kw.get("asset_path", ""))
    ),
    "create_material_instance": lambda **kw: _gt(
        lambda: material_ops.create_material_instance(
            kw.get("asset_path", ""),
            kw.get("parent_path", ""),
            bool(kw.get("overwrite", False)),
        )
    ),
    "set_material_instance_params": lambda **kw: _gt(
        lambda: material_ops.set_material_instance_params(
            kw.get("asset_path", ""),
            kw.get("scalars"),
            kw.get("vectors"),
            kw.get("textures"),
            bool(kw.get("force", False)),
        )
    ),
    # Widgets
    "create_widget_blueprint": lambda **kw: _gt(
        lambda: widget_ops.create_widget_blueprint(
            kw.get("asset_path", ""),
            kw.get("parent_class", "UserWidget"),
            bool(kw.get("overwrite", False)),
        )
    ),
    "inspect_widget_blueprint": lambda **kw: _gt(
        lambda: widget_ops.inspect_widget_blueprint(
            kw.get("asset_path", ""), kw.get("graph_name", "")
        )
    ),
    # Niagara
    "create_niagara_system": lambda **kw: _gt(
        lambda: niagara_ops.create_niagara_system(
            kw.get("asset_path", ""), bool(kw.get("overwrite", False))
        )
    ),
    "inspect_niagara_system": lambda **kw: _gt(
        lambda: niagara_ops.inspect_niagara_system(kw.get("asset_path", ""))
    ),
    "spawn_niagara_actor": lambda **kw: _gt(
        lambda: niagara_ops.spawn_niagara_actor(
            kw.get("system_path", kw.get("asset_path", "")),
            kw.get("location"),
            kw.get("label", ""),
        )
    ),
    # AI
    "create_blackboard": lambda **kw: _gt(
        lambda: ai_ops.create_blackboard(
            kw.get("asset_path", ""), bool(kw.get("overwrite", False))
        )
    ),
    "inspect_blackboard": lambda **kw: _gt(
        lambda: ai_ops.inspect_blackboard(kw.get("asset_path", ""))
    ),
    "add_blackboard_keys": lambda **kw: _gt(
        lambda: ai_ops.add_blackboard_keys(
            kw.get("asset_path", ""),
            kw.get("keys") or [],
            bool(kw.get("force", False)),
        )
    ),
    "create_behavior_tree": lambda **kw: _gt(
        lambda: ai_ops.create_behavior_tree(
            kw.get("asset_path", ""),
            kw.get("blackboard_path", ""),
            bool(kw.get("overwrite", False)),
        )
    ),
    "inspect_behavior_tree": lambda **kw: _gt(
        lambda: ai_ops.inspect_behavior_tree(kw.get("asset_path", ""))
    ),
    "link_behavior_tree_blackboard": lambda **kw: _gt(
        lambda: ai_ops.link_behavior_tree_blackboard(
            kw.get("bt_path", kw.get("asset_path", "")),
            kw.get("blackboard_path", ""),
            bool(kw.get("force", False)),
        )
    ),
    "add_behavior_tree_wait_task": lambda **kw: _gt(
        lambda: ai_ops.add_behavior_tree_wait_task(
            kw.get("asset_path", ""),
            float(kw.get("wait_seconds", 1.0)),
            bool(kw.get("force", False)),
        )
    ),
    # Assets
    "find_assets": lambda **kw: _gt(
        lambda: asset_ops.find_assets(
            kw.get("class_name", ""),
            kw.get("path_prefix", "/Game"),
            kw.get("name_contains", ""),
            int(kw.get("limit", 50)),
        )
    ),
    "duplicate_asset": lambda **kw: _gt(
        lambda: asset_ops.duplicate_asset(
            kw.get("source_path", ""), kw.get("dest_path", "")
        )
    ),
    "delete_asset": lambda **kw: _gt(
        lambda: asset_ops.delete_asset(
            kw.get("asset_path", ""), bool(kw.get("force", False))
        )
    ),
}

# Accept both asset_path and path-style kwargs used by various clients
COMMANDS["save_asset"] = lambda **kw: save_asset(
    kw.get("asset_path") or kw.get("path") or ""
)
COMMANDS["load_asset"] = lambda **kw: load_asset(
    kw.get("asset_path") or kw.get("path") or ""
)
COMMANDS["list_actors"] = lambda **kw: list_actors(
    kw.get("class_filter") or kw.get("class_filter") or "",
    kw.get("label_filter") or kw.get("label_filter") or "",
)


def dispatch(command: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    if command not in COMMANDS:
        return {
            "success": False,
            "error": f"Unknown command: {command}",
            "available": list(COMMANDS),
        }
    try:
        return COMMANDS[command](**args)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
