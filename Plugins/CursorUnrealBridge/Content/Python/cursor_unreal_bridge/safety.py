"""Edit safety for gameplay / complex assets (inspect-first, Aura-like)."""

from __future__ import annotations

from typing import Any

PROTOTYPE_PREFIXES = (
    "/Game/CursorTest/",
)

PROTECTED_SUBSTRINGS = (
    "BP_Pistol",
    "BP_Zombie_Pawn",
    "BP_XRPawn",
    "BP_Zombie",
    "WBP_HUD",
    "WBP_Menu",
    "BT_Zombie",
    "BB_Zombie",
    "/Game/Zombie/",
    "/Game/XRFramework/Blueprints/",
    "/Game/Weapons/",
)


def normalize_path(asset_path: str) -> str:
    p = (asset_path or "").strip().replace("\\", "/")
    if "." in p.rsplit("/", 1)[-1]:
        pkg, leaf = p.rsplit("/", 1)
        if "." in leaf:
            p = f"{pkg}/{leaf.split('.', 1)[0]}"
    return p


def is_prototype(asset_path: str) -> bool:
    p = normalize_path(asset_path)
    return any(p.startswith(pref) for pref in PROTOTYPE_PREFIXES)


def is_protected(asset_path: str) -> bool:
    p = normalize_path(asset_path)
    if is_prototype(p):
        return False
    low = p.lower()
    return any(needle.lower() in low for needle in PROTECTED_SUBSTRINGS)


def guard_edit(
    asset_path: str,
    force: bool = False,
    action: str = "edit",
    inspect_summary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return None if allowed; otherwise a needs_force payload."""
    if force or not is_protected(asset_path):
        return None
    return {
        "success": False,
        "needs_force": True,
        "action": action,
        "path": normalize_path(asset_path),
        "reason": (
            "Protected gameplay / complex asset. "
            "Inspect first, then retry with force=True."
        ),
        "hint": (
            "Use inspect_blueprint / inspect_behavior_tree / inspect_widget_blueprint, "
            "then call again with force=True for a minimal diff."
        ),
        "inspect_summary": inspect_summary,
    }


def complexity_flags(node_count: int, variable_count: int = 0) -> dict[str, Any]:
    level = "simple"
    if node_count >= 80 or variable_count >= 40:
        level = "high"
    elif node_count >= 25 or variable_count >= 15:
        level = "medium"
    return {
        "complexity": level,
        "node_count": node_count,
        "variable_count": variable_count,
        "recommend_inspect_first": level != "simple",
    }
