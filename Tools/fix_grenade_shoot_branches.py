"""Wire IA_Shoot branches on BP_GrenadeLauncher (condition was disconnected).

Run in Unreal:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_grenade_shoot_branches.py"
"""
from __future__ import annotations

import unreal
import cursor_unreal_bridge.blueprint_ops as bo

PATH = "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"


def main() -> None:
    bp = unreal.load_asset(PATH + ".BP_GrenadeLauncher")
    ed, _ = bo._editor_for(bp, "EventGraph")
    pinlib = bo._pinlib()

    get_can = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Get bCanFire":
            get_can = n
            break
    if get_can is None:
        get_can = ed.add_get_member_variable_node("bCanFire")
        bo._set_node_pos(get_can, 2400, 520)

    can_pin = bo._find_pin(get_can, "bCanFire", prefer_direction="output") or next(
        p for p in bo._bel().list_all_pins(get_can) or [] if str(p.get_pin_name()) != "self"
    )

    for name in ("K2Node_IfThenElse_20", "K2Node_IfThenElse_21"):
        br = next(n for n in ed.list_all_nodes() if n.get_name() == name)
        cond = bo._find_pin(br, "Condition")
        pinlib.break_pin_links(cond)
        pinlib.try_create_connection(can_pin, cond)

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(PATH)
    unreal.log("fix_grenade_shoot_branches: wired bCanFire to shoot branches.")


if __name__ == "__main__":
    main()
