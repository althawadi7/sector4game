"""One gun only: BP_GunVR_UMP45 mesh swap + shoot/grab fix. Run:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_one_gunvr_ump45.py"
"""
import sys
import unreal

# Bridge package (CursorUnrealBridge plugin)
_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
import cursor_unreal_bridge.blueprint_ops as bo

GUN = "/Game/GunVR/BP_GunVR_UMP45"
UMP_MESH = "/Game/Weapons/UMP45/Mesh/StaticMesh/SM_UMP45"
PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
SCALE = 0.85  # UMP static mesh ~same size as SM_Rifle; tweak if needed
TABLE_LOC = unreal.Vector(-500, 470, 71)
TABLE_ROT = unreal.Rotator(-90, 0, 0)


def fix_mesh():
    bp = unreal.load_asset(GUN)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    mesh_asset = unreal.load_asset(UMP_MESH)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or "")
        obj = lib.get_object(data)
        if isinstance(obj, unreal.StaticMeshComponent) and name in ("SM_Pistol", "GunMesh", "Mesh"):
            obj.set_static_mesh(mesh_asset)
            obj.set_editor_property("relative_scale3d", unreal.Vector(SCALE, SCALE, SCALE))
            print("mesh set", name, UMP_MESH)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(GUN)


def fix_shoot():
  path = GUN
  name = "BP_GunVR_UMP45"
  bp = unreal.load_asset(path + "." + name)
  ed, _ = bo._editor_for(bp, "EventGraph")
  pl = bo._pinlib()
  bel = bo._bel()
  POLL = "PollReload"
  IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
  IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
  GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"

  def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")

  spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
  if spawn:
    pl.set_pin_value(p(spawn, "Class"), PROJECTILE)
  # grab chain + timer (from fix_shoot_safe)
  grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
  en = bo._find_node(ed, "K2Node_CallFunction_4")
  hide = bo._find_node(ed, "K2Node_Message_1")
  add = bo._find_node(ed, "K2Node_CallFunction_13")
  if grab and en and hide and add:
    pl.break_pin_links(p(grab, "then", True))
    pl.try_create_connection(p(grab, "then", True), p(en, "execute"))
    pl.try_create_connection(p(en, "then", True), p(hide, "execute"))
    pl.try_create_connection(p(hide, "then", True), p(add, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")
    timer = None
    for n in ed.list_all_nodes() or []:
      if bo._node_title(n) == "Set Timer by Function Name" and pl.get_pin_value(p(n, "FunctionName")) == POLL:
        timer = n
        break
    if not timer:
      timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimerByFunctionName")
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    sp = None
    for n in ed.list_all_nodes() or []:
      if bo._node_title(n) == "Self-Reference":
        sp = n
        break
    if sp and timer:
      pl.try_create_connection(p(sp, "self", True), p(timer, "Object"))
    pl.break_pin_links(p(add, "then", True))
    pl.try_create_connection(p(add, "then", True), bel.find_execute_pin(timer))

  sel = bo._find_node(ed, "K2Node_Select_1")
  if sel and add:
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    pl.break_pin_links(p(add, "MappingContext"))
    pl.try_create_connection(p(sel, "ReturnValue", True), p(add, "MappingContext"))

  if spawn:
    spawn_exec = bel.find_execute_pin(spawn)
    poll = bo._find_node(ed, POLL)
    if not poll:
      ed.add_custom_event_node(POLL)
      poll = bo._find_node(ed, POLL)
    br = None
    poll_then = p(poll, "then", True)
    for pin in pl.list_connected_pins(poll_then) or []:
      node = pin.get_owning_node()
      if bo._node_title(node) == "Branch":
        br = node
        break
    if br:
      pl.break_pin_links(bel.find_then_pin(br))
      pl.try_create_connection(bel.find_then_pin(br), spawn_exec)

  unreal.BlueprintEditorLibrary.compile_blueprint(bp)
  unreal.EditorAssetLibrary.save_asset(path)
  print("shoot fix", bp.status)


def cleanup_level():
    removed = 0
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        cn = actor.get_class().get_name()
        label = actor.get_actor_label()
        if "Pistol" in cn or "Rifle" in cn or "Grenade" in cn or "Weapon_" in cn or label.startswith("GunVR"):
            unreal.EditorLevelLibrary.destroy_actor(actor)
            removed += 1
    print("removed", removed)
    bp = unreal.load_asset(GUN)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), TABLE_LOC, TABLE_ROT)
    actor.set_actor_label("GunVR_UMP45_TEST")
    print("spawned", actor.get_actor_label(), "comps", [c.get_name() for c in actor.get_components_by_class(unreal.ActorComponent)])
    unreal.EditorLevelLibrary.save_current_level()


print("=== ONE GUN: UMP45 ===")
fix_mesh()
fix_shoot()
cleanup_level()
print("DONE — test ONE gun: GunVR_UMP45_TEST on table")
