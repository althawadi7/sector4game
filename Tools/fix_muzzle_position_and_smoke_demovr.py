"""Fix muzzle flash/smoke: correct nozzle offsets + attach FX to MuzzleLocation."""
import sys
from pathlib import Path

import unreal

PLUGIN_PY = Path(__file__).resolve().parents[1] / "Plugins/CursorUnrealBridge/Content/Python"
if str(PLUGIN_PY) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PY))

import cursor_unreal_bridge.blueprint_ops as bo  # noqa: E402

LOG = []

GUN_SETUP = {
    "/Game/XRFramework/Blueprints/BP_Pistol": {
        "muzzle_y": 19.223918,
        "smoke": "/Game/NW_MuzzleFX/Particle_FX/Smoke/FXS_NS_Smoke_2.FXS_NS_Smoke_2",
    },
    "/Game/XRFramework/Blueprints/BP_Rifle": {
        "muzzle_y": 51.0,
        "smoke": "/Game/NW_MuzzleFX/Particle_FX/Smoke/FXS_NS_Smoke_2.FXS_NS_Smoke_2",
    },
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher": {
        "muzzle_y": 54.8,
        "smoke": "/Game/NW_MuzzleFX/Particle_FX/Smoke/FXS_NS_Smoke_3.FXS_NS_Smoke_3",
    },
}

MUZZLE_Z = 8.321923
FLASH_VAR = "MuzzleFlashFX"
SMOKE_VAR = "MuzzleSmokeFX"
ATTACH_FN = "/Script/Niagara.NiagaraFunctionLibrary.SpawnSystemAttached"


def log(msg):
    LOG.append(msg)
    unreal.log(str(msg))


def get_pin(node, name):
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    for p in bel.list_all_pins(node):
        if str(pinlib.get_pin_name(p)) == name:
            return p
    return None


def link(a, an, b, bn):
    pinlib = unreal.BlueprintGraphPinLibrary
    pa, pb = get_pin(a, an), get_pin(b, bn)
    if pa and pb:
        return bool(pinlib.try_create_connection(pa, pb))
    return False


def unlink_all(node, name):
    pinlib = unreal.BlueprintGraphPinLibrary
    p = get_pin(node, name)
    if not p:
        return
    for cp in list(pinlib.list_connected_pins(p) or []):
        pinlib.break_single_pin_link(p, cp)


def ensure_niagara_var(bp, var_name):
    bel = unreal.BlueprintEditorLibrary
    names = {str(n) for n in bel.list_member_variable_names(bp)}
    if var_name in names:
        return
    pin_type = bel.get_object_reference_type(unreal.NiagaraSystem)
    bel.add_member_variable(bp, var_name, pin_type)


def set_muzzle_offset(bp_path, muzzle_y):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    bp = unreal.load_asset(bp_path)
    loc = unreal.Vector(0.000086, muzzle_y, MUZZLE_Z)
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        if str(lib.get_display_name(data)) == "MuzzleLocation_GEN_VARIABLE":
            obj = lib.get_object(data)
            obj.set_editor_property("relative_location", loc)
            log(f"{bp.get_name()} MuzzleLocation -> y={muzzle_y}")
            return
    log(f"{bp_path} MuzzleLocation subobject not found")


def find_muzzle_var_node(editor, bel):
    for node in editor.list_all_nodes():
        if bel.get_node_title(node) == "Get MuzzleLocation":
            return node
    return None


def fix_fx_graph(bp_path, smoke_path):
    bp = unreal.load_asset(bp_path)
    smoke = unreal.load_asset(smoke_path)
    if not smoke:
        log(f"MISSING smoke asset {smoke_path}")
        return

    bel = unreal.BlueprintEditorLibrary
    ensure_niagara_var(bp, SMOKE_VAR)
    bel.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property(SMOKE_VAR, smoke)

    editor, _ = bo._editor_for(bp, "EventGraph")
    spawn = next(
        (n for n in editor.list_all_nodes() if bel.get_node_title(n) == "SpawnActor BP Projectile"),
        None,
    )
    knot = next((n for n in editor.list_all_nodes() if n.get_name() == "K2Node_Knot_0"), None)
    world_loc = next((n for n in editor.list_all_nodes() if n.get_name() == "K2Node_CallFunction_7"), None)
    muzzle_var = find_muzzle_var_node(editor, bel)

    if not spawn or not knot or not muzzle_var:
        log(f"{bp.get_name()} missing shoot graph nodes")
        return

    sounds = [n for n in editor.list_all_nodes() if bel.get_node_title(n) == "PlaySoundAtLocation"]
    old_at_loc = [n for n in editor.list_all_nodes() if bel.get_node_title(n) == "SpawnSystemAtLocation"]
    old_attached = [n for n in editor.list_all_nodes() if bel.get_node_title(n) == "SpawnSystemAttached"]

    sound = sounds[0] if sounds else editor.add_call_function_node(
        "/Script/Engine.GameplayStatics.PlaySoundAtLocation"
    )
    for extra in sounds[1:]:
        editor.remove_nodes([extra])
    for n in old_at_loc + old_attached:
        editor.remove_nodes([n])

    flash = editor.add_call_function_node(ATTACH_FN)
    smoke_node = editor.add_call_function_node(ATTACH_FN)
    bo._set_node_pos(flash, 2480, 620)
    bo._set_node_pos(smoke_node, 2720, 620)

    flash_var = next(
        (n for n in editor.list_all_nodes() if FLASH_VAR in bel.get_node_title(n)),
        None,
    )
    smoke_var = next(
        (n for n in editor.list_all_nodes() if SMOKE_VAR in bel.get_node_title(n)),
        None,
    )
    if not flash_var:
        flash_var = editor.add_get_member_variable_node(FLASH_VAR)
    if not smoke_var:
        smoke_var = editor.add_get_member_variable_node(SMOKE_VAR)
    bo._set_node_pos(flash_var, 2200, 700)
    bo._set_node_pos(smoke_var, 2200, 820)

    sv = next((n for n in editor.list_all_nodes() if "FireSoundCue" in bel.get_node_title(n)), None)
    if not sv:
        sv = editor.add_get_member_variable_node("FireSoundCue")

    for node, pinname in [
        (knot, "OutputPin"),
        (sound, "execute"),
        (sound, "then"),
        (flash, "execute"),
        (flash, "then"),
        (smoke_node, "execute"),
        (smoke_node, "then"),
        (spawn, "execute"),
    ]:
        unlink_all(node, pinname)

    link(knot, "OutputPin", sound, "execute")
    link(sound, "then", flash, "execute")
    link(flash, "then", smoke_node, "execute")
    link(smoke_node, "then", spawn, "execute")

    link(sv, "FireSoundCue", sound, "Sound")
    if world_loc:
        link(world_loc, "ReturnValue", sound, "Location")

    link(flash_var, FLASH_VAR, flash, "SystemTemplate")
    link(smoke_var, SMOKE_VAR, smoke_node, "SystemTemplate")
    link(muzzle_var, "MuzzleLocation", flash, "AttachToComponent")
    link(muzzle_var, "MuzzleLocation", smoke_node, "AttachToComponent")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    log(f"{bp.get_name()} attached flash+smoke at MuzzleLocation")


log("=== FIX MUZZLE POSITION + SMOKE ===")
for bp_path, cfg in GUN_SETUP.items():
    set_muzzle_offset(bp_path, cfg["muzzle_y"])
    fix_fx_graph(bp_path, cfg["smoke"])

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("DONE")
RESULT = LOG
