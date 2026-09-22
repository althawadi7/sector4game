"""ONE rebuild + minimal shoot fix. Single compile at end."""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"
PISTOL = "/Game/XRFramework/Blueprints/BP_Pistol"
UMP_MESH = "/Game/Weapons/UMP45/Mesh/StaticMesh/SM_UMP45"
PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
POLL = "PollReload"
KEY_L = "OculusTouch_Left_Trigger_Click"
KEY_R = "OculusTouch_Right_Trigger_Click"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def L(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


# fresh duplicate
if unreal.EditorAssetLibrary.does_asset_exist(GUN):
    unreal.EditorAssetLibrary.delete_asset(GUN)
unreal.EditorAssetLibrary.duplicate_asset(PISTOL, GUN)
bp = unreal.load_asset(GUN)
mesh = unreal.load_asset(UMP_MESH)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    data = sub.k2_find_subobject_data_from_handle(h)
    name = str(lib.get_variable_name(data) or "")
    obj = lib.get_object(data)
    if isinstance(obj, unreal.StaticMeshComponent) and name in ("SM_Pistol", "GunMesh", "Mesh"):
        obj.set_static_mesh(mesh)
        obj.set_editor_property("relative_scale3d", unreal.Vector(0.85, 0.85, 0.85))

ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
bel = bo._bel()

spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
spawn_exec = bel.find_execute_pin(spawn)
pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
pl.break_pin_links(spawn_exec)

# FireWeapon hub
fire_evt = ed.add_custom_event_node("FireWeapon")
bo._set_node_pos(fire_evt, 1500, 50)
L(pl, p(fire_evt, "then", True), spawn_exec)

call_l = ed.add_call_function_node("FireWeapon")
call_r = ed.add_call_function_node("FireWeapon")
self_n = bo._find_node(ed, "K2Node_Self_0")
if self_n:
    L(pl, p(self_n, "self", True), p(call_l, "self"))
    L(pl, p(self_n, "self", True), p(call_r, "self"))

br0 = bo._find_node(ed, "K2Node_IfThenElse_0")
br1 = bo._find_node(ed, "K2Node_IfThenElse_1")
if br0:
    pl.break_pin_links(bel.find_then_pin(br0))
    L(pl, bel.find_then_pin(br0), bel.find_execute_pin(call_l))
if br1:
    pl.break_pin_links(bel.find_then_pin(br1))
    L(pl, bel.find_then_pin(br1), bel.find_execute_pin(call_r))

ia1 = bo._find_node(ed, "K2Node_EnhancedInputAction_1")
ia2 = bo._find_node(ed, "K2Node_EnhancedInputAction_2")
if ia1 and br0:
    pl.break_pin_links(bel.find_execute_pin(br0))
    L(pl, p(ia1, "Triggered", True), bel.find_execute_pin(br0))
if ia2 and br1:
    pl.break_pin_links(bel.find_execute_pin(br1))
    L(pl, p(ia2, "Triggered", True), bel.find_execute_pin(br1))

# grab + timer + simple poll
add = bo._find_node(ed, "K2Node_CallFunction_13")
sel = bo._find_node(ed, "K2Node_Select_1")
grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
en = bo._find_node(ed, "K2Node_CallFunction_4")
hide = bo._find_node(ed, "K2Node_Message_1")
if sel and add:
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    pl.break_pin_links(p(add, "MappingContext"))
    L(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")
if grab and en and hide and add:
    pl.break_pin_links(p(grab, "then", True))
    L(pl, p(grab, "then", True), p(en, "execute"))
    L(pl, p(en, "then", True), p(hide, "execute"))
    L(pl, p(hide, "then", True), p(add, "execute"))
    pl.break_pin_links(bel.find_then_pin(add))

grab_get = bo._find_node(ed, "K2Node_VariableGet_0")
get_owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
L(pl, p(grab_get, "GrabComponentSnap", True), p(get_owner, "self"))
timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
pl.set_pin_value(p(timer, "FunctionName"), POLL)
pl.set_pin_value(p(timer, "Time"), "0.05")
pl.set_pin_value(p(timer, "bLooping"), "true")
L(pl, p(get_owner, "ReturnValue", True), p(timer, "Object"))
L(pl, bel.find_then_pin(add), bel.find_execute_pin(timer))

poll = ed.add_custom_event_node(POLL)
br = ed.add_branch_node()
L(pl, p(poll, "then", True), bel.find_execute_pin(br))
call_p = ed.add_call_function_node("FireWeapon")
if self_n:
    L(pl, p(self_n, "self", True), p(call_p, "self"))
L(pl, bel.find_then_pin(br), bel.find_execute_pin(call_p))

pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
was_l = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
pl.set_pin_value(p(was_l, "Key"), KEY_L)
was_r = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
pl.set_pin_value(p(was_r, "Key"), KEY_R)
or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
L(pl, p(pc, "ReturnValue", True), p(was_l, "self"))
L(pl, p(pc, "ReturnValue", True), p(was_r, "self"))
L(pl, p(was_l, "ReturnValue", True), p(or_n, "A"))
L(pl, p(was_r, "ReturnValue", True), p(or_n, "B"))
L(pl, p(or_n, "ReturnValue", True), p(br, "Condition"))

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
if bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE:
    unreal.EditorAssetLibrary.save_asset(GUN)
    # respawn on table
    TABLE = unreal.Vector(-500, 470, 71)
    ROT = unreal.Rotator(-90, 0, 0)
    for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        if "GunVR" in a.get_actor_label() or a.get_class().get_name() == "BP_GunVR_UMP45_C":
            unreal.EditorLevelLibrary.destroy_actor(a)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), TABLE, ROT)
    actor.set_actor_label("GunVR_UMP45_TEST")
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print("SPAWNED", actor.get_actor_label())
