"""
Rebuild BP_GunVR_UMP45 from working BP_Pistol + Quest3 shoot fix (single clean pass).
Run: py ".../Tools/rebuild_ump45_from_pistol.py"
"""
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
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
POLL = "PollReload"
AXIS_L = "OculusTouch_Left_Trigger_Axis"
AXIS_R = "OculusTouch_Right_Trigger_Axis"


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    return pl.try_create_connection(a, b) if a and b else False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


def find_poll_branch(ed, pl, poll):
    bel = bo._bel()
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) != "Branch":
            continue
        ex = bel.find_execute_pin(n)
        for pin in pl.list_connected_pins(ex) or []:
            if pin.get_owning_node() == poll:
                return n
    return None


def wire_quest3_edge(ed, pl, br):
    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
    if not pc:
        return False
    ax = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    pl.set_pin_value(p(ax, "Key"), AXIS_L)
    ge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    pl.set_pin_value(p(ge, "B"), "0.55")
    link(pl, p(pc, "ReturnValue", True), p(ax, "self"))
    link(pl, p(ax, "ReturnValue", True), p(ge, "A"))
    td = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    pl.set_pin_value(p(td, "Key"), AXIS_L)
    lt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    pl.set_pin_value(p(lt, "B"), "0.12")
    link(pl, p(pc, "ReturnValue", True), p(td, "self"))
    link(pl, p(td, "ReturnValue", True), p(lt, "A"))
    and_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    link(pl, p(ge, "ReturnValue", True), p(and_l, "A"))
    link(pl, p(lt, "ReturnValue", True), p(and_l, "B"))
    ax2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputAnalogKeyState")
    pl.set_pin_value(p(ax2, "Key"), AXIS_R)
    ge2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Greater_DoubleDouble")
    pl.set_pin_value(p(ge2, "B"), "0.55")
    link(pl, p(pc, "ReturnValue", True), p(ax2, "self"))
    link(pl, p(ax2, "ReturnValue", True), p(ge2, "A"))
    td2 = ed.add_call_function_node("/Script/Engine.PlayerController.GetInputKeyTimeDown")
    pl.set_pin_value(p(td2, "Key"), AXIS_R)
    lt2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.Less_DoubleDouble")
    pl.set_pin_value(p(lt2, "B"), "0.12")
    link(pl, p(pc, "ReturnValue", True), p(td2, "self"))
    link(pl, p(td2, "ReturnValue", True), p(lt2, "A"))
    and_r = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanAND")
    link(pl, p(ge2, "ReturnValue", True), p(and_r, "A"))
    link(pl, p(lt2, "ReturnValue", True), p(and_r, "B"))
    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    link(pl, p(and_l, "ReturnValue", True), p(or_n, "A"))
    link(pl, p(and_r, "ReturnValue", True), p(or_n, "B"))
    cond = p(br, "Condition")
    unlink(pl, cond)
    return link(pl, p(or_n, "ReturnValue", True), cond)


def fix_grab_timer(ed, pl):
    bel = bo._bel()
    grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
    en = bo._find_node(ed, "K2Node_CallFunction_4")
    hide = bo._find_node(ed, "K2Node_Message_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not all([grab, en, hide, add]):
        return False
    unlink(pl, p(grab, "then", True))
    link(pl, p(grab, "then", True), p(en, "execute"))
    link(pl, p(en, "then", True), p(hide, "execute"))
    link(pl, p(hide, "then", True), p(add, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")
    timer = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Set Timer by Function Name":
            if pl.get_pin_value(p(n, "FunctionName")) == POLL:
                timer = n
                break
    if not timer:
        timer = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.K2_SetTimerByFunctionName"
        )
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    grab_get = bo._find_node(ed, "K2Node_VariableGet_0")
    get_owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
    link(pl, p(grab_get, "GrabComponentSnap", True), p(get_owner, "self"))
    unlink(pl, p(timer, "Object"))
    link(pl, p(get_owner, "ReturnValue", True), p(timer, "Object"))
    unlink(pl, p(add, "then", True))
    return link(pl, p(add, "then", True), bel.find_execute_pin(timer))


def fix_shoot(ed, pl):
    bel = bo._bel()
    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if not spawn:
        return False
    spawn_exec = bel.find_execute_pin(spawn)
    pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
    poll = bo._find_node(ed, POLL)
    if not poll:
        ed.add_custom_event_node(POLL)
        poll = bo._find_node(ed, POLL)
    br = find_poll_branch(ed, pl, poll)
    if not br:
        return False
    unlink(pl, bel.find_then_pin(br))
    ok1 = link(pl, bel.find_then_pin(br), spawn_exec)
    ok2 = wire_quest3_edge(ed, pl, br)
    return ok1 and ok2


def fix_imc(ed, pl):
    sel = bo._find_node(ed, "K2Node_Select_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not sel or not add:
        return
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    unlink(pl, p(add, "MappingContext"))
    link(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))


def swap_mesh(bp):
    mesh_asset = unreal.load_asset(UMP_MESH)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or "")
        obj = lib.get_object(data)
        if isinstance(obj, unreal.StaticMeshComponent) and name in ("SM_Pistol", "GunMesh", "Mesh"):
            obj.set_static_mesh(mesh_asset)
            obj.set_editor_property("relative_scale3d", unreal.Vector(0.85, 0.85, 0.85))


def fix_ia():
    for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
        path = "/Game/XRFramework/Input/Actions/" + name
        ia = unreal.load_asset(path + "." + name)
        if not ia:
            continue
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t]
        if not triggers:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)


# rebuild asset
if unreal.EditorAssetLibrary.does_asset_exist(GUN):
    unreal.EditorAssetLibrary.delete_asset(GUN)
if not unreal.EditorAssetLibrary.does_directory_exist("/Game/GunVR"):
    unreal.EditorAssetLibrary.make_directory("/Game/GunVR")
unreal.EditorAssetLibrary.duplicate_asset(PISTOL, GUN)

bp = unreal.load_asset(GUN)
swap_mesh(bp)
ed, _ = bo._editor_for(bp, "EventGraph")
pl = bo._pinlib()
fix_ia()
fix_imc(ed, pl)
t_ok = fix_grab_timer(ed, pl)
s_ok = fix_shoot(ed, pl)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(GUN)
print("timer", t_ok, "shoot", s_ok, "status", bp.status)

# respawn on table
TABLE = unreal.Vector(-500, 470, 71)
ROT = unreal.Rotator(-90, 0, 0)
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    cn = actor.get_class().get_name()
    if "GunVR" in actor.get_actor_label() or cn == "BP_GunVR_UMP45_C":
        unreal.EditorLevelLibrary.destroy_actor(actor)
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), TABLE, ROT)
actor.set_actor_label("GunVR_UMP45_TEST")
unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print("spawned", actor.get_actor_label())
