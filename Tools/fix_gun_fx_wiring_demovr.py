"""Fix broken shoot SFX/VFX wiring on all gun blueprints."""
import sys
from pathlib import Path

import unreal

PLUGIN_PY = Path(__file__).resolve().parents[1] / "Plugins/CursorUnrealBridge/Content/Python"
if str(PLUGIN_PY) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PY))

import cursor_unreal_bridge.blueprint_ops as bo  # noqa: E402

LOG = []
GUNS = [
    "/Game/XRFramework/Blueprints/BP_Pistol",
    "/Game/XRFramework/Blueprints/BP_Rifle",
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
]


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


def fix_bp(bp_path):
    bel = unreal.BlueprintEditorLibrary
    bp = unreal.load_asset(bp_path)
    editor, _ = bo._editor_for(bp, "EventGraph")

    spawn = next(n for n in editor.list_all_nodes() if bel.get_node_title(n) == "SpawnActor BP Projectile")
    knot = next(n for n in editor.list_all_nodes() if n.get_name() == "K2Node_Knot_0")
    world_loc = next((n for n in editor.list_all_nodes() if n.get_name() == "K2Node_CallFunction_7"), None)
    world_rot = next((n for n in editor.list_all_nodes() if n.get_name() == "K2Node_CallFunction_8"), None)

    sounds = [n for n in editor.list_all_nodes() if bel.get_node_title(n) == "PlaySoundAtLocation"]
    niags = [n for n in editor.list_all_nodes() if bel.get_node_title(n) == "SpawnSystemAtLocation"]
    sound = sounds[0] if sounds else editor.add_call_function_node(
        "/Script/Engine.GameplayStatics.PlaySoundAtLocation"
    )
    niag = niags[0] if niags else editor.add_call_function_node(
        "/Script/Niagara.NiagaraFunctionLibrary.SpawnSystemAtLocation"
    )
    for extra in sounds[1:] + niags[1:]:
        editor.remove_nodes([extra])

    sv = next((n for n in editor.list_all_nodes() if "FireSoundCue" in bel.get_node_title(n)), None)
    fv = next((n for n in editor.list_all_nodes() if "MuzzleFlashFX" in bel.get_node_title(n)), None)
    if not sv:
        sv = editor.add_get_member_variable_node("FireSoundCue")
    if not fv:
        fv = editor.add_get_member_variable_node("MuzzleFlashFX")

    for node, pinname in [
        (knot, "OutputPin"),
        (sound, "execute"),
        (sound, "then"),
        (niag, "execute"),
        (niag, "then"),
        (spawn, "execute"),
    ]:
        unlink_all(node, pinname)

    link(knot, "OutputPin", sound, "execute")
    link(sound, "then", niag, "execute")
    link(niag, "then", spawn, "execute")
    link(sv, "FireSoundCue", sound, "Sound")
    if world_loc:
        link(world_loc, "ReturnValue", sound, "Location")
    link(fv, "MuzzleFlashFX", niag, "SystemTemplate")
    if world_loc:
        link(world_loc, "ReturnValue", niag, "Location")
    if world_rot:
        link(world_rot, "ReturnValue", niag, "Rotation")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    log(bp.get_name() + " shoot chain: sound+niagara wired")


log("=== FIX GUN FX WIRING ===")
for path in GUNS:
    fix_bp(path)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("DONE")
RESULT = LOG
