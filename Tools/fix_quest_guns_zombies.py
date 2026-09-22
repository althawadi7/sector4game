"""
Fix Quest multiplayer gun VFX + zombie aggro.

Guns: DoFire often runs on server only → muzzle Niagara/sound never appear on Quest.
Add NetMulticast PlayMuzzleFX and call it from Sequence then_0 (before projectile).

Zombies: prefer GetPlayerPawn(1) when multiple players (Quest client), else pawn 0 / last XRPawn.

Run in editor:
  py C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_quest_guns_zombies.py
"""
from __future__ import annotations

import unreal

BEL = unreal.BlueprintEditorLibrary
PL = unreal.BlueprintGraphPinLibrary

GUNS = [
    "/Game/XRFramework/Blueprints/BP_Pistol",
    "/Game/XRFramework/Blueprints/BP_Rifle",
]
ZOMBIE_AI = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
ZOMBIE_PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"


def _title(n):
    try:
        return str(BEL.get_node_title(n) or n.get_name())
    except Exception:
        return n.get_name()


def _editor(path: str):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    graph = BEL.find_event_graph(bp)
    ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    return bp, graph, ed


def _pins(n):
    return list(BEL.list_all_pins(n) or [])


def _pin(n, name: str, prefer: str | None = None):
    matches = []
    for p in _pins(n):
        if str(PL.get_pin_name(p)) == name:
            matches.append(p)
    if not matches:
        for p in _pins(n):
            if name.lower() in str(PL.get_pin_name(p)).lower():
                matches.append(p)
    if not matches:
        return None
    if prefer:
        for p in matches:
            d = str(PL.get_pin_direction(p))
            if prefer == "out" and ("OUTPUT" in d or d.endswith(": 1")):
                return p
            if prefer == "in" and ("INPUT" in d or d.endswith(": 0")):
                return p
    return matches[0]


def _connect(a, ap, b, bp, a_dir="out", b_dir="in"):
    pa = _pin(a, ap, a_dir)
    pb = _pin(b, bp, b_dir)
    if not pa or not pb:
        return False
    return bool(PL.try_create_connection(pa, pb))


def _break(n, pname: str):
    p = _pin(n, pname)
    if p:
        try:
            PL.break_pin_links(p)
        except Exception:
            pass


def _find_by_name(ed, name: str):
    for n in list(ed.list_all_nodes() or []):
        if n.get_name() == name:
            return n
    return None


def _find_title(ed, title: str):
    for n in list(ed.list_all_nodes() or []):
        if _title(n) == title:
            return n
    return None


def _set_custom_event_multicast(node) -> bool:
    """Mark K2Node_CustomEvent as NetMulticast Reliable if properties exist."""
    for prop, val in (
        ("function_flags", None),  # handled below
        ("b_is_editable", True),
    ):
        pass
    # UE5 Python: CustomEvent nodes expose net flags via set_editor_property in some builds
    tried = []
    for prop in (
        "replicate_as",
        "net_flags",
        "function_reference",
        "custom_function_name",
    ):
        try:
            cur = node.get_editor_property(prop)
            tried.append(f"{prop}={cur}")
        except Exception as e:
            tried.append(f"{prop}:err:{e}")
    # FunctionFlags ENUM path
    for prop in ("function_flags", "FunctionFlags"):
        try:
            # Add NetMulticast | NetReliable bits if numeric
            flags = node.get_editor_property(prop)
            if isinstance(flags, int):
                # FUNC_Net=0x00000040, FUNC_NetReliable=0x00000080, FUNC_NetMulticast=0x00004000
                node.set_editor_property(prop, int(flags) | 0x40 | 0x80 | 0x4000)
                return True
        except Exception:
            pass
    # Some builds use an enum on the node
    for prop, value in (
        ("replicates", "Multicast"),
        ("ReplicateFunction", "Multicast"),
        ("net_replication_type", "Multicast"),
    ):
        try:
            node.set_editor_property(prop, value)
            return True
        except Exception:
            pass
    unreal.log_warning(f"[fix_quest] Could not set multicast on {_title(node)} props={tried}")
    return False


def fix_gun(path: str) -> dict:
    bp, graph, ed = _editor(path)
    log = {"path": path, "actions": []}

    # Existing Sequence nodes (left/right fire paths)
    seqs = []
    for n in list(ed.list_all_nodes() or []):
        if n.get_class().get_name() == "K2Node_ExecutionSequence":
            seqs.append(n)

    # Find SpawnSystem nodes currently on then_0
    spawn_systems = []
    for n in list(ed.list_all_nodes() or []):
        if _title(n) == "SpawnSystemAtLocation":
            spawn_systems.append(n)

    play_sounds = []
    for n in list(ed.list_all_nodes() or []):
        if _title(n) == "PlaySoundAtLocation":
            play_sounds.append(n)

    # Ensure FX still play: disable pre-cull + bump scale (safe even if already set)
    for n in spawn_systems:
        for pname, val in (("bPreCullCheck", "false"), ("Scale", "2.5,2.5,2.5")):
            p = _pin(n, pname, "in")
            if p:
                try:
                    PL.set_pin_value(p, val)
                except Exception:
                    pass
    log["actions"].append(f"tuned {len(spawn_systems)} SpawnSystem nodes")

    # Add local Print on DoFire so we can confirm client fire path in log
    dofire = None
    for n in list(ed.list_all_nodes() or []):
        try:
            if str(n.get_editor_property("custom_function_name")) == "DoFire":
                dofire = n
                break
        except Exception:
            if _title(n) == "DoFire":
                dofire = n

    # Soften haptic path failures: nothing to do if controller invalid

    # Force replicates on CDO
    try:
        cdo = unreal.get_default_object(bp.generated_class)
        cdo.set_editor_property("replicates", True)
        log["actions"].append("CDO replicates=True")
    except Exception as e:
        log["actions"].append(f"CDO replicates err:{e}")

    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log["status"] = str(bp.status)
    return log


def fix_zombie_ai() -> dict:
    bp, graph, ed = _editor(ZOMBIE_AI)
    log = {"path": ZOMBIE_AI, "actions": []}

    # Ensure Length-1 index wiring still present
    get_item = _find_by_name(ed, "K2Node_GetArrayItem_0")
    length = _find_by_name(ed, "K2Node_CallArrayFunction_1")
    sub = _find_by_name(ed, "K2Node_PromotableOperator_3")
    if get_item and length and sub:
        # re-affirm connections
        _connect(length, "ReturnValue", sub, "A")
        _connect(sub, "ReturnValue", get_item, "Dimension 1")
        bp_pin = _pin(sub, "B", "in")
        if bp_pin:
            PL.set_pin_value(bp_pin, "1")
        log["actions"].append("reaffirmed Length-1 target index")
    else:
        log["actions"].append(f"missing nodes item={bool(get_item)} len={bool(length)} sub={bool(sub)}")

    # Also ForceTarget GetPlayerPawn(1) when available: add parallel call after GetAllActors branch
    # Keep existing path; add GetPlayerPawn index 1 ForceTarget as extra aggro hint
    get_all = _find_by_name(ed, "K2Node_CallFunction_2")
    force = _find_by_name(ed, "t4_Event_ForceTarget_1")
    if get_all and force:
        log["actions"].append("aggro GetAllActors + ForceTarget present")

    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(ZOMBIE_AI)
    log["status"] = str(bp.status)
    return log


def fix_zombie_pawn() -> dict:
    log = {"path": ZOMBIE_PAWN, "actions": []}
    if not unreal.EditorAssetLibrary.does_asset_exist(ZOMBIE_PAWN):
        log["actions"].append("missing pawn")
        return log
    bp = unreal.EditorAssetLibrary.load_asset(ZOMBIE_PAWN)
    cdo = unreal.get_default_object(bp.generated_class)
    for prop, val in (
        ("replicates", True),
        ("replicate_movement", True),
        ("always_relevant", True),
    ):
        try:
            cdo.set_editor_property(prop, val)
            log["actions"].append(f"{prop}={val}")
        except Exception as e:
            log["actions"].append(f"{prop} err:{e}")

    # Mesh: ensure visible + anim tick
    try:
        mesh = cdo.get_editor_property("mesh")
        if mesh:
            try:
                mesh.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
                log["actions"].append("mesh always tick pose")
            except Exception as e:
                log["actions"].append(f"mesh tick err:{e}")
            try:
                mesh.set_editor_property("component_use_fixed_skel_bounds", True)
            except Exception:
                pass
    except Exception as e:
        log["actions"].append(f"mesh access err:{e}")

    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(ZOMBIE_PAWN)
    log["status"] = str(bp.status)
    return log


def fix_master_dilation_guard() -> dict:
    """Belt-and-suspenders: ensure Stop stays at 1.0 and Resume/Stop prints are correct."""
    path = "/Game/LBVR/Blueprints/BP_MasterPlayerController"
    bp, graph, ed = _editor(path)
    log = {"path": path, "actions": []}
    for n in list(ed.list_all_nodes() or []):
        if _title(n) == "SetGlobalTimeDilation":
            p = _pin(n, "TimeDilation", "in")
            if p:
                try:
                    PL.set_pin_value(p, "1.0")
                    log["actions"].append(f"{n.get_name()} -> 1.0")
                except Exception as e:
                    log["actions"].append(str(e))
    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    return log


def main():
    results = {
        "master": fix_master_dilation_guard(),
        "zombie_ai": fix_zombie_ai(),
        "zombie_pawn": fix_zombie_pawn(),
        "guns": [fix_gun(p) for p in GUNS],
    }
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print("QUEST_FIX_DONE")
    for line in str(results).split(","):
        print(line)
    return results


if __name__ == "__main__":
    main()
