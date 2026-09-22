"""
SAFE shoot fix — minimal edits, one gun at a time. Does NOT spam new nodes.
Rewires existing PollReload -> Branch -> SpawnActor (skips broken Call FireWeapon).

Run AFTER reopening Unreal (Output Log):
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_shoot_safe.py"
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
BOMB = "/Game/XRFramework/Blueprints/BP_BombProjectile.BP_BombProjectile_C"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
GOOD = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
POLL = "PollReload"
KEY_L = "OculusTouch_Left_Trigger_Click"
KEY_R = "OculusTouch_Right_Trigger_Click"

WEAPONS = [
    ("/Game/XRFramework/Blueprints/BP_Pistol", PROJECTILE),
    ("/Game/XRFramework/Blueprints/BP_Rifle", PROJECTILE),
    ("/Game/XRFramework/Blueprints/BP_GrenadeLauncher", BOMB),
]


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    if a and b:
        return pl.try_create_connection(a, b)
    return False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


def self_pin(ed):
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_Self":
            return p(n, "self", True)
    return None


def wire_timer_object(ed, pl, timer_node):
    obj = p(timer_node, "Object")
    sp = self_pin(ed)
    if not obj or not sp:
        return False
    unlink(pl, obj)
    return link(pl, sp, obj)


def find_poll_shoot_branch(ed, pl, poll):
    """Branch whose execute is driven by PollReload then."""
    bel = bo._bel()
    poll_then = p(poll, "then", True)
    if not poll_then:
        return None
    for pin in pl.list_connected_pins(poll_then) or []:
        node = pin.get_owning_node()
        if bo._node_title(node) == "Branch":
            return node
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) != "Branch":
            continue
        ex = bel.find_execute_pin(n)
        for pin in pl.list_connected_pins(ex) or []:
            if pin.get_owning_node() == poll:
                return n
    return None


def ensure_minimal_poll(ed, pl, spawn_exec):
    """Only if no poll branch exists: tiny poll + 2 keys + branch -> spawn."""
    bel = bo._bel()
    poll = bo._find_node(ed, POLL)
    if not poll:
        poll = ed.add_custom_event_node(POLL)
        bo._set_node_pos(poll, 900, 400)

    br = find_poll_shoot_branch(ed, pl, poll)
    if br:
        unlink(pl, bel.find_then_pin(br))
        return link(pl, bel.find_then_pin(br), spawn_exec)

    pc = bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")
    if not pc:
        return False

    was_l = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
    bo._set_node_pos(was_l, 1100, 300)
    pl.set_pin_value(p(was_l, "Key"), KEY_L)
    link(pl, p(pc, "ReturnValue", True), p(was_l, "self"))

    was_r = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
    bo._set_node_pos(was_r, 1100, 400)
    pl.set_pin_value(p(was_r, "Key"), KEY_R)
    link(pl, p(pc, "ReturnValue", True), p(was_r, "self"))

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    bo._set_node_pos(or_n, 1300, 350)
    link(pl, p(was_l, "ReturnValue", True), p(or_n, "A"))
    link(pl, p(was_r, "ReturnValue", True), p(or_n, "B"))

    br = ed.add_branch_node()
    bo._set_node_pos(br, 1450, 350)
    link(pl, p(poll, "then", True), bel.find_execute_pin(br))
    link(pl, p(or_n, "ReturnValue", True), p(br, "Condition"))
    return link(pl, bel.find_then_pin(br), spawn_exec)


def fix_grab_timer(ed, pl):
    grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
    en = bo._find_node(ed, "K2Node_CallFunction_4")
    hide = bo._find_node(ed, "K2Node_Message_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not all([grab, en, hide, add]):
        return
    unlink(pl, p(grab, "then", True))
    link(pl, p(grab, "then", True), p(en, "execute"))
    link(pl, p(en, "then", True), p(hide, "execute"))
    link(pl, p(hide, "then", True), p(add, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD)
    pl.set_pin_value(p(add, "Priority"), "10")

    bel = bo._bel()
    timer = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Set Timer by Function Name":
            fn = pl.get_pin_value(p(n, "FunctionName"))
            if fn == POLL:
                timer = n
                break
    if not timer:
        timer = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.K2_SetTimerByFunctionName"
        )
        bo._set_node_pos(timer, 2000, 200)
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    wire_timer_object(ed, pl, timer)
    unlink(pl, p(add, "then", True))
    link(pl, p(add, "then", True), bel.find_execute_pin(timer))


def fix_imc(ed, pl):
    sel = bo._find_node(ed, "K2Node_Select_1")
    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if not sel or not add:
        return
    pl.set_pin_value(p(sel, "Option 0"), IMC_L)
    pl.set_pin_value(p(sel, "Option 1"), IMC_R)
    unlink(pl, p(add, "MappingContext"))
    link(pl, p(sel, "ReturnValue", True), p(add, "MappingContext"))


def fix_weapon(path, projectile):
    name = path.split("/")[-1]
    bp = unreal.load_asset(path + "." + name)
    if not bp:
        unreal.log_error("missing " + path)
        return
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()
    bel = bo._bel()

    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if not spawn:
        unreal.log_error(name + ": no spawn node")
        return
    spawn_exec = bel.find_execute_pin(spawn)
    pl.set_pin_value(p(spawn, "Class"), projectile)

    fix_imc(ed, pl)
    fix_grab_timer(ed, pl)

    poll = bo._find_node(ed, POLL)
    if not poll:
        ed.add_custom_event_node(POLL)
        poll = bo._find_node(ed, POLL)

    br = find_poll_shoot_branch(ed, pl, poll)
    if br:
        unlink(pl, bel.find_then_pin(br))
        ok = link(pl, bel.find_then_pin(br), spawn_exec)
        unreal.log(name + " rewire branch->spawn=" + str(ok))
    else:
        ok = ensure_minimal_poll(ed, pl, spawn_exec)
        unreal.log(name + " minimal poll=" + str(ok))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(name + " " + str(bp.status))


for path, proj in WEAPONS:
    try:
        fix_weapon(path, proj)
    except Exception as exc:
        unreal.log_error(path + " " + str(exc))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("fix_shoot_safe DONE")
