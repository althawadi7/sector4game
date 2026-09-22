"""
Wire NW_MuzzleFX + FreeWeaponSounds into all VR gun blueprints.
Inserts PlaySoundAtLocation + SpawnSystemAtLocation before projectile spawn.

Run in demovr (Output Log Python):
  py C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/add_realistic_fx_to_guns_demovr.py
"""
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
        "sound": "/Game/FreeWeaponSounds/Cue/Handgun/Gunshots/handgun_gunshot_01_Cue.handgun_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_Pistol_MuzzleFlash.FXS_Pistol_MuzzleFlash",
    },
    "/Game/XRFramework/Blueprints/BP_Rifle": {
        "sound": "/Game/FreeWeaponSounds/Cue/AssaultRifle/Gunshots/assault_rifle_gunshot_01_Cue.assault_rifle_gunshot_01_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_02.FXS_NS_MuzzleFlash_02",
    },
    "/Game/XRFramework/Blueprints/BP_GrenadeLauncher": {
        "sound": "/Game/FreeWeaponSounds/Cue/GrenadeLauncher/GL_fire_Cue.GL_fire_Cue",
        "fx": "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_ShotBurst_01.FXS_NS_ShotBurst_01",
    },
}

SOUND_VAR = "FireSoundCue"
FX_VAR = "MuzzleFlashFX"
FX_NODE_SOUND = "PlaySoundAtLocation"
FX_NODE_NIAGARA = "SpawnSystemAtLocation"


def log(msg):
    LOG.append(msg)
    unreal.log(str(msg))


def ensure_object_var(bp, var_name, obj_class):
    bel = unreal.BlueprintEditorLibrary
    names = {str(n) for n in bel.list_member_variable_names(bp)}
    if var_name in names:
        return
    pin_type = bel.get_object_reference_type(obj_class)
    bel.add_member_variable(bp, var_name, pin_type)


def set_var_default(bp, var_name, asset):
    bel = unreal.BlueprintEditorLibrary
    bel.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property(var_name, asset)


def find_node(editor, bel, name=None, title=None):
    for node in editor.list_all_nodes():
        if name and node.get_name() == name:
            return node
        if title and bel.get_node_title(node) == title:
            return node
    return None


def find_pin(node, pin_name, direction=None):
    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary
    return bo._find_pin(node, pin_name, prefer_direction=direction)


def wire_fx_graph(bp_path, sound_path, fx_path):
    bp = unreal.load_asset(bp_path)
    if not bp:
        log("MISSING " + bp_path)
        return False

    sound = unreal.load_asset(sound_path)
    fx = unreal.load_asset(fx_path)
    if not sound or not fx:
        log("MISSING assets for " + bp_path)
        return False

    bel = unreal.BlueprintEditorLibrary
    pinlib = unreal.BlueprintGraphPinLibrary

    ensure_object_var(bp, SOUND_VAR, unreal.SoundBase)
    ensure_object_var(bp, FX_VAR, unreal.NiagaraSystem)
    set_var_default(bp, SOUND_VAR, sound)
    set_var_default(bp, FX_VAR, fx)

    editor, _graph = bo._editor_for(bp, "EventGraph")

    if find_node(editor, bel, title="PlaySoundAtLocation") and find_node(
        editor, bel, title="SpawnSystemAtLocation"
    ):
        log(bp.get_name() + " FX already wired — updated defaults only")
        unreal.EditorAssetLibrary.save_asset(bp_path)
        return True

    spawn = find_node(editor, bel, title="SpawnActor BP Projectile")
    knot = find_node(editor, bel, name="K2Node_Knot_0")
    world_loc = find_node(editor, bel, name="K2Node_CallFunction_7")
    world_rot = find_node(editor, bel, name="K2Node_CallFunction_8")
    if not spawn or not knot or not world_loc:
        log(bp.get_name() + " missing expected shoot nodes")
        return False

    spawn_exec = find_pin(spawn, "execute", "input")
    knot_out = find_pin(knot, "OutputPin", "output")
    if knot_out:
        for cp in list(pinlib.list_connected_pins(knot_out) or []):
            pinlib.break_single_pin_link(knot_out, cp)

    sound_node = editor.add_call_function_node(
        "/Script/Engine.GameplayStatics.PlaySoundAtLocation"
    )
    bo._set_node_pos(sound_node, 2480, 420)

    fx_node = editor.add_call_function_node(
        "/Script/Niagara.NiagaraFunctionLibrary.SpawnSystemAtLocation"
    )
    bo._set_node_pos(fx_node, 2480, 620)

    sound_var = editor.add_get_member_variable_node(SOUND_VAR)
    bo._set_node_pos(sound_var, 2200, 500)

    fx_var = editor.add_get_member_variable_node(FX_VAR)
    bo._set_node_pos(fx_var, 2200, 700)

    self_node = editor.create_node_from_name(
        "Self-Reference", unreal.Vector2D(2200.0, 380.0), []
    )

    pinlib.try_create_connection(find_pin(knot, "OutputPin", "output"), find_pin(sound_node, "execute", "input"))
    pinlib.try_create_connection(find_pin(sound_node, "then", "output"), find_pin(fx_node, "execute", "input"))
    pinlib.try_create_connection(find_pin(fx_node, "then", "output"), find_pin(spawn, "execute", "input"))

    pinlib.try_create_connection(find_pin(self_node, "self", "output"), find_pin(sound_node, "WorldContextObject", "input"))
    pinlib.try_create_connection(find_pin(self_node, "self", "output"), find_pin(fx_node, "WorldContextObject", "input"))
    pinlib.try_create_connection(find_pin(sound_var, SOUND_VAR, "output"), find_pin(sound_node, "Sound", "input"))
    pinlib.try_create_connection(find_pin(world_loc, "ReturnValue", "output"), find_pin(sound_node, "Location", "input"))

    pinlib.try_create_connection(find_pin(fx_var, FX_VAR, "output"), find_pin(fx_node, "SystemTemplate", "input"))
    pinlib.try_create_connection(find_pin(world_loc, "ReturnValue", "output"), find_pin(fx_node, "Location", "input"))
    if world_rot:
        pinlib.try_create_connection(find_pin(world_rot, "ReturnValue", "output"), find_pin(fx_node, "Rotation", "input"))

  # Scale vector default (1,1,1) left as pin default
    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    log(bp.get_name() + " wired sound=" + sound.get_name() + " fx=" + fx.get_name())
    return True


log("=== ADD REALISTIC FX TO GUNS ===")
for bp_path, cfg in GUN_SETUP.items():
    wire_fx_graph(bp_path, cfg["sound"], cfg["fx"])

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("DONE")
RESULT = LOG
