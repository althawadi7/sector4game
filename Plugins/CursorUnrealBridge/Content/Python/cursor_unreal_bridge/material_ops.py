"""Material create/edit helpers (local Aura-like material tools).

NOTE: Aggressive MaterialEditingLibrary graph edits can crash UE if the
Material Editor toolkit is involved. We keep create paths conservative.
"""

from __future__ import annotations

from typing import Any

import unreal

from . import safety


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _mel():
    return unreal.MaterialEditingLibrary


def _split(asset_path: str) -> tuple[str, str]:
    p = asset_path.strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p.rsplit("/", 1)


def create_material(
    asset_path: str,
    base_color: list[float] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not overwrite:
                return {"success": False, "error": f"Already exists: {path}"}
            unreal.EditorAssetLibrary.delete_asset(path)

        factory = unreal.MaterialFactoryNew()
        mat = _tools().create_asset(name, folder, unreal.Material, factory)
        if not mat:
            return {"success": False, "error": "MaterialFactoryNew failed"}

        color = base_color or [0.2, 0.6, 1.0, 1.0]
        wired = False
        wire_error = None
        # Best-effort base color; never call recompile_material (can AV).
        try:
            mel = _mel()
            const = mel.create_material_expression(
                mat, unreal.MaterialExpressionConstant3Vector, -350, 0
            )
            if const:
                const.set_editor_property(
                    "constant",
                    unreal.LinearColor(
                        float(color[0]),
                        float(color[1]),
                        float(color[2]),
                        float(color[3] if len(color) > 3 else 1.0),
                    ),
                )
                mel.connect_material_property(
                    const, "", unreal.MaterialProperty.MP_BASE_COLOR
                )
                wired = True
        except Exception as exc:
            wire_error = str(exc)

        unreal.EditorAssetLibrary.save_asset(path)
        out = {
            "success": True,
            "path": path,
            "base_color": color,
            "wired_base_color": wired,
        }
        if wire_error:
            out["wire_warning"] = wire_error
        return out
    except Exception as exc:
        return {"success": False, "error": str(exc), "path": path}


def inspect_material(asset_path: str) -> dict[str, Any]:
    path = asset_path.rsplit(".", 1)[0] if "." in asset_path.rsplit("/", 1)[-1] else asset_path
    try:
        mat = unreal.EditorAssetLibrary.load_asset(path)
        if not mat:
            return {"success": False, "error": f"Not found: {path}"}
        exprs = []
        try:
            for e in list(_mel().get_material_expressions(mat) or []):
                exprs.append({"class": e.get_class().get_name(), "name": e.get_name()})
        except Exception as exc:
            exprs = [{"error": str(exc)}]
        return {
            "success": True,
            "path": path,
            "class": mat.get_class().get_name(),
            "expressions": exprs,
            "count": len(exprs),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "path": path}


def create_material_instance(
    asset_path: str,
    parent_path: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    folder, name = _split(asset_path)
    path = f"{folder}/{name}"
    try:
        parent = (
            parent_path.rsplit(".", 1)[0]
            if "." in parent_path.rsplit("/", 1)[-1]
            else parent_path
        )
        parent_mat = unreal.EditorAssetLibrary.load_asset(parent)
        if not parent_mat:
            return {"success": False, "error": f"Parent not found: {parent}"}
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not overwrite:
                return {"success": False, "error": f"Already exists: {path}"}
            unreal.EditorAssetLibrary.delete_asset(path)

        mi = _tools().create_asset(
            name,
            folder,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
        if not mi:
            return {"success": False, "error": "MIC factory failed"}
        _mel().set_material_instance_parent(mi, parent_mat)
        unreal.EditorAssetLibrary.save_asset(path)
        return {"success": True, "path": path, "parent": parent}
    except Exception as exc:
        return {"success": False, "error": str(exc), "path": path}


def set_material_instance_params(
    asset_path: str,
    scalars: dict | None = None,
    vectors: dict | None = None,
    textures: dict | None = None,
    force: bool = False,
) -> dict[str, Any]:
    path = asset_path.rsplit(".", 1)[0] if "." in asset_path.rsplit("/", 1)[-1] else asset_path
    blocked = safety.guard_edit(path, force=force, action="set_material_instance_params")
    if blocked:
        return blocked
    try:
        mi = unreal.EditorAssetLibrary.load_asset(path)
        if not mi:
            return {"success": False, "error": f"Not found: {path}"}
        mel = _mel()
        applied = []
        for k, v in (scalars or {}).items():
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
            applied.append({"scalar": k, "value": float(v)})
        for k, v in (vectors or {}).items():
            cols = list(v) if not isinstance(v, (int, float)) else [v, v, v, 1]
            while len(cols) < 4:
                cols.append(1.0 if len(cols) == 3 else 0.0)
            mel.set_material_instance_vector_parameter_value(
                mi,
                k,
                unreal.LinearColor(
                    float(cols[0]), float(cols[1]), float(cols[2]), float(cols[3])
                ),
            )
            applied.append({"vector": k, "value": cols})
        for k, tex_path in (textures or {}).items():
            tp = (
                tex_path.rsplit(".", 1)[0]
                if "." in str(tex_path).rsplit("/", 1)[-1]
                else tex_path
            )
            tex = unreal.EditorAssetLibrary.load_asset(tp)
            if not tex:
                applied.append({"texture": k, "ok": False, "error": f"missing {tp}"})
                continue
            mel.set_material_instance_texture_parameter_value(mi, k, tex)
            applied.append({"texture": k, "ok": True, "path": tp})
        unreal.EditorAssetLibrary.save_asset(path)
        return {"success": True, "path": path, "applied": applied}
    except Exception as exc:
        return {"success": False, "error": str(exc), "path": path}
