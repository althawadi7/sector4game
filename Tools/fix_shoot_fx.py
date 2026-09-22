"""
Add muzzle VFX + fire SFX on the working shoot chain (safe, minimal nodes).
Chain: fire trigger -> SpawnSystemAtLocation -> PlaySoundAtLocation -> PlayHapticEffect -> Spawn projectile

Run: py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_shoot_fx.py"
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

MUZZLE = "/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash.NS_MuzzleFlash"
POLL = "PollReload"

WEAPONS = [
    (
        "/Game/XRFramework/Blueprints/BP_Pistol",
        "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C",
        "/Game/Zombie/Sound/Gun/S__EnergyBeamPistol_Fire_01.S__EnergyBeamPistol_Fire_01",
        "0.4,0.4,0.4",
    ),
    (
        "/Game/XRFramework/Blueprints/BP_Rifle",
        "/Game/XRFramework/Blueprints/BP_Projectile.BP_Projectile_C",
        "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_gunshot_01_Cue.assault_rifle_gunshot_01_Cue",
        "0.45,0.45,0.45",
    ),
    (
        "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
        "/Game/XRFramework/Blueprints/BP_BombProjectile.BP_BombProjectile_C",
        "/Game/Zombie/Sound/Gun/S__EnergyBeamPistol_Fire_01.S__EnergyBeamPistol_Fire_01",
        "0.5,0.5,0.5",
    ),
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


def find_get_loc(ed):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "Get World Location":
            return n
    return None


def find_haptic(ed):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "PlayHapticEffect":
            return n
    return None


def find_or_add_muzzle(ed):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "SpawnSystemAtLocation":
            return n
    n = ed.add_call_function_node(
        "/Script/Niagara.NiagaraFunctionLibrary.SpawnSystemAtLocation"
    )
    bo._set_node_pos(n, 2200, -350)
    return n


def find_or_add_sound(ed):
    for n in ed.list_all_nodes() or []:
        if bo._node_title(n) == "PlaySoundAtLocation":
            return n
    n = ed.add_call_function_node("/Script/Engine.GameplayStatics.PlaySoundAtLocation")
    bo._set_node_pos(n, 2400, -350)
    return n


def find_poll_shoot_branch(ed, pl, poll):
    bel = bo._bel()
    poll_then = p(poll, "then", True)
    if poll_then:
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


def collect_fire_sources(ed, pl):
    """Nodes whose then pin should start the FX chain."""
    bel = bo._bel()
    sources = []
    poll = bo._find_node(ed, POLL)
    if poll:
        br = find_poll_shoot_branch(ed, pl, poll)
        if br:
            sources.append(bel.find_then_pin(br))
    for br_id in ["K2Node_IfThenElse_0", "K2Node_IfThenElse_1"]:
        br = bo._find_node(ed, br_id)
        if br:
            sources.append(bel.find_then_pin(br))
    fire_evt = bo._find_node(ed, "FireWeapon")
    if fire_evt and fire_evt.get_class().get_name() == "K2Node_CustomEvent":
        sources.append(p(fire_evt, "then", True))
    return sources


def fix_weapon(path, projectile, sound, scale):
    name = path.split("/")[-1]
    bp = unreal.load_asset(path + "." + name)
    if not bp:
        unreal.log_error("missing " + path)
        return
    ed, _ = bo._editor_for(bp, "EventGraph")
    pl = bo._pinlib()
    bel = bo._bel()

    spawn = bo._find_node(ed, "K2Node_SpawnActorFromClass_0")
    haptic = find_haptic(ed)
    if not spawn or not haptic:
        unreal.log_error(name + ": missing spawn/haptic")
        return

    muzzle = find_or_add_muzzle(ed)
    sound_n = find_or_add_sound(ed)
    get_loc = find_get_loc(ed)

    pl.set_pin_value(p(muzzle, "SystemTemplate"), MUZZLE)
    pl.set_pin_value(p(muzzle, "Scale"), scale)
    pl.set_pin_value(p(sound_n, "Sound"), sound)
    pl.set_pin_value(p(sound_n, "VolumeMultiplier"), "1.0")
    pl.set_pin_value(p(spawn, "Class"), projectile)

    if get_loc:
        loc = p(get_loc, "ReturnValue", True)
        unlink(pl, p(muzzle, "Location"))
        unlink(pl, p(sound_n, "Location"))
        link(pl, loc, p(muzzle, "Location"))
        link(pl, loc, p(sound_n, "Location"))

    muzzle_exec = bel.find_execute_pin(muzzle)
    spawn_exec = bel.find_execute_pin(spawn)
    haptic_exec = bel.find_execute_pin(haptic)

    unlink(pl, p(muzzle, "then", True))
    unlink(pl, p(sound_n, "execute"))
    unlink(pl, p(sound_n, "then", True))
    unlink(pl, p(haptic, "execute"))
    unlink(pl, p(haptic, "then", True))
    unlink(pl, spawn_exec)

    link(pl, p(muzzle, "then", True), bel.find_execute_pin(sound_n))
    link(pl, bel.find_then_pin(sound_n), haptic_exec)
    link(pl, bel.find_then_pin(haptic), spawn_exec)

    for src in collect_fire_sources(ed, pl):
        unlink(pl, src)
        ok = link(pl, src, muzzle_exec)
        unreal.log(name + " fire src -> muzzle: " + str(ok))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log(name + " FX OK " + str(bp.status))


for w in WEAPONS:
    try:
        fix_weapon(*w)
    except Exception as exc:
        unreal.log_error(str(exc))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("fix_shoot_fx DONE")
