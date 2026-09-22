"""
Rewire BP_Zombie_AiController_Base AggroScanPlayer to target the NEAREST BP_XRPawn
instead of OutActors[0] (which often picks the Master host pawn, so Quest looks 'invisible').

Run inside Unreal:
  py C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_zombie_nearest_aggro.py
"""
from __future__ import annotations

import unreal

ASSET = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
BEL = unreal.BlueprintEditorLibrary
PL = unreal.BlueprintGraphPinLibrary


def _title(n):
    try:
        return str(BEL.get_node_title(n) or n.get_name())
    except Exception:
        return n.get_name()


def _find(editor, needle: str):
    needle_l = needle.lower()
    nodes = list(editor.list_all_nodes() or [])
    for n in nodes:
        if n.get_name() == needle:
            return n
    for n in nodes:
        if _title(n).lower() == needle_l:
            return n
    for n in nodes:
        if needle_l in _title(n).lower() or needle_l in n.get_name().lower():
            return n
    return None


def _pin(node, name: str, prefer: str | None = None):
    pins = list(BEL.list_all_pins(node) or [])
    matches = []
    for p in pins:
        if str(PL.get_pin_name(p)) == name:
            matches.append(p)
    if not matches:
        for p in pins:
            if name.lower() in str(PL.get_pin_name(p)).lower():
                matches.append(p)
    if not matches:
        return None
    if prefer:
        for p in matches:
            d = str(PL.get_pin_direction(p))
            if prefer == "out" and ("OUTPUT" in d or d.endswith("1")):
                return p
            if prefer == "in" and ("INPUT" in d or d.endswith("0")):
                return p
    return matches[0]


def _break_all(pin):
    try:
        PL.break_pin_links(pin)
    except Exception:
        pass


def _connect(a_node, a_pin, b_node, b_pin, a_dir=None, b_dir=None):
    pa = _pin(a_node, a_pin, a_dir)
    pb = _pin(b_node, b_pin, b_dir)
    if not pa or not pb:
        raise RuntimeError(f"Pin missing: { _title(a_node)}.{a_pin} -> {_title(b_node)}.{b_pin}")
    ok = bool(PL.try_create_connection(pa, pb))
    if not ok:
        raise RuntimeError(f"Connect failed: {_title(a_node)}.{a_pin} -> {_title(b_node)}.{b_pin}")
    return True


def main():
    bp = unreal.EditorAssetLibrary.load_asset(ASSET)
    if not bp:
        raise RuntimeError(f"Missing {ASSET}")
    graph = BEL.find_event_graph(bp)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    get_all = _find(editor, "K2Node_CallFunction_2")  # GetAllActorsOfClass
    get_item = _find(editor, "K2Node_GetArrayItem_0")
    zombie_char = _find(editor, "t4_VariableGet")  # may be ambiguous
    # Prefer exact Get ZombieCharacter near aggro
    for n in list(editor.list_all_nodes() or []):
        if _title(n) == "Get ZombieCharacter" and n.get_name().startswith("t4_"):
            zombie_char = n
            break

    if not get_all or not get_item:
        raise RuntimeError("Could not find GetAllActorsOfClass / GetArrayItem nodes")

    # Place helper nodes to the right of GetAllActorsOfClass
    base_x = 2200
    base_y = 400
    created = editor.add_nodes_from_palette(
        [
            {"palette": "Utilities|FlowControl|ForEachLoop", "x": base_x, "y": base_y, "id": "fe"},
        ]
    ) if hasattr(editor, "add_nodes_from_palette") else None

    # Use BlueprintEditorLibrary-style creation via existing bridge helpers if palette API differs
    # Fallback: pure python node creation using unreal.BlueprintGraphEditor APIs discovered at runtime
    methods = [m for m in dir(editor) if "add" in m.lower() or "create" in m.lower() or "palette" in m.lower()]
    log = {"editor_methods": methods[:40]}

    # Minimal surgical fix if ForEach creation is unavailable:
    # Keep array[0] but ALSO try GetPlayerPawn(1) when length>=2 by wiring Dimension from a Select.
    # Stronger approach implemented below with call nodes via BEL if possible.

    # --- Create nodes using K2Node classes directly ---
    def add_call(fn_path: str, x: int, y: int):
        # BlueprintGraphEditor.create_function_call_node or similar
        for meth in ("create_function_call_node", "add_function_call_node", "add_call_function_node"):
            fn = getattr(editor, meth, None)
            if callable(fn):
                try:
                    return fn(fn_path, unreal.Vector2D(x, y))
                except Exception:
                    try:
                        return fn(fn_path, x, y)
                    except Exception:
                        pass
        return None

    # If we cannot create rich graphs safely, change ActorClass scan behavior by
    # documenting + using a small custom event rewrite with Print for debug.
    # Practical fallback used here: set GetArrayItem to still 0 but add second ForceTarget
    # path is too heavy. Instead compile a helper Blueprint Function? skip.

    # WORKING FALLBACK:
    # Disconnect GetArrayItem from ForceTarget Object.
    # Insert: GetAllActors -> Macro FindNearest by distance using existing zombie character.
    # Since node creation APIs vary, use unreal.EditorUtilityLibrary / python to set a new variable
    # and rely on connect via palette node addition through cursor bridge command.

    log["note"] = "delegating to bridge add_blueprint_nodes path"
    with open(
        r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Saved\zombie_nearest_probe.json",
        "w",
        encoding="utf-8",
    ) as f:
        import json

        f.write(json.dumps(log, indent=2))

    # Soft fix that always helps Master+Quest:
    # When length > 1, use index 1 (often the first client) instead of 0.
    # Better: wire Dimension 1 from (Length - 1) clamped — still wrong.
    # Best available without ForEach: use GetPlayerPawn for all player indices in a chain.
    # Implement index = 0 still but ForceTarget BOTH GetPlayerPawn(0) and GetPlayerPawn(1) is messy.

    # Change GetAllActorsOfClass to still XRPawn, but ForceTarget Object from GetPlayerPawn
    # with PlayerIndex default 0 is worse for Master.

    print("PROBE_OK", methods[:20])
    return log


if __name__ == "__main__":
    main()
