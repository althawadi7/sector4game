"""Ultra-minimal: reconnect existing nodes only. No new nodes. One compile."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"


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

# hand branches -> spawn
for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
    br = bo._find_node(ed, br_id)
    if br:
        pl.break_pin_links(bel.find_then_pin(br))
        L(pl, bel.find_then_pin(br), spawn_exec)

# IA -> hand branch execute
ia1 = bo._find_node(ed, "K2Node_EnhancedInputAction_1")
ia2 = bo._find_node(ed, "K2Node_EnhancedInputAction_2")
br0 = bo._find_node(ed, "K2Node_IfThenElse_0")
br1 = bo._find_node(ed, "K2Node_IfThenElse_1")
if ia1 and br0:
    pl.break_pin_links(bel.find_execute_pin(br0))
    L(pl, p(ia1, "Triggered", True), bel.find_execute_pin(br0))
if ia2 and br1:
    pl.break_pin_links(bel.find_execute_pin(br1))
    L(pl, p(ia2, "Triggered", True), bel.find_execute_pin(br1))

# grab chain: ensure add mapping options + break printstring
add = bo._find_node(ed, "K2Node_CallFunction_13")
sel = bo._find_node(ed, "K2Node_Select_1")
if sel and add:
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    pl.break_pin_links(p(add, "MappingContext"))
    L(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")
    pl.break_pin_links(bel.find_then_pin(add))

for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
    path = "/Game/XRFramework/Input/Actions/" + name
    ia = unreal.load_asset(path + "." + name)
    if ia:
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t]
        if not triggers:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("STATUS", bp.status)
spawn_in = [bo._node_title(x.get_owning_node()) for x in (pl.list_connected_pins(spawn_exec) or [])]
print("spawn<-", spawn_in)
print("IA1->br0", pl.list_connected_pins(bel.find_execute_pin(br0)) if br0 else None)
if bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE:
    unreal.EditorAssetLibrary.save_asset(GUN)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
