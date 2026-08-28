"""Asset discovery / duplicate helpers."""

from __future__ import annotations

from typing import Any

import unreal

from . import safety


def _norm(path: str) -> str:
    p = (path or "").strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p


def find_assets(
    class_name: str = "",
    path_prefix: str = "/Game",
    name_contains: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path(path_prefix, True) or []
    out: list[dict[str, Any]] = []
    name_q = (name_contains or "").lower()
    class_q = (class_name or "").lower()
    for a in assets:
        try:
            cn = str(a.asset_class_path.asset_name)
        except Exception:
            cn = str(getattr(a, "asset_class", ""))
        pkg = str(a.package_name)
        aname = str(getattr(a, "asset_name", pkg.rsplit("/", 1)[-1]))
        if class_q and class_q not in cn.lower():
            continue
        if name_q and name_q not in aname.lower() and name_q not in pkg.lower():
            continue
        out.append({"path": f"{pkg}.{aname}", "package": pkg, "name": aname, "class": cn})
        if len(out) >= max(1, int(limit)):
            break
    return {"success": True, "count": len(out), "assets": out}


def duplicate_asset(source_path: str, dest_path: str) -> dict[str, Any]:
    src, dst = _norm(source_path), _norm(dest_path)
    if not unreal.EditorAssetLibrary.does_asset_exist(src):
        return {"success": False, "error": f"Source not found: {src}"}
    if unreal.EditorAssetLibrary.does_asset_exist(dst):
        return {"success": False, "error": f"Destination already exists: {dst}"}
    ok = unreal.EditorAssetLibrary.duplicate_asset(src, dst)
    if not ok:
        return {"success": False, "error": "duplicate_asset failed"}
    unreal.EditorAssetLibrary.save_asset(dst)
    return {"success": True, "source": src, "path": dst}


def delete_asset(asset_path: str, force: bool = False) -> dict[str, Any]:
    path = _norm(asset_path)
    blocked = safety.guard_edit(path, force=force, action="delete_asset")
    if blocked:
        return blocked
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return {"success": False, "error": f"Not found: {path}"}
    ok = unreal.EditorAssetLibrary.delete_asset(path)
    return {"success": bool(ok), "path": path}
