"""
Simple default shooting: strip VFX/SFX/debug/auto-fire, wire Branch -> Spawn projectile,
add Quest-safe trigger poll (VR trigger press -> FireWeapon -> spawn).

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/simple_default_shoot.py"
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
GRENADE_PROJECTILE = "/Game/XRFramework/Blueprints/BP_BombProjectile.BP_BombProjectile_C"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
GOOD_OPTIONS = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"
POLL = "PollReload"
KEY_L_PRESS = "OculusTouch_Left_Trigger_Click"
KEY_R_PRESS = "OculusTouch_Right_Trigger_Click"

WEAPONS = [
    ("/Game/XRFramework/Blueprints/BP_Pistol", PROJECTILE),
    ("/Game/XRFramework/Blueprints/BP_Rifle", PROJECTILE),
    ("/Game/XRFramework/Blueprints/BP_GrenadeLauncher", GRENADE_PROJECTILE),
]

REMOVE_TITLES = {
    "PrintString",
    "SpawnSystemAtLocation",
    "PlaySoundAtLocation",
    "SpawnSoundAtLocation",
    "SpawnEmitterAtLocation",
    "AutoFire",
    "CheckAutoFire",
    "Set bWantsFire",
    "Get bWantsFire",
    "Get FireInterval",
    "Set Timer by Function Name",
    "Clear Timer by Function Name",
}


def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")


def link(pl, a, b):
    if a and b:
        return pl.try_create_connection(a, b)
    return False


def unlink(pl, pin):
    if pin:
        pl.break_pin_links(pin)


def wire_self_actor_ref(ed, pl, target_object_pin):
    self_n = None
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_Self":
            self_n = n
            break
    if not self_n or not target_object_pin:
        return False
    root = ed.add_call_function_node("/Script/Engine.Actor.K2_GetRootComponent")
    bo._set_node_pos(root, 1650, 50)
    owner = ed.add_call_function_node("/Script/Engine.ActorComponent.GetOwner")
    bo._set_node_pos(owner, 1800, 50)
    link(pl, p(self_n, "self", True), p(root, "self"))
    link(pl, p(root, "ReturnValue", True), p(owner, "self"))
    link(pl, p(owner, "ReturnValue", True), target_object_pin)
    return True


def find_spawn_fire_target(ed, pl):
    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if not spawn:
        return None
    bel = bo._bel()
    spawn_exec = bel.find_execute_pin(spawn)
    for n in ed.list_all_nodes() or []:
        if "Knot" in n.get_class().get_name():
            out_pin = p(n, "OutputPin", True)
            if out_pin and spawn_exec in (pl.list_connected_pins(out_pin) or []):
                return p(n, "InputPin", False) or bel.find_execute_pin(n)
    return spawn_exec


def ensure_fire_event(ed, pl, fire_target):
    bel = bo._bel()
    fire = bo._find_node(ed, "FireWeapon")
    if not fire:
        fire = ed.add_custom_event_node("FireWeapon")
        bo._set_node_pos(fire, 800, -600)
    unlink(pl, p(fire, "then", True))
    link(pl, p(fire, "then", True), fire_target)
    return fire


def get_call_fire(ed):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "FireWeapon" and "CallFunction" in n.get_class().get_name():
            return n
    n = ed.add_call_function_node("FireWeapon")
    bo._set_node_pos(n, 750, -500)
    return n


def get_pc(ed):
    return bo._find_node(ed, "K2Node_CallFunction_9") or bo._find_node(ed, "K2Node_CallFunction_31")


def fix_ia_triggers():
    base = "/Game/XRFramework/Input/Actions/"
    for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
        path = base + name
        ia = unreal.load_asset(path + "." + name)
        if not ia:
            continue
        triggers = [t for t in list(ia.get_editor_property("triggers") or []) if t is not None]
        if not triggers:
            triggers = [unreal.InputTriggerPressed(), unreal.InputTriggerDown()]
        ia.set_editor_property("triggers", triggers)
        unreal.EditorAssetLibrary.save_asset(path)


def strip_nodes(ed):
    remove = []
    for n in ed.list_all_nodes() or []:
        title = bo._node_title(n)
        if title in REMOVE_TITLES:
            remove.append(n)
        if title == POLL and n.get_class().get_name() == "K2Node_CustomEvent":
            remove.append(n)
        if title == "FireWeapon" and "CallFunction" in n.get_class().get_name():
            remove.append(n)
    if remove:
        ed.remove_nodes(remove)


def fix_grab_and_timer(ed, pl, add):
    grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
    en = bo._find_node(ed, "K2Node_CallFunction_4")
    hide = bo._find_node(ed, "K2Node_Message_1")
    if grab and en and hide:
        unlink(pl, p(grab, "then", True))
        link(pl, p(grab, "then", True), p(en, "execute"))
        link(pl, p(en, "then", True), p(hide, "execute"))
        link(pl, p(hide, "then", True), p(add, "execute"))

    unlink(pl, p(add, "then", True))
    timer = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_SetTimer")
    bo._set_node_pos(timer, 2000, 200)
    pl.set_pin_value(p(timer, "FunctionName"), POLL)
    pl.set_pin_value(p(timer, "Time"), "0.05")
    pl.set_pin_value(p(timer, "bLooping"), "true")
    wire_self_actor_ref(ed, pl, p(timer, "Object"))
    link(pl, p(add, "then", True), p(timer, "execute"))
    pl.set_pin_value(p(add, "Options"), GOOD_OPTIONS)
    pl.set_pin_value(p(add, "Priority"), "10")

    drop = bo._find_node(ed, "K2Node_ComponentBoundEvent_1")
    show = bo._find_node(ed, "K2Node_Message_0")
    dis = bo._find_node(ed, "K2Node_CallFunction_12")
    rem = bo._find_node(ed, "K2Node_CallFunction_14")
    if drop and show:
        clear = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.K2_ClearTimer")
        bo._set_node_pos(clear, 2000, 350)
        pl.set_pin_value(p(clear, "FunctionName"), POLL)
        wire_self_actor_ref(ed, pl, p(clear, "Object"))
        unlink(pl, p(drop, "then", True))
        link(pl, p(drop, "then", True), p(show, "execute"))
        if dis and rem:
            link(pl, p(show, "then", True), p(dis, "execute"))
            link(pl, p(dis, "then", True), p(rem, "execute"))
            link(pl, p(rem, "then", True), p(clear, "execute"))
        else:
            link(pl, p(show, "then", True), p(clear, "execute"))

    if not bo._find_node(ed, POLL):
        ed.add_custom_event_node(POLL)


def fix_poll_shoot(ed, pl):
    bel = bo._bel()
    poll = bo._find_node(ed, POLL)
    if not poll:
        poll = ed.add_custom_event_node(POLL)
        bo._set_node_pos(poll, 900, 400)

    unlink(pl, p(poll, "then", True))
    pc = get_pc(ed)
    if not pc:
        return False

    was_l = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
    bo._set_node_pos(was_l, 1100, 300)
    pl.set_pin_value(p(was_l, "Key"), KEY_L_PRESS)
    link(pl, p(pc, "ReturnValue", True), p(was_l, "self"))

    was_r = ed.add_call_function_node("/Script/Engine.PlayerController.WasInputKeyJustPressed")
    bo._set_node_pos(was_r, 1100, 400)
    pl.set_pin_value(p(was_r, "Key"), KEY_R_PRESS)
    link(pl, p(pc, "ReturnValue", True), p(was_r, "self"))

    or_n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.BooleanOR")
    bo._set_node_pos(or_n, 1300, 350)
    link(pl, p(was_l, "ReturnValue", True), p(or_n, "A"))
    link(pl, p(was_r, "ReturnValue", True), p(or_n, "B"))

    shoot_br = ed.add_branch_node()
    bo._set_node_pos(shoot_br, 1450, 350)
    link(pl, bel.find_then_pin(poll), bel.find_execute_pin(shoot_br))
    link(pl, p(or_n, "ReturnValue", True), p(shoot_br, "Condition"))

    call_fire = get_call_fire(ed)
    unlink(pl, bel.find_execute_pin(call_fire))
    ok = link(pl, bel.find_then_pin(shoot_br), bel.find_execute_pin(call_fire))
    return ok


def wire_hand_branches(ed, pl, fire_target):
    bel = bo._bel()
    for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
        br = bo._find_node(ed, br_id)
        if not br:
            continue
        then = bel.find_then_pin(br)
        unlink(pl, then)
        link(pl, then, fire_target)


def fix_weapon(bp_path, projectile):
    name = bp_path.split("/")[-1]
    bp = unreal.load_asset(bp_path + "." + name)
    if not bp:
        unreal.log_error("simple_shoot: missing " + bp_path)
        return
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()

    strip_nodes(ed)

    sel = bo._find_node(ed, "K2Node_Select_1")
    add_mc = bo._find_node(ed, "K2Node_CallFunction_13")
    if sel and add_mc:
        pl.set_pin_value(p(sel, "Option 0"), IMC_L)
        pl.set_pin_value(p(sel, "Option 1"), IMC_R)
        unlink(pl, p(add_mc, "MappingContext"))
        link(pl, p(sel, "ReturnValue", True), p(add_mc, "MappingContext"))
        pl.set_pin_value(p(add_mc, "Options"), GOOD_OPTIONS)
        pl.set_pin_value(p(add_mc, "Priority"), "10")

    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if spawn:
        pl.set_pin_value(p(spawn, "Class"), projectile)

    fire_target = find_spawn_fire_target(ed, pl)
    if fire_target:
        ensure_fire_event(ed, pl, fire_target)
        wire_hand_branches(ed, pl, fire_target)

    if add_mc:
        fix_grab_and_timer(ed, pl, add_mc)
    poll_ok = fix_poll_shoot(ed, pl)
    unreal.log(name + " poll=" + str(poll_ok))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    unreal.log(name + " status=" + str(bp.status))


def main():
    fix_ia_triggers()
    for path, projectile in WEAPONS:
        try:
            fix_weapon(path, projectile)
        except Exception as exc:
            unreal.log_error("simple_shoot: " + path + " failed: " + str(exc))
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log("simple_shoot: DONE — grab gun, pull VR trigger to shoot")


main()
