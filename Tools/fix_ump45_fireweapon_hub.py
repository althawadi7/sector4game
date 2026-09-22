"""Fix spawn hub via FireWeapon call — few nodes, one compile."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def L(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


bp = unreal.load_asset(GUN + ".BP_GunVR_UMP45")
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.break_pin_links(spawn_exec)

fire_evt = bo._find_node(ed, "FireWeapon")
if not fire_evt:
    fire_evt = ed.add_custom_event_node("FireWeapon")
    bo._set_node_pos(fire_evt, 1500, 100)
L(pl, p(fire_evt, "then", True), spawn_exec)

call1 = ed.add_call_function_node("FireWeapon")
bo._set_node_pos(call1, 1400, 300)
call2 = ed.add_call_function_node("FireWeapon")
bo._set_node_pos(call2, 1400, 500)

br0 = bo._find_node(ed, "K2Node_IfThenElse_0")
br1 = bo._find_node(ed, "K2Node_IfThenElse_1")
if br0:
    pl.break_pin_links(bel.find_then_pin(br0))
    L(pl, bel.find_then_pin(br0), bel.find_execute_pin(call1))
if br1:
    pl.break_pin_links(bel.find_then_pin(br1))
    L(pl, bel.find_then_pin(br1), bel.find_execute_pin(call2))

ia1 = bo._find_node(ed, "K2Node_EnhancedInputAction_1")
ia2 = bo._find_node(ed, "K2Node_EnhancedInputAction_2")
if ia1 and br0:
    pl.break_pin_links(bel.find_execute_pin(br0))
    L(pl, p(ia1, "Triggered", True), bel.find_execute_pin(br0))
if ia2 and br1:
    pl.break_pin_links(bel.find_execute_pin(br1))
    L(pl, p(ia2, "Triggered", True), bel.find_execute_pin(br1))

# poll branch if exists -> call fire
poll = bo._find_node(ed, "PollReload")
if poll:
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Branch":
            ex = bel.find_execute_pin(n)
            for pin in pl.list_connected_pins(ex) or []:
                if pin.get_owning_node() == poll:
                    pl.break_pin_links(bel.find_then_pin(n))
                    call3 = ed.add_call_function_node("FireWeapon")
                    L(pl, bel.find_then_pin(n), bel.find_execute_pin(call3))
                    break

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("STATUS", bp.status)
if bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE:
    unreal.EditorAssetLibrary.save_asset(GUN)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
spawn_in = [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(spawn_exec) or [])]
print("spawn<-", spawn_in)
