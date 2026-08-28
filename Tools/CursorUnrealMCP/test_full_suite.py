"""Sequential smoke test for CursorUnrealBridge (Blueprint + Aura extras)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:27182"
ROOT = "/Game/CursorTest"


def _get(path: str, timeout: float = 20) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _cmd(command: str, args: dict | None = None, timeout: float = 120) -> dict:
    data = json.dumps({"command": command, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/command",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "error": body or str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def wait_ready(max_wait: float = 300) -> dict:
    start = time.time()
    last = None
    while time.time() - start < max_wait:
        try:
            st = _get("/status", timeout=5)
            if st.get("ok") and "create_material" in (st.get("commands") or []):
                return {"ready": True, "status": st}
            last = st
        except Exception as exc:
            last = {"error": str(exc)}
        time.sleep(3)
    return {"ready": False, "last": last}


def step(name: str, command: str, args: dict) -> dict:
    print(f"\n== {name} ==")
    # Confirm bridge still up
    try:
        _get("/health", timeout=5)
    except Exception as exc:
        print("BRIDGE DOWN before step:", exc)
        return {"success": False, "error": f"bridge down: {exc}"}
    res = _cmd(command, args)
    ok = bool(res.get("success") or res.get("ok") or res.get("needs_force"))
    print("OK" if ok else "FAIL", json.dumps(res, default=str)[:500])
    time.sleep(0.5)
    return res


def main() -> int:
    print("Waiting for Unreal bridge...")
    ready = wait_ready()
    if not ready.get("ready"):
        print("FAIL: bridge not ready", ready)
        return 1
    cmds = ready["status"].get("commands") or []
    print(f"READY aura_extras={ready['status'].get('aura_extras')} commands={len(cmds)}")

    results = {}
    results["list"] = step("list_actors", "list_actors", {"label_filter": ""})
    results["bp"] = step(
        "create_blueprint",
        "create_blueprint",
        {"asset_path": f"{ROOT}/BP_FullSmoke", "parent_class": "Actor", "overwrite": True},
    )
    results["var"] = step(
        "add_blueprint_variable",
        "add_blueprint_variable",
        {"asset_path": f"{ROOT}/BP_FullSmoke", "var_name": "SmokeOk", "var_type": "bool"},
    )
    results["begin"] = step(
        "add_beginplay_print",
        "add_beginplay_print",
        {"asset_path": f"{ROOT}/BP_FullSmoke", "message": "FULL SMOKE OK"},
    )
    results["compile"] = step(
        "compile_blueprint", "compile_blueprint", {"asset_path": f"{ROOT}/BP_FullSmoke"}
    )
    results["inspect_bp"] = step(
        "inspect_blueprint", "inspect_blueprint", {"asset_path": f"{ROOT}/BP_FullSmoke"}
    )

    results["mat"] = step(
        "create_material",
        "create_material",
        {
            "asset_path": f"{ROOT}/M_FullSmoke",
            "base_color": [0.1, 0.7, 1.0, 1.0],
            "overwrite": True,
        },
    )
    results["widget"] = step(
        "create_widget_blueprint",
        "create_widget_blueprint",
        {"asset_path": f"{ROOT}/WBP_FullSmoke", "overwrite": True},
    )
    results["niagara"] = step(
        "create_niagara_system",
        "create_niagara_system",
        {"asset_path": f"{ROOT}/NS_FullSmoke", "overwrite": True},
    )
    results["bb"] = step(
        "create_blackboard",
        "create_blackboard",
        {"asset_path": f"{ROOT}/BB_FullSmoke", "overwrite": True},
    )
    results["bb_keys"] = step(
        "add_blackboard_keys",
        "add_blackboard_keys",
        {
            "asset_path": f"{ROOT}/BB_FullSmoke",
            "keys": [
                {"name": "TargetActor", "type": "object"},
                {"name": "bReady", "type": "bool"},
            ],
        },
    )
    results["bt"] = step(
        "create_behavior_tree",
        "create_behavior_tree",
        {
            "asset_path": f"{ROOT}/BT_FullSmoke",
            "blackboard_path": f"{ROOT}/BB_FullSmoke",
            "overwrite": True,
        },
    )
    results["wait"] = step(
        "add_behavior_tree_wait_task",
        "add_behavior_tree_wait_task",
        {"asset_path": f"{ROOT}/BT_FullSmoke", "wait_seconds": 0.25},
    )
    results["find"] = step(
        "find_assets",
        "find_assets",
        {"name_contains": "FullSmoke", "path_prefix": ROOT, "limit": 20},
    )
    results["safety"] = step(
        "safety_block",
        "add_beginplay_print",
        {"asset_path": "/Game/Weapons/BP_Pistol", "message": "blocked"},
    )

    nodes = str(results["inspect_bp"].get("nodes", []))
    checks = {
        "list": results["list"].get("success"),
        "bp": results["bp"].get("success"),
        "begin": results["begin"].get("success"),
        "compile": results["compile"].get("success"),
        "inspect_has_print": "PrintString" in nodes,
        "mat": results["mat"].get("success"),
        "widget": results["widget"].get("success"),
        "niagara": results["niagara"].get("success"),
        "bb": results["bb"].get("success"),
        "bb_keys": results["bb_keys"].get("success"),
        "bt": results["bt"].get("success"),
        "wait": results["wait"].get("success"),
        "find": results["find"].get("success") or (results["find"].get("count", 0) >= 1),
        "safety": bool(results["safety"].get("needs_force"))
        or (
            results["safety"].get("success") is False
            and "force" in str(results["safety"]).lower()
        ),
    }
    print("\n=== CHECKS ===")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    ok = all(checks.values())
    print("\n=== FINAL:", "PASS" if ok else "FAIL", "===")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
