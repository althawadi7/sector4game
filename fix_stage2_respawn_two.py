"""
Fix Stage2: when zombies die, destroy them and respawn until 2 alive.
Run in Unreal: Output Log -> py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/fix_stage2_respawn_two.py"
Or via CursorUnrealBridge execute_unreal_python.
"""
import unreal
import sys

sys.path.insert(
    0,
    r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python",
)
from cursor_unreal_bridge import blueprint_ops as ops

bel = unreal.BlueprintEditorLibrary
pinlib = unreal.BlueprintGraphPinLibrary
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log("[RESPAWNFIX] " + str(m))


def find_pin(n, name):
    for p in bel.list_all_pins(n) or []:
        if str(pinlib.get_pin_name(p)) == name:
            return p
    return None


def links(p):
    try:
        return list(pinlib.list_connected_pins(p) or [])
    except Exception:
        return []


def connect(a, b):
    if not a or not b:
        return False
    try:
        return bool(pinlib.try_create_connection(a, b))
    except Exception as e:
        log(f"conn {e}")
        return False


def set_pin(n, pname, val):
    p = find_pin(n, pname)
    if not p:
        return False
    pinlib.set_pin_value(p, str(val))
    return True


def break_links(p):
    if not p:
        return
    try:
        pinlib.break_pin_links(p)
    except Exception:
        pass


def main():
    # 1) Destroy zombie as soon as HandleDeath runs (so GetAllActors count drops)
    PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
    bpz = unreal.load_asset(PAWN)
    edh, _ = ops._editor_for(bpz, "HandleDamageTaken")
    hd = None
    for n in edh.list_all_nodes():
        if bel.get_node_title(n) == "HandleDeath":
            hd = n
            break
    if hd:
        then = find_pin(hd, "then")
        linked = [bel.get_node_title(x.get_owning_node()) for x in links(then)]
        log(f"HandleDeath.then -> {linked}")
        if not any("Destroy" in x for x in linked):
            break_links(then)
            destroy = edh.add_call_function_node("/Script/Engine.Actor.K2_DestroyActor")
            ok = connect(then, find_pin(destroy, "execute"))
            log(f"HandleDeath.then->DestroyActor={ok}")
        else:
            log("Destroy already wired")

    cdoz = unreal.get_default_object(bpz.generated_class())
    try:
        cdoz.set_editor_property("Time before FadeOut", 0.05)
        cdoz.set_editor_property("Fades out after Death", True)
    except Exception as e:
        log(f"cdoz {e}")

    bel.compile_blueprint(bpz)
    unreal.EditorAssetLibrary.save_asset(PAWN)
    log(f"Pawn={bpz.status}")

    # 2) Stage2: keep Length < 2 spawn path healthy + random offsets + AlwaysSpawn
    PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
    pve = unreal.load_asset(PVE)
    ed, _ = ops._editor_for(pve, "EventGraph")

    getall = length = tofloat = fltlt = branch_spawn = begin_spawn = addv = None
    for n in ed.list_all_nodes():
        nm = n.get_name()
        t = bel.get_node_title(n)
        if nm == "K2Node_CallFunction_0" and "GetAllActorsOfClass" in t:
            getall = n
        if nm == "K2Node_CallArrayFunction_0":
            length = n
        if "To Float" in t:
            tofloat = n
        if t == "float < float":
            fltlt = n
        if nm == "K2Node_IfThenElse_0":
            branch_spawn = n
        if "BeginDeferredActorSpawnFromClass" in t:
            begin_spawn = n
        if "vector + vector" in t:
            addv = n

    # Ensure GetAll.then -> Branch and Length wired
    if getall and branch_spawn:
        then = find_pin(getall, "then")
        if not links(then):
            connect(then, find_pin(branch_spawn, "execute"))
            log("restored GetAll.then->Branch")
        out = find_pin(getall, "OutActors")
        if length and not links(find_pin(length, "TargetArray")):
            connect(out, find_pin(length, "TargetArray"))
            log("restored OutActors->Length")

    if length and tofloat and fltlt:
        # Length -> ToFloat -> float< A, B=2
        inp = find_pin(tofloat, "InInt")
        if not inp:
            for p in bel.list_all_pins(tofloat) or []:
                nm = str(pinlib.get_pin_name(p))
                if nm not in ("self", "ReturnValue"):
                    inp = p
                    break
        if not links(inp):
            connect(find_pin(length, "ReturnValue"), inp)
        if not links(find_pin(fltlt, "A")):
            connect(find_pin(tofloat, "ReturnValue"), find_pin(fltlt, "A"))
        set_pin(fltlt, "B", "2.0")
        log("Length<2 comparison OK")

    if begin_spawn:
        try:
            set_pin(begin_spawn, "CollisionHandlingOverride", "AlwaysSpawn")
            log("AlwaysSpawn")
        except Exception as e:
            log(f"AlwaysSpawn {e}")

    # Random XY spawn so new pair doesn't stack
    if addv:
        bp = find_pin(addv, "B")
        already = any(
            "MakeVector" in bel.get_node_title(x.get_owning_node()) for x in links(bp)
        )
        if not already:
            break_links(bp)
            mk = ed.add_call_function_node("/Script/Engine.KismetMathLibrary.MakeVector")
            rx = ed.add_call_function_node(
                "/Script/Engine.KismetMathLibrary.RandomFloatInRange"
            )
            ry = ed.add_call_function_node(
                "/Script/Engine.KismetMathLibrary.RandomFloatInRange"
            )
            set_pin(rx, "Min", "-450.0")
            set_pin(rx, "Max", "450.0")
            set_pin(ry, "Min", "-450.0")
            set_pin(ry, "Max", "450.0")
            set_pin(mk, "Z", "100.0")
            connect(find_pin(rx, "ReturnValue"), find_pin(mk, "X"))
            connect(find_pin(ry, "ReturnValue"), find_pin(mk, "Y"))
            connect(find_pin(mk, "ReturnValue"), bp)
            log("random spawn XY + Z100")
        else:
            log("random spawn already set")

    # Dual spawn: when Branch.then fires, Sequence spawn A then spawn B
    # Duplicate BeginDeferred+Finish+ForceAggro chain is heavy; tick-based 1-then-1 is fine
    # once Destroy works. Optionally force BatchSize spawn via ForLoop 0..(2-Length-1).

    bel.compile_blueprint(pve)
    unreal.EditorAssetLibrary.save_asset(PVE)
    log(f"PVE={pve.status}")

    # Verify
    edh, _ = ops._editor_for(bpz, "HandleDamageTaken")
    for n in edh.list_all_nodes():
        if bel.get_node_title(n) in ("HandleDeath", "Destroy Actor"):
            parts = []
            for p in bel.list_all_pins(n) or []:
                ls = [
                    f"{bel.get_node_title(x.get_owning_node())}.{pinlib.get_pin_name(x)}"
                    for x in links(p)
                ]
                if ls:
                    parts.append(f"{pinlib.get_pin_name(p)}<-{ls}")
            log(f"V {bel.get_node_title(n)}: {parts}")

    return {"log": LOG}


if __name__ == "__main__":
    print(main())
