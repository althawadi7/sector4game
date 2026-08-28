"""Smoke test: materials / widgets / Niagara / BT / safety (CursorUnrealBridge)."""

from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:27182"
ROOT = "/Game/CursorTest"


def _get(path: str, timeout: float = 20) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _cmd(command: str, args: dict | None = None, timeout: float = 90) -> dict:
    data = json.dumps({"command": command, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/command",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(max_wait: float = 180) -> bool:
    start = time.time()
    while time.time() - start < max_wait:
        try:
            st = _get("/status", timeout=5)
            cmds = st.get("commands") or []
            if st.get("ok") and "create_material" in cmds:
                print("READY:", json.dumps({k: st.get(k) for k in ("ok", "bridge", "aura_extras", "engine")}, default=str))
                return True
        except Exception as exc:
            print("wait:", exc)
        time.sleep(2)
    return False


def main() -> int:
    print("Waiting for bridge (run restart_bridge.py in Unreal if needed)...")
    if not wait_ready():
        print("FAIL: bridge not ready")
        return 1

    results = {}
    results["material"] = _cmd(
        "create_material",
        {
            "asset_path": f"{ROOT}/M_AuraExtraTest",
            "base_color": [1.0, 0.2, 0.1, 1.0],
            "overwrite": True,
        },
    )
    print("MATERIAL:", results["material"].get("success"), results["material"].get("error"))

    results["widget"] = _cmd(
        "create_widget_blueprint",
        {"asset_path": f"{ROOT}/WBP_AuraExtraTest", "overwrite": True},
    )
    print("WIDGET:", results["widget"].get("success"), results["widget"].get("error"))

    results["niagara"] = _cmd(
        "create_niagara_system",
        {"asset_path": f"{ROOT}/NS_AuraExtraTest", "overwrite": True},
    )
    print("NIAGARA:", results["niagara"].get("success"), results["niagara"].get("error"))

    results["bb"] = _cmd(
        "create_blackboard",
        {"asset_path": f"{ROOT}/BB_AuraExtraTest", "overwrite": True},
    )
    results["bb_keys"] = _cmd(
        "add_blackboard_keys",
        {
            "asset_path": f"{ROOT}/BB_AuraExtraTest",
            "keys": [
                {"name": "TargetActor", "type": "object"},
                {"name": "bReady", "type": "bool"},
            ],
        },
    )
    print(
        "BLACKBOARD:",
        results["bb"].get("success"),
        results["bb_keys"].get("success"),
        results["bb_keys"].get("error"),
    )

    results["bt"] = _cmd(
        "create_behavior_tree",
        {
            "asset_path": f"{ROOT}/BT_AuraExtraTest",
            "blackboard_path": f"{ROOT}/BB_AuraExtraTest",
            "overwrite": True,
        },
    )
    results["wait"] = _cmd(
        "add_behavior_tree_wait_task",
        {"asset_path": f"{ROOT}/BT_AuraExtraTest", "wait_seconds": 0.5},
    )
    print("BT:", results["bt"].get("success"), results["wait"].get("success"), results["wait"].get("error"))

    results["safety"] = _cmd(
        "add_beginplay_print",
        {"asset_path": "/Game/Weapons/BP_Pistol", "message": "should block"},
    )
    blocked = bool(results["safety"].get("needs_force")) or (
        results["safety"].get("success") is False
        and "force" in str(results["safety"]).lower()
    )
    print("SAFETY:", results["safety"])

    results["find"] = _cmd(
        "find_assets",
        {"name_contains": "AuraExtra", "path_prefix": ROOT, "limit": 20},
    )
    print("FIND:", results["find"].get("count"), results["find"].get("error"))

    ok = all(
        [
            results["material"].get("success"),
            results["widget"].get("success"),
            results["niagara"].get("success"),
            results["bb"].get("success"),
            results["bb_keys"].get("success"),
            results["bt"].get("success"),
            results["wait"].get("success"),
            blocked,
        ]
    )
    print("\n=== FINAL:", "PASS" if ok else "FAIL", "===")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
