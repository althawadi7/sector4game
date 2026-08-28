"""Widget Blueprint helpers (create + EventGraph via blueprint_ops).

UMG designer WidgetTree is protected in UE Python — EventGraph editing works.
"""

from __future__ import annotations

from typing import Any

import unreal

from . import blueprint_ops, safety


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _split(asset_path: str) -> tuple[str, str]:
    p = asset_path.strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p.rsplit("/", 1)


def create_widget_blueprint(
    asset_path: str,
    parent_class: str = "UserWidget",
    overwrite: bool = False,
) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not overwrite:
            return {"success": False, "error": f"Already exists: {path}"}
        unreal.EditorAssetLibrary.delete_asset(path)

    factory = unreal.WidgetBlueprintFactory()
    parent = unreal.UserWidget
    if parent_class and parent_class != "UserWidget":
        if parent_class.startswith("/"):
            loaded = unreal.EditorAssetLibrary.load_blueprint_class(parent_class)
            if loaded:
                parent = loaded
        else:
            parent = getattr(unreal, parent_class, unreal.UserWidget)
    factory.set_editor_property("parent_class", parent)

    wb = _tools().create_asset(name, folder, unreal.WidgetBlueprint, factory)
    if not wb:
        return {"success": False, "error": "WidgetBlueprintFactory failed"}
    unreal.EditorAssetLibrary.save_asset(path)
    return {
        "success": True,
        "path": path,
        "class": "WidgetBlueprint",
        "parent": str(parent),
        "note": (
            "Widget created. EventGraph editable via Blueprint tools. "
            "UMG WidgetTree designer hierarchy is not exposed to Python."
        ),
    }


def inspect_widget_blueprint(asset_path: str, graph_name: str = "") -> dict[str, Any]:
    path = asset_path.rsplit(".", 1)[0] if "." in asset_path.rsplit("/", 1)[-1] else asset_path
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        return {"success": False, "error": f"Not found: {path}"}
    if not isinstance(asset, unreal.WidgetBlueprint):
        return {
            "success": False,
            "error": f"Not a WidgetBlueprint: {path} ({asset.get_class().get_name()})",
        }
    info = blueprint_ops.inspect_blueprint(path, graph_name)
    info["asset_kind"] = "WidgetBlueprint"
    info["widget_tree_note"] = (
        "WidgetTree is protected in UE Python. Use EventGraph tools for logic; "
        "open UMG designer for hierarchy."
    )
    nodes = info.get("nodes") or []
    vars_ = info.get("variables") or []
    info["safety"] = safety.complexity_flags(len(nodes), len(vars_))
    return info
