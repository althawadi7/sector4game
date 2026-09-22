"""Grenade step 2b-WIRE: OR left+right AND -> poll branch. Compile once."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
PATH = "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


bp = unreal.load_asset(PATH + ".BP_GrenadeLauncher")
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
if not br:
    unreal.log_error("no poll branch")
else:
    cond = p(br, "Condition")
    and_l = None
    and_r = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) != "AND Boolean":
            continue
        rv = p(n, "ReturnValue", True)
        pins = pl.list_connected_pins(rv) or []
        if cond in pins:
            and_l = n
        elif not pins:
            and_r = n
    if not and_l:
        unreal.log_error("no left AND found")
    elif not and_r:
        unreal.log_error("run step2b-ADD first")
    else:
        pl.break_pin_links(cond)
        or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
        bo._set_node_pos(or_n, 1550, 1040)
        link(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
        link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
        ok = link(pl, p(or_n, "ReturnValue", True), cond)
        unreal.log("grenade step2b-WIRE ok=" + str(ok))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.log("compile " + str(bp.status))

unreal.EditorAssetLibrary.save_asset(PATH)
unreal.log("grenade step2b-WIRE saved")
