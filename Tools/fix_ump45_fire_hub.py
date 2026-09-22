"""Wire FireWeapon hub + IA + poll + timer. Run via execute_unreal_python exec."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

POLL = "PollReload"
bp = unreal.load_asset("/Game/GunVR/BP_GunVR_UMP45.BP_GunVR_UMP45")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(a, b):
    return pl.try_create_connection(a, b) if a and b else False


spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.break_pin_links(spawn_exec)

fire = bo._find_node(ed, "FireWeapon")
if not fire:
    fire = ed.add_custom_event_node("FireWeapon")
    bo._set_node_pos(fire, 1600, 200)
link(p(fire, "then", True), spawn_exec)

poll = bo._find_node(ed, POLL)
br_poll = None
for n in ed.list_all_nodes() or []:
    if bo._node_title(n) == "Branch":
        ex = bel.find_execute_pin(n)
        for pin in pl.list_connected_pins(ex) or []:
            if pin.get_owning_node() == poll:
                br_poll = n
                break

if br_poll:
    pl.break_pin_links(bel.find_then_pin(br_poll))
    link(bel.find_then_pin(br_poll), p(fire, "then", True))
    ex = bel.find_execute_pin(br_poll)
    pl.break_pin_links(ex)
    link(p(poll, "then", True), ex)

for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
    br = bo._find_node(ed, br_id)
    if br:
        pl.break_pin_links(bel.find_then_pin(br))
        pl.break_pin_links(bel.find_execute_pin(br))
        link(bel.find_then_pin(br), p(fire, "then", True))

ia1 = bo._find_node(ed, "K2Node_EnhancedInputAction_1")
ia2 = bo._find_node(ed, "K2Node_EnhancedInputAction_2")
br0 = bo._find_node(ed, "K2Node_IfThenElse_0")
br1 = bo._find_node(ed, "K2Node_IfThenElse_1")
print("IA1->br0", link(p(ia1, "Triggered", True), bel.find_execute_pin(br0)))
print("IA2->br1", link(p(ia2, "Triggered", True), bel.find_execute_pin(br1)))

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("status", bp.status)
unreal.EditorAssetLibrary.save_asset("/Game/GunVR/BP_GunVR_UMP45")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

spawn_ins = pl.list_connected_pins(spawn_exec) or []
print("spawn from", [bo._node_title(x.get_owning_node()) for x in spawn_ins])
fire_out = pl.list_connected_pins(p(fire, "then", True)) or []
print("fire->", [bo._node_title(x.get_owning_node()) for x in fire_out])

n = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
for i in range(6):
    then = bel.find_then_pin(n)
    dest = [bo._node_title(c.get_owning_node()) for c in (pl.list_connected_pins(then) or [])]
    print(bo._node_title(n), "->", dest)
    if not pl.list_connected_pins(then):
        break
    n = pl.list_connected_pins(then)[0].get_owning_node()
