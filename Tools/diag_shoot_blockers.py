"""Deep shoot blocker diagnostic. Run via execute_unreal_python."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

pinlib = bo._pinlib()
bel = bo._bel()

def p(n, name, out=False):
    return bo._find_pin(n, name, "output" if out else "input")

def conns(pin):
    if not pin:
        return []
    return [
        bo._node_title(c.get_owning_node()) + "/" + str(c.get_pin_name())
        for c in (pinlib.list_connected_pins(pin) or [])
    ]

print("=" * 60)
print("INPUT ACTIONS — IA_Shoot triggers")
for name in ["IA_Shoot_Left", "IA_Shoot_Right"]:
    ia = unreal.load_asset("/Game/XRFramework/Input/Actions/" + name + "." + name)
    if not ia:
        print("  MISSING", name)
        continue
    triggers = ia.get_editor_property("triggers") or []
    print(" ", name, "triggers=", len([t for t in triggers if t]))

print("\nIMC WEAPON mappings (Quest keys):")
for ip in ["/Game/XRFramework/Input/IMC_Weapon_Left", "/Game/XRFramework/Input/IMC_Weapon_Right"]:
    imc = unreal.load_asset(ip + "." + ip.split("/")[-1])
    if not imc:
        print("  MISSING", ip)
        continue
    dk = imc.get_editor_property("default_key_mappings")
    for m in dk.get_editor_property("mappings"):
        act = m.get_editor_property("action")
        key = m.get_editor_property("key")
        kn = key.get_editor_property("key_name") if key else "?"
        print(" ", ip.split("/")[-1], act.get_name() if act else "?", "->", kn)

for path in [
    "/Game/XRFramework/Blueprints/BP_Pistol",
    "/Game/XRFramework/Blueprints/BP_Rifle",
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
]:
    name = path.split("/")[-1]
    bp = unreal.load_asset(path + "." + name)
    ed, _ = bo._editor_for(bp, "EventGraph")
    print("\n" + "=" * 60)
    print(name, "status=", bp.status)

    grab = bo._find_node(ed, "K2Node_ComponentBoundEvent_0")
    if grab:
        print(" GRAB chain:")
        n = grab
        for _ in range(8):
            then = bel.find_then_pin(n)
            dests = conns(then)
            print("   ", bo._node_title(n), "->", dests)
            if not dests:
                break
            n = pinlib.list_connected_pins(then)[0].get_owning_node()

    add = bo._find_node(ed, "K2Node_CallFunction_13")
    if add:
        opts = pinlib.get_pin_value(p(add, "Options"))
        print(" AddMappingContext Options:", opts)
        if "True" in str(opts) and "IgnoreAllPressed" in str(opts):
            print("  *** BLOCKER: bIgnoreAllPressedKeysUntilRelease=True blocks trigger! ***")

    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Set Timer by Function Name":
            fn = pinlib.get_pin_value(p(n, "FunctionName"))
            obj = conns(p(n, "Object"))
            print(" SetTimer fn=", fn, "Object=", obj)
            if not obj:
                print("  *** BLOCKER: SetTimer Object not wired — poll never runs! ***")

    poll = bo._find_node(ed, "PollReload")
    if poll:
        print(" PollReload.then ->", conns(p(poll, "then", True)))
    else:
        print(" *** BLOCKER: no PollReload event ***")

    for n in ed.list_all_nodes() or []:
        if "WasInputKeyJustPressed" in bo._node_title(n) or "IsInputKeyDown" in bo._node_title(n):
            key = pinlib.get_pin_value(p(n, "Key"))
            print(" KeyCheck", bo._node_title(n), "key=", key)

    for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
        br = bo._find_node(ed, br_id)
        if br:
            print(" HandBranch", br_id)
            print("   exec<-", conns(p(br, "execute")))
            print("   cond<-", conns(p(br, "Condition")))
            print("   then->", conns(bel.find_then_pin(br)))
            print("   else->", conns(bo._find_pin(br, "else", True)))

    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Branch" and poll:
            ex = bel.find_execute_pin(n)
            if any(pinlib.list_connected_pins(ex)):
                for pin in pinlib.list_connected_pins(ex) or []:
                    if pin.get_owning_node() == poll:
                        print(" PollShootBranch", n.get_name())
                        print("   cond<-", conns(p(n, "Condition")))
                        print("   then->", conns(bel.find_then_pin(n)))

    for n in ed.list_all_nodes() or []:
        if "EnhancedInputAction" in n.get_class().get_name():
            for pname in ["Started", "Triggered"]:
                cp = p(n, pname, True)
                c = conns(cp)
                if c:
                    print(" IA", bo._node_title(n), pname, "->", c)

    muzzle = None
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "SpawnSystemAtLocation":
            muzzle = n
    if muzzle:
        print(" Muzzle exec<-", conns(bel.find_execute_pin(muzzle)))
        print(" Muzzle then->", conns(bel.find_then_pin(muzzle)))

    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    if spawn:
        print(" Spawn exec<-", conns(bel.find_execute_pin(spawn)))
        print(" Spawn Class=", pinlib.get_pin_value(p(spawn, "Class")))

print("\n" + "=" * 60)
print("DIAG DONE")
