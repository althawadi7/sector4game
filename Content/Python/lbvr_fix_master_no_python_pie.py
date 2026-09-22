"""
Disable ExecutePython on Master PC PlayerController so PIE no longer asserts.
Run via: UnrealEditor-Cmd.exe sector4v2.uproject -ExecutePythonScript=<this> -unattended
"""
from __future__ import annotations

import unreal


ASSET = "/Game/LBVR/Blueprints/BP_MasterPlayerController"


def _log(msg: str) -> None:
    unreal.log(f"[LBVR_FIX] {msg}")


def main() -> None:
    bp = unreal.EditorAssetLibrary.load_asset(ASSET)
    if not bp:
        unreal.log_error(f"[LBVR_FIX] missing {ASSET}")
        return

    # Soft-compile path: strip PythonCommand pins to empty / harmless, and
    # prefer removing exec links into ExecutePythonCommand nodes via Editor API.
    try:
        graphs = unreal.BlueprintEditorLibrary.get_all_graphs(bp)
    except Exception as e:
        _log(f"get_all_graphs failed: {e}")
        graphs = []

    removed = 0
    neutralized = 0
    for g in graphs or []:
        try:
            nodes = g.get_editor_property("nodes")
        except Exception:
            continue
        for node in nodes or []:
            try:
                title = str(node.get_class().get_name())
            except Exception:
                title = ""
            # K2Node_CallFunction named ExecutePythonCommand
            is_py = False
            try:
                if hasattr(node, "get_editor_property"):
                    fn = None
                    try:
                        fn = node.get_editor_property("function_reference")
                    except Exception:
                        pass
                    # Fallback: pin named PythonCommand
                    for pin in node.get_editor_property("pins") or []:
                        try:
                            if str(pin.get_editor_property("pin_name")) == "PythonCommand":
                                is_py = True
                                # Neutralize command text so accidental fires are no-ops
                                pin.set_editor_property("default_value", "print('[MASTER] python disabled')")
                                neutralized += 1
                        except Exception:
                            pass
            except Exception:
                pass

            if is_py:
                # Break incoming exec
                try:
                    for pin in node.get_editor_property("pins") or []:
                        pname = str(pin.get_editor_property("pin_name"))
                        if pname == "execute" and pin.get_editor_property("linked_to"):
                            # break_all_pin_links if available
                            try:
                                pin.break_all_pin_links(True)
                                removed += 1
                            except Exception:
                                pass
                except Exception:
                    pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    ok = unreal.EditorAssetLibrary.save_asset(ASSET, only_if_is_dirty=False)
    _log(f"done neutralized={neutralized} broken_links={removed} saved={ok}")


if __name__ == "__main__":
    main()
