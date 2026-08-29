"""
BP_Pistol only: fix IMC wiring + on-screen debug prints for shoot chain.

Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_pistol_debug.py"
"""
import unreal

PISTOL = "/Game/XRFramework/Blueprints/BP_Pistol"
PROJECTILE = "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C"
IMC_L = "/Game/XRFramework/Input/IMC_Weapon_Left.IMC_Weapon_Left"
IMC_R = "/Game/XRFramework/Input/IMC_Weapon_Right.IMC_Weapon_Right"
GOOD_OPTIONS = "(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bNotifyUserSettings=False)"


def _pin(node, name, out=False):
    return blueprint_ops._find_pin(node, name, "output" if out else "input")


def _link(pinlib, a, b):
    if a and b:
        return pinlib.try_create_connection(a, b)
    return False


def _unlink(pinlib, pin):
    if pin:
        pinlib.break_pin_links(pin)


def _dbg(ed, pinlib, text, x, y):
    n = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
    blueprint_ops._set_node_pos(n, x, y)
    pinlib.set_pin_value(_pin(n, "InString"), text)
    pinlib.set_pin_value(_pin(n, "bPrintToScreen"), "true")
    pinlib.set_pin_value(_pin(n, "bPrintToLog"), "true")
    pinlib.set_pin_value(_pin(n, "Duration"), "3.0")
    pinlib.set_pin_value(_pin(n, "TextColor"), "(R=1.0,G=0.9,B=0.2,A=1.0)")
    return n


def main():
    bp = unreal.load_asset(PISTOL)
    ed, _ = blueprint_ops._editor_for(bp, "EventGraph")
    pinlib = blueprint_ops._pinlib()

    # --- fix IMC Select (was disconnected) ---
    sel = blueprint_ops._find_node(ed, "K2Node_Select_1")
    add_mc = blueprint_ops._find_node(ed, "K2Node_CallFunction_13")
    if sel and add_mc:
        pinlib.set_pin_value(_pin(sel, "Option 0"), IMC_L)
        pinlib.set_pin_value(_pin(sel, "Option 1"), IMC_R)
        mc = _pin(add_mc, "MappingContext")
        _unlink(pinlib, mc)
        _link(pinlib, _pin(sel, "ReturnValue", True), mc)
        pinlib.set_pin_value(_pin(add_mc, "Options"), GOOD_OPTIONS)
        pinlib.set_pin_value(_pin(add_mc, "Priority"), "10")
        unreal.log("PISTOL DBG: IMC Select + AddMappingContext fixed")

    # --- projectile class ---
    spawn = blueprint_ops._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if spawn:
        cp = _pin(spawn, "Class")
        if cp:
            pinlib.set_pin_value(cp, PROJECTILE)

    # --- ensure IA Started -> Branch (left/right) ---
    pairs = [
        ("K2Node_EnhancedInputAction_1", "K2Node_IfThenElse_0", "LEFT"),
        ("K2Node_EnhancedInputAction_2", "K2Node_IfThenElse_1", "RIGHT"),
    ]
    for ia_id, br_id, side in pairs:
        ia = blueprint_ops._find_node(ed, ia_id)
        br = blueprint_ops._find_node(ed, br_id)
        if not ia or not br:
            continue
        started = None
        for pname in ("Started", "Triggered"):
            p = _pin(ia, pname, True)
            if p:
                started = p
                break
        if started:
            _unlink(pinlib, started)
            _unlink(pinlib, _pin(br, "execute"))
            _link(pinlib, started, _pin(br, "execute"))
            unreal.log(f"PISTOL DBG: wired IA_Shoot_{side} -> Branch")

    # --- on-screen debug prints ---
    grab = blueprint_ops._find_node(ed, "K2Node_ComponentBoundEvent_0")
    drop = blueprint_ops._find_node(ed, "K2Node_ComponentBoundEvent_1")
    br_l = blueprint_ops._find_node(ed, "K2Node_IfThenElse_0")
    br_r = blueprint_ops._find_node(ed, "K2Node_IfThenElse_1")

    if grab:
        p_grab_dbg = _dbg(ed, pinlib, "PISTOL: GRABBED", -400, -400)
        _unlink(pinlib, _pin(grab, "then", True))
        _link(pinlib, _pin(grab, "then", True), _pin(p_grab_dbg, "execute"))
        en = blueprint_ops._find_node(ed, "K2Node_CallFunction_4")
        if en:
            _link(pinlib, _pin(p_grab_dbg, "then", True), _pin(en, "execute"))

    if add_mc and grab:
        p_imc_dbg = _dbg(ed, pinlib, "PISTOL: IMC ADDED", -200, -400)
        _unlink(pinlib, _pin(add_mc, "then", True))
        _link(pinlib, _pin(add_mc, "then", True), _pin(p_imc_dbg, "execute"))

    if br_l and spawn:
        p_fire_l = _dbg(ed, pinlib, "PISTOL: SHOOT LEFT OK", 200, -200)
        knot = blueprint_ops._find_node(ed, "K2Node_Knot_0")
        _unlink(pinlib, _pin(br_l, "then", True))
        _link(pinlib, _pin(br_l, "then", True), _pin(p_fire_l, "execute"))
        if knot:
            inp = _pin(knot, "InputPin") or _pin(knot, "Input")
            out = _pin(knot, "OutputPin", True) or _pin(knot, "", True)
            _unlink(pinlib, inp)
            _unlink(pinlib, out)
            _link(pinlib, _pin(p_fire_l, "then", True), inp)
            _link(pinlib, out, _pin(spawn, "execute"))
        else:
            _link(pinlib, _pin(p_fire_l, "then", True), _pin(spawn, "execute"))

    if br_r and spawn:
        p_fire_r = _dbg(ed, pinlib, "PISTOL: SHOOT RIGHT OK", 200, -100)
        knot = blueprint_ops._find_node(ed, "K2Node_Knot_0")
        _unlink(pinlib, _pin(br_r, "then", True))
        _link(pinlib, _pin(br_r, "then", True), _pin(p_fire_r, "execute"))
        if knot:
            inp = _pin(knot, "InputPin") or _pin(knot, "Input")
            _link(pinlib, _pin(p_fire_r, "then", True), inp)

    if drop:
        p_drop = _dbg(ed, pinlib, "PISTOL: DROPPED", -400, -500)
        _unlink(pinlib, _pin(drop, "then", True))
        _link(pinlib, _pin(drop, "then", True), _pin(p_drop, "execute"))
        dis = blueprint_ops._find_node(ed, "K2Node_CallFunction_12")
        if dis:
            _link(pinlib, _pin(p_drop, "then", True), _pin(dis, "execute"))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.log(f"PISTOL DBG: compile status = {bp.status}")
    unreal.EditorAssetLibrary.save_asset(PISTOL)
    unreal.log("PISTOL DBG: saved. Grab pistol, watch yellow on-screen text.")


main()
