"""Full VIP Blueprint power smoke test against CursorUnrealBridge."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:27182"
BP = "/Game/CursorTest/BP_VipAgentFinal"


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


def wait_ready(max_wait: float = 180) -> dict:
    start = time.time()
    last = None
    while time.time() - start < max_wait:
        try:
            health = _get("/health", timeout=3)
            if health.get("ok"):
                try:
                    status = _get("/status", timeout=15)
                    if status.get("ok") or status.get("bridge"):
                        return {"ready": True, "health": health, "status": status}
                    last = status
                except Exception as exc:
                    last = {"status_err": str(exc)}
        except Exception as exc:
            last = {"health_err": str(exc)}
        time.sleep(2)
    return {"ready": False, "last": last}


def main() -> int:
    print("Waiting for bridge (run py.file restart in Unreal if needed)...")
    ready = wait_ready()
    print("READY:", json.dumps(ready, indent=2, default=str)[:800])
    if not ready.get("ready"):
        print("FAIL: bridge not ready")
        return 1

    results = {}

    results["create"] = _cmd(
        "create_blueprint",
        {"asset_path": BP, "parent_class": "Actor", "overwrite": True},
    )
    print("CREATE:", results["create"].get("success"), results["create"].get("status"))

    results["variable"] = _cmd(
        "add_blueprint_variable",
        {"asset_path": BP, "var_name": "VipReady", "var_type": "bool"},
    )
    print("VAR:", results["variable"].get("success"), results["variable"])

    results["beginplay"] = _cmd(
        "add_beginplay_print",
        {"asset_path": BP, "message": "VIP AGENT BLUEPRINT POWER ONLINE"},
    )
    print(
        "BEGINPLAY:",
        results["beginplay"].get("success"),
        json.dumps(results["beginplay"], default=str)[:500],
    )

    results["pin"] = _cmd(
        "set_blueprint_pin_defaults",
        {
            "asset_path": BP,
            "updates": [
                {
                    "node": "PrintString",
                    "pin": "InString",
                    "value": "VIP AGENT BLUEPRINT POWER ONLINE",
                }
            ],
        },
    )
    print("PIN:", results["pin"].get("success"), results["pin"])

    results["compile"] = _cmd("compile_blueprint", {"asset_path": BP})
    print("COMPILE:", results["compile"].get("success"), results["compile"].get("status"))

    results["inspect"] = _cmd("inspect_blueprint", {"asset_path": BP})
    nodes = [n.get("title") for n in results["inspect"].get("nodes", [])]
    print("INSPECT nodes:", nodes)
    print("INSPECT status:", results["inspect"].get("status"))

    results["actors"] = _cmd("list_actors", {"label_filter": "Cursor"})
    print("ACTORS:", results["actors"].get("count"), "matching Cursor*")

    ok = all(
        [
            results["create"].get("success"),
            results["beginplay"].get("success"),
            results["compile"].get("success"),
            results["inspect"].get("success"),
            "PrintString" in str(nodes),
            "BeginPlay" in str(nodes) or "Event BeginPlay" in str(nodes),
        ]
    )
    print("\n=== FINAL:", "PASS" if ok else "FAIL", "===")
    print(json.dumps({k: v for k, v in results.items() if k != "inspect"}, indent=2, default=str)[:2000])
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
