"""Behavior Tree + Blackboard helpers (local Aura-like AI tools)."""

from __future__ import annotations

from typing import Any

import unreal

from . import safety

_KEY_TYPE_MAP = {
    "bool": "Bool",
    "int": "Int",
    "float": "Float",
    "string": "String",
    "name": "Name",
    "vector": "Vector",
    "object": "Object",
    "class": "Class",
    "enum": "Enum",
    "rotator": "Rotator",
}


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _split(asset_path: str) -> tuple[str, str]:
    p = asset_path.strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p.rsplit("/", 1)


def _norm(asset_path: str) -> str:
    p = asset_path.strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p


def create_blackboard(asset_path: str, overwrite: bool = False) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not overwrite:
            return {"success": False, "error": f"Already exists: {path}"}
        unreal.EditorAssetLibrary.delete_asset(path)
    bb = _tools().create_asset(
        name, folder, unreal.BlackboardData, unreal.BlackboardDataFactory()
    )
    if not bb:
        return {"success": False, "error": "BlackboardDataFactory failed"}
    unreal.EditorAssetLibrary.save_asset(path)
    return {"success": True, "path": path, "class": "BlackboardData"}


def inspect_blackboard(asset_path: str) -> dict[str, Any]:
    path = _norm(asset_path)
    bb = unreal.EditorAssetLibrary.load_asset(path)
    if not bb:
        return {"success": False, "error": f"Not found: {path}"}
    keys = []
    try:
        for k in list(bb.get_editor_property("keys") or []):
            kn = str(k.get_editor_property("entry_name"))
            kt = k.get_editor_property("key_type")
            keys.append(
                {
                    "name": kn,
                    "type": kt.get_class().get_name() if kt else None,
                }
            )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "path": path, "keys": keys, "count": len(keys)}


def add_blackboard_keys(
    asset_path: str,
    keys: list | None = None,
    force: bool = False,
) -> dict[str, Any]:
    path = _norm(asset_path)
    blocked = safety.guard_edit(path, force=force, action="add_blackboard_keys")
    if blocked:
        blocked["inspect_summary"] = inspect_blackboard(path)
        return blocked
    bb = unreal.EditorAssetLibrary.load_asset(path)
    if not bb:
        return {"success": False, "error": f"Not found: {path}"}

    existing = list(bb.get_editor_property("keys") or [])
    existing_names: set[str] = set()
    for k in existing:
        try:
            existing_names.add(str(k.get_editor_property("entry_name")))
        except Exception:
            pass

    added = []
    for item in keys or []:
        if isinstance(item, str):
            name, ktype = item, "bool"
        else:
            name = str(item.get("name") or item.get("key") or "")
            ktype = str(item.get("type") or item.get("key_type") or "bool")
        if not name:
            continue
        if name in existing_names:
            added.append({"name": name, "ok": False, "error": "already exists"})
            continue
        short = _KEY_TYPE_MAP.get(ktype.lower(), ktype)
        cls = unreal.load_class(None, f"/Script/AIModule.BlackboardKeyType_{short}")
        if not cls:
            added.append({"name": name, "ok": False, "error": f"unknown type {ktype}"})
            continue
        kt = unreal.new_object(cls, bb)
        entry = unreal.BlackboardEntry()
        entry.set_editor_property("entry_name", name)
        entry.set_editor_property("key_type", kt)
        existing.append(entry)
        existing_names.add(name)
        added.append({"name": name, "ok": True, "type": short})

    bb.set_editor_property("keys", existing)
    unreal.EditorAssetLibrary.save_asset(path)
    return {
        "success": True,
        "path": path,
        "added": added,
        "keys": inspect_blackboard(path).get("keys"),
    }


def create_behavior_tree(
    asset_path: str,
    blackboard_path: str = "",
    overwrite: bool = False,
) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not overwrite:
            return {"success": False, "error": f"Already exists: {path}"}
        unreal.EditorAssetLibrary.delete_asset(path)

    bt = _tools().create_asset(
        name, folder, unreal.BehaviorTree, unreal.BehaviorTreeFactory()
    )
    if not bt:
        return {"success": False, "error": "BehaviorTreeFactory failed"}

    if not bt.root_node:
        sel = unreal.new_object(unreal.BTComposite_Selector, bt, unreal.Name("RootSelector"))
        bt.set_editor_property("root_node", sel)

    linked = None
    if blackboard_path:
        bb_path = _norm(blackboard_path)
        bb = unreal.EditorAssetLibrary.load_asset(bb_path)
        if not bb:
            return {"success": False, "error": f"Blackboard not found: {bb_path}", "path": path}
        bt.set_editor_property("blackboard_asset", bb)
        linked = bb_path

    unreal.EditorAssetLibrary.save_asset(path)
    return {
        "success": True,
        "path": path,
        "root": type(bt.root_node).__name__ if bt.root_node else None,
        "blackboard": linked,
    }


def link_behavior_tree_blackboard(
    bt_path: str,
    blackboard_path: str,
    force: bool = False,
) -> dict[str, Any]:
    path = _norm(bt_path)
    blocked = safety.guard_edit(path, force=force, action="link_behavior_tree_blackboard")
    if blocked:
        return blocked
    bt = unreal.EditorAssetLibrary.load_asset(path)
    bb = unreal.EditorAssetLibrary.load_asset(_norm(blackboard_path))
    if not bt:
        return {"success": False, "error": f"BT not found: {path}"}
    if not bb:
        return {"success": False, "error": f"Blackboard not found: {blackboard_path}"}
    bt.set_editor_property("blackboard_asset", bb)
    unreal.EditorAssetLibrary.save_asset(path)
    return {"success": True, "path": path, "blackboard": _norm(blackboard_path)}


def _summarize_node(node, depth: int = 0, max_depth: int = 4) -> dict[str, Any]:
    if not node or depth > max_depth:
        return {"class": None}
    info: dict[str, Any] = {
        "class": node.get_class().get_name(),
        "name": node.get_name(),
        "depth": depth,
    }
    try:
        children = list(node.get_editor_property("children") or [])
    except Exception:
        children = []
    kids = []
    for c in children:
        try:
            task = c.get_editor_property("child_task")
            comp = c.get_editor_property("child_composite")
        except Exception:
            task = None
            comp = None
        if comp:
            kids.append(_summarize_node(comp, depth + 1, max_depth))
        elif task:
            kids.append(
                {
                    "class": task.get_class().get_name(),
                    "name": task.get_name(),
                    "depth": depth + 1,
                    "kind": "task",
                }
            )
        else:
            kids.append({"class": type(c).__name__, "kind": "empty"})
    if kids:
        info["children"] = kids
    return info


def inspect_behavior_tree(asset_path: str) -> dict[str, Any]:
    path = _norm(asset_path)
    bt = unreal.EditorAssetLibrary.load_asset(path)
    if not bt:
        return {"success": False, "error": f"Not found: {path}"}
    bb = None
    try:
        bb = bt.get_blackboard_asset()
    except Exception:
        try:
            bb = bt.get_editor_property("blackboard_asset")
        except Exception:
            bb = None
    root = bt.root_node
    return {
        "success": True,
        "path": path,
        "blackboard": bb.get_path_name() if bb else None,
        "root": type(root).__name__ if root else None,
        "tree": _summarize_node(root) if root else None,
        "protected": safety.is_protected(path),
    }


def add_behavior_tree_wait_task(
    asset_path: str,
    wait_seconds: float = 1.0,
    force: bool = False,
) -> dict[str, Any]:
    """Add a BTTask_Wait under the root composite."""
    path = _norm(asset_path)
    blocked = safety.guard_edit(
        path,
        force=force,
        action="add_behavior_tree_wait_task",
        inspect_summary=inspect_behavior_tree(path),
    )
    if blocked:
        return blocked
    bt = unreal.EditorAssetLibrary.load_asset(path)
    if not bt:
        return {"success": False, "error": f"Not found: {path}"}
    if not bt.root_node:
        sel = unreal.new_object(unreal.BTComposite_Selector, bt, unreal.Name("RootSelector"))
        bt.set_editor_property("root_node", sel)

    wait = unreal.new_object(unreal.BTTask_Wait, bt)
    try:
        vt = wait.get_editor_property("wait_time")
        vt.set_editor_property("default_value", float(wait_seconds))
        wait.set_editor_property("wait_time", vt)
    except Exception as exc:
        return {"success": False, "error": f"Could not set wait_time: {exc}"}

    child = unreal.BTCompositeChild()
    child.set_editor_property("child_task", wait)
    children = list(bt.root_node.get_editor_property("children") or [])
    children.append(child)
    bt.root_node.set_editor_property("children", children)
    unreal.EditorAssetLibrary.save_asset(path)
    return {
        "success": True,
        "path": path,
        "added": "BTTask_Wait",
        "wait_seconds": float(wait_seconds),
        "child_count": len(children),
        "tree": inspect_behavior_tree(path).get("tree"),
    }
