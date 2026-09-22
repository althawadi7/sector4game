"""Fix BP_Zombie_Pawn AnimBlueprint / Flinch_Alpha runtime None errors.

Safe to re-run in Unreal Editor Python console.
"""
from __future__ import annotations

import unreal
import cursor_unreal_bridge.blueprint_ops as bo


PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
CAST_PALETTE = "Utilities|Casting|CastToAnimBP_Zombie"


def _save() -> None:
    unreal.EditorAssetLibrary.save_asset(PAWN)


def _cast_out_pin(cast_node) -> object | None:
    bel = bo._bel()
    for pin in bel.list_all_pins(cast_node) or []:
        if str(pin.get_pin_name()) == "AsAnim BP Zombie":
            return pin
    return None


def fix_pawn_flinch_anim() -> None:
    path = PAWN + ".BP_Zombie_Pawn"
    bp = unreal.load_asset(path)
    ed, _ = bo._editor_for(bp, "EventGraph")
    pinlib = bo._pinlib()
    bel = bo._bel()

    get_anim_fn = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_0")
    timeline = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_Timeline_0")
    set_flinch = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_VariableSet_13")
    hd = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_14")
    play25 = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_25")
    cast0 = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_DynamicCast_0")
    delay17 = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_17")
    cast1 = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_DynamicCast_1")
    get_ctrl = next(n for n in ed.list_all_nodes() if n.get_name() == "K2Node_CallFunction_7")

    set_anim18 = next((n for n in ed.list_all_nodes() if n.get_name() == "K2Node_VariableSet_18"), None)
    if set_anim18 is None:
        set_anim18 = ed.add_set_member_variable_node("AnimBlueprint")
        bo._set_node_pos(set_anim18, 3100, 2080)

    cast_tl = next((n for n in ed.list_all_nodes() if n.get_name() == "K2Node_DynamicCast_2"), None)
    if cast_tl is None:
        cast_tl = ed.create_node_from_name(CAST_PALETTE, unreal.Vector2D(3600, 2520), [])
        bo._set_node_pos(cast_tl, 3600, 2520)

    cast_dmg = next((n for n in ed.list_all_nodes() if n.get_name() == "K2Node_DynamicCast_3"), None)
    if cast_dmg is None:
        cast_dmg = ed.create_node_from_name(CAST_PALETTE, unreal.Vector2D(3000, 2080), [])
        bo._set_node_pos(cast_dmg, 3000, 2080)

    anim_inst = bel.find_result_pin(get_anim_fn)
    for cast_node in (cast_tl, cast_dmg):
        obj = bo._find_pin(cast_node, "Object")
        pinlib.break_pin_links(obj)
        pinlib.try_create_connection(anim_inst, obj)

    fail0 = bo._find_pin(cast0, "CastFailed")
    if not pinlib.list_connected_pins(fail0):
        pinlib.try_create_connection(fail0, bel.find_execute_pin(delay17))

    obj1 = bo._find_pin(cast1, "Object")
    if not pinlib.list_connected_pins(obj1):
        pinlib.try_create_connection(bel.find_result_pin(get_ctrl), obj1)

    update_pin = next(p for p in bel.list_all_pins(timeline) or [] if str(p.get_pin_name()) == "Update")
    pinlib.break_pin_links(update_pin)
    pinlib.break_pin_links(bo._find_pin(set_flinch, "execute"))
    pinlib.break_pin_links(bo._find_pin(set_flinch, "self"))
    pinlib.try_create_connection(update_pin, bel.find_execute_pin(cast_tl))
    pinlib.try_create_connection(bel.find_then_pin(cast_tl), bo._find_pin(set_flinch, "execute"))
    out_tl = _cast_out_pin(cast_tl)
    if out_tl:
        pinlib.try_create_connection(out_tl, bo._find_pin(set_flinch, "self"))

    pinlib.break_pin_links(bo._find_pin(hd, "then"))
    pinlib.break_pin_links(bo._find_pin(play25, "execute"))
    pinlib.break_pin_links(bo._find_pin(set_anim18, "execute"))
    pinlib.break_pin_links(bo._find_pin(set_anim18, "AnimBlueprint"))
    pinlib.try_create_connection(bo._find_pin(hd, "then"), bel.find_execute_pin(cast_dmg))
    pinlib.try_create_connection(bel.find_then_pin(cast_dmg), bo._find_pin(set_anim18, "execute"))
    out_dmg = _cast_out_pin(cast_dmg)
    if out_dmg:
        pinlib.try_create_connection(out_dmg, bo._find_pin(set_anim18, "AnimBlueprint"))
    pinlib.try_create_connection(bo._find_pin(set_anim18, "then"), bo._find_pin(play25, "execute"))
    pinlib.try_create_connection(bo._find_pin(cast_dmg, "CastFailed"), bo._find_pin(play25, "execute"))

    bel.compile_blueprint(bp)
    _save()


def main() -> None:
    fix_pawn_flinch_anim()
    unreal.log("fix_zombie_pawn_flinch: done")


if __name__ == "__main__":
    main()
