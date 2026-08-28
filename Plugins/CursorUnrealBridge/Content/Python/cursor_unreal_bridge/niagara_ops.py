"""Niagara system helpers."""

from __future__ import annotations

from typing import Any

import unreal


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _split(asset_path: str) -> tuple[str, str]:
    p = asset_path.strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p.rsplit("/", 1)


def create_niagara_system(asset_path: str, overwrite: bool = False) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not overwrite:
            return {"success": False, "error": f"Already exists: {path}"}
        unreal.EditorAssetLibrary.delete_asset(path)
    ns = _tools().create_asset(
        name, folder, unreal.NiagaraSystem, unreal.NiagaraSystemFactoryNew()
    )
    if not ns:
        return {"success": False, "error": "NiagaraSystemFactoryNew failed"}
    unreal.EditorAssetLibrary.save_asset(path)
    return {
        "success": True,
        "path": path,
        "class": "NiagaraSystem",
        "note": "Empty Niagara system created. Open Niagara editor for emitter modules.",
    }


def inspect_niagara_system(asset_path: str) -> dict[str, Any]:
    path = asset_path.rsplit(".", 1)[0] if "." in asset_path.rsplit("/", 1)[-1] else asset_path
    ns = unreal.EditorAssetLibrary.load_asset(path)
    if not ns:
        return {"success": False, "error": f"Not found: {path}"}
    if not isinstance(ns, unreal.NiagaraSystem):
        return {"success": False, "error": f"Not a NiagaraSystem: {path}"}
    return {
        "success": True,
        "path": path,
        "class": ns.get_class().get_name(),
        "name": ns.get_name(),
        "note": "Emitter module graph APIs are limited in Python; use Niagara editor for deep VFX.",
    }


def spawn_niagara_actor(
    system_path: str,
    location: list[float] | None = None,
    label: str = "",
) -> dict[str, Any]:
    path = system_path.rsplit(".", 1)[0] if "." in system_path.rsplit("/", 1)[-1] else system_path
    ns = unreal.EditorAssetLibrary.load_asset(path)
    if not ns:
        return {"success": False, "error": f"Niagara system not found: {path}"}
    loc = location or [0.0, 0.0, 100.0]
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = eas.spawn_actor_from_class(
        unreal.NiagaraActor,
        unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
    )
    if not actor:
        return {"success": False, "error": "Failed to spawn NiagaraActor"}
    try:
        comp = actor.niagara_component
        if comp:
            comp.set_asset(ns)
            comp.activate(True)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Spawned actor but failed to assign system: {exc}",
            "label": actor.get_actor_label(),
        }
    if label:
        actor.set_actor_label(label)
    return {
        "success": True,
        "label": actor.get_actor_label(),
        "system": path,
        "location": loc,
    }
