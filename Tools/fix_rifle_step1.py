"""Step 1: BP_Rifle — clear broken poll branch condition only."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
PATH = "/Game/XRFramework/Blueprints/BP_Rifle"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


bp = unreal.load_asset(PATH + ".BP_Rifle")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()
poll = bo._find_node(ed, POLL)
br = None
for n in ed.list_all_nodes() or []:
    if bo._node_title(n) != "Branch":
        continue
    ex = bel.find_execute_pin(n)
    for pin in pl.list_connected_pins(ex) or []:
        if pin.get_owning_node() == poll:
            br = n
            break
if br:
    pl.break_pin_links(p(br, "Condition"))
    unreal.log("BP_Rifle step1: old condition cleared")
unreal.EditorAssetLibrary.save_asset(PATH)
unreal.log("BP_Rifle step1 saved")
