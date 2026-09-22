"""
Simpler kit ammo screen wiring for BP_Rifle.
Creates XRUpdateKitAmmoScreen that updates material Ammo Сount on meshes.
Also wires BeginPlay + hooks after existing Set CurrentAmmo nodes via Call.
"""
import unreal
import sys
import json

sys.path.insert(
    0,
    r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python",
)
import cursor_unreal_bridge.blueprint_ops as bo

PATH = "/Game/XRFramework/Blueprints/BP_Rifle"
PARAM = "Ammo \u0421ount"
FOREACH = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop"
OUT = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools\_wire_ammo_result.json"

log = []


def L(m, **k):
    log.append({"m": m, **k})


bp = unreal.load_asset(PATH)
editor, graph = bo._editor_for(bp)
pinlib = unreal.BlueprintGraphPinLibrary
bel = unreal.BlueprintEditorLibrary


def find_title(title):
    for n in editor.list_all_nodes():
        if bo._node_title(n) == title:
            return n
    return None


def link(a, ap, b, bpname):
    pa = bo._find_pin(a, ap, "output") or bo._find_pin(a, ap)
    pb = bo._find_pin(b, bpname, "input") or bo._find_pin(b, bpname)
    if not pa or not pb:
        return False
    return bool(pinlib.try_create_connection(pa, pb))


def setv(node, pname, value):
    pin = bo._find_pin(node, pname)
    if not pin:
        return False
    try:
        pinlib.set_pin_value(pin, str(value))
        return True
    except Exception:
        return False


# Remove previous XRUpdateKitAmmoScreen event and nearby nodes at y>~5000 if present
to_del = []
for n in editor.list_all_nodes():
    t = bo._node_title(n) or ""
    y = float(getattr(n, "node_pos_y", 0) or 0)
    if t == "XRUpdateKitAmmoScreen" or (y >= 5000 and y <= 7000 and t):
        # only delete our previous region carefully: titles we create
        if t in (
            "XRUpdateKitAmmoScreen",
            "Get Components By Class",
            "For Each Loop",
            "CreateDynamicMaterialInstance",
            "SetScalarParameterValue",
            "Get Child Actor",
            "Is Valid",
            "Branch",
            "To Float (Integer)",
            "Set Text",
            "Get CurrentAmmo",
            "Get AmmoTextRender",
            "Conv_IntToText",
            "To Text (Integer)",
        ) and y >= 5000:
            to_del.append(n.get_name())
        elif t == "XRUpdateKitAmmoScreen":
            to_del.append(n.get_name())
if to_del:
    try:
        editor.remove_nodes([bo._find_node(editor, n) for n in to_del if bo._find_node(editor, n)])
        L("removed", n=len(to_del))
    except Exception as e:
        L("remove_err", err=str(e)[:100])

# Fresh editor
bp = unreal.load_asset(PATH)
editor, graph = bo._editor_for(bp)

Y = 5600
X = -2200

evt = editor.add_custom_event_node("XRUpdateKitAmmoScreen")
bo._set_node_pos(evt, X, Y)
L("evt", name=evt.get_name())

get_ammo = editor.add_get_member_variable_node("CurrentAmmo")
bo._set_node_pos(get_ammo, X + 280, Y + 140)

to_float = editor.add_call_function_node("/Script/Engine.KismetMathLibrary.Conv_IntToFloat")
bo._set_node_pos(to_float, X + 520, Y + 140)
link(get_ammo, "CurrentAmmo", to_float, "In")

# Get all ChildActorComponents on self
get_cac = editor.add_call_function_node("/Script/Engine.Actor.GetComponentsByClass")
bo._set_node_pos(get_cac, X + 280, Y + 300)
setv(get_cac, "ComponentClass", "/Script/Engine.ChildActorComponent")
link(evt, "then", get_cac, "execute")

fe_cac = editor.add_macro_node(FOREACH)
bo._set_node_pos(fe_cac, X + 700, Y + 280)
link(get_cac, "then", fe_cac, "Exec")
link(get_cac, "ReturnValue", fe_cac, "Array")

# GetChildActor (pure)
get_child = editor.add_call_function_node("/Script/Engine.ChildActorComponent.GetChildActor")
bo._set_node_pos(get_child, X + 1050, Y + 300)
link(fe_cac, "Array Element", get_child, "self")

# Get SK components from child
get_sk = editor.add_call_function_node("/Script/Engine.Actor.GetComponentsByClass")
bo._set_node_pos(get_sk, X + 1300, Y + 260)
setv(get_sk, "ComponentClass", "/Script/Engine.SkeletalMeshComponent")
# self = child actor
link(get_child, "ReturnValue", get_sk, "self")
link(fe_cac, "LoopBody", get_sk, "execute")

fe_sk = editor.add_macro_node(FOREACH)
bo._set_node_pos(fe_sk, X + 1650, Y + 240)
link(get_sk, "then", fe_sk, "Exec")
link(get_sk, "ReturnValue", fe_sk, "Array")

# For each skeletal mesh: CDMI slot0 + set ammo + brightness (slot0 covers most screens)
cdmi = editor.add_call_function_node("/Script/Engine.PrimitiveComponent.CreateDynamicMaterialInstance")
bo._set_node_pos(cdmi, X + 2000, Y + 200)
setv(cdmi, "ElementIndex", "0")
link(fe_sk, "Array Element", cdmi, "self")
link(fe_sk, "LoopBody", cdmi, "execute")

ssp = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp, X + 2350, Y + 180)
setv(ssp, "ParameterName", PARAM)
link(cdmi, "ReturnValue", ssp, "self")
link(cdmi, "then", ssp, "execute")
link(to_float, "ReturnValue", ssp, "Value")

ssp2 = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp2, X + 2700, Y + 180)
setv(ssp2, "ParameterName", "Backlight Display")
setv(ssp2, "Value", "10.0")
link(cdmi, "ReturnValue", ssp2, "self")
link(ssp, "then", ssp2, "execute")

ssp3 = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp3, X + 3050, Y + 180)
setv(ssp3, "ParameterName", "Interface Brightness")
setv(ssp3, "Value", "10.0")
link(cdmi, "ReturnValue", ssp3, "self")
link(ssp2, "then", ssp3, "execute")

# Also slot 1 (some kits put screen on second material)
cdmi1 = editor.add_call_function_node("/Script/Engine.PrimitiveComponent.CreateDynamicMaterialInstance")
bo._set_node_pos(cdmi1, X + 2000, Y + 420)
setv(cdmi1, "ElementIndex", "1")
link(fe_sk, "Array Element", cdmi1, "self")
link(ssp3, "then", cdmi1, "execute")

ssp1 = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp1, X + 2350, Y + 400)
setv(ssp1, "ParameterName", PARAM)
link(cdmi1, "ReturnValue", ssp1, "self")
link(cdmi1, "then", ssp1, "execute")
link(to_float, "ReturnValue", ssp1, "Value")

ssp1b = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp1b, X + 2700, Y + 400)
setv(ssp1b, "ParameterName", "Backlight Display")
setv(ssp1b, "Value", "10.0")
link(cdmi1, "ReturnValue", ssp1b, "self")
link(ssp1, "then", ssp1b, "execute")

# Own meshes path for pistol (no child actor): after CAC Completed
get_own = editor.add_call_function_node("/Script/Engine.Actor.GetComponentsByClass")
bo._set_node_pos(get_own, X + 700, Y + 700)
setv(get_own, "ComponentClass", "/Script/Engine.SkeletalMeshComponent")
link(fe_cac, "Completed", get_own, "execute")

fe_own = editor.add_macro_node(FOREACH)
bo._set_node_pos(fe_own, X + 1050, Y + 680)
link(get_own, "then", fe_own, "Exec")
link(get_own, "ReturnValue", fe_own, "Array")

cdmi_o = editor.add_call_function_node("/Script/Engine.PrimitiveComponent.CreateDynamicMaterialInstance")
bo._set_node_pos(cdmi_o, X + 1400, Y + 660)
setv(cdmi_o, "ElementIndex", "0")
link(fe_own, "Array Element", cdmi_o, "self")
link(fe_own, "LoopBody", cdmi_o, "execute")

ssp_o = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp_o, X + 1750, Y + 640)
setv(ssp_o, "ParameterName", PARAM)
link(cdmi_o, "ReturnValue", ssp_o, "self")
link(cdmi_o, "then", ssp_o, "execute")
link(to_float, "ReturnValue", ssp_o, "Value")

ssp_ob = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp_ob, X + 2100, Y + 640)
setv(ssp_ob, "ParameterName", "Backlight Display")
setv(ssp_ob, "Value", "10.0")
link(cdmi_o, "ReturnValue", ssp_ob, "self")
link(ssp_o, "then", ssp_ob, "execute")

ssp_oi = editor.add_call_function_node("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue")
bo._set_node_pos(ssp_oi, X + 2450, Y + 640)
setv(ssp_oi, "ParameterName", "Interface Brightness")
setv(ssp_oi, "Value", "10.0")
link(cdmi_o, "ReturnValue", ssp_oi, "self")
link(ssp_ob, "then", ssp_oi, "execute")

bel.compile_blueprint(bp)
st = bel.get_blueprint_compile_status(bp) if hasattr(bel, "get_blueprint_compile_status") else None
unreal.EditorAssetLibrary.save_asset(PATH)
L("compile", status=str(st))

# Wire calls to XRUpdateKitAmmoScreen after Set CurrentAmmo nodes and add BeginPlay
# Find Set CurrentAmmo nodes and append call
bp = unreal.load_asset(PATH)
editor, graph = bo._editor_for(bp)

call_nodes = []
set_ammo_nodes = []
for n in editor.list_all_nodes():
    t = bo._node_title(n) or ""
    if t == "Set CurrentAmmo":
        set_ammo_nodes.append(n)

L("set_ammo_count", n=len(set_ammo_nodes))

# For each Set CurrentAmmo, find its 'then' connections; insert call to custom event
# Easier: add Call Function XRUpdateKitAmmoScreen after each Set CurrentAmmo by reconnecting
for i, sn in enumerate(set_ammo_nodes):
    # create call to custom event
    try:
        call = editor.create_node_from_name("XRUpdateKitAmmoScreen", unreal.Vector2D(float(sn.node_pos_x + 300), float(sn.node_pos_y + 80)), [])
    except Exception:
        call = None
    if call is None:
        # use custom event call node via CallFunction on self - add_call to process event?
        try:
            call = editor.add_call_function_node("XRUpdateKitAmmoScreen")
        except Exception as e:
            L("call_fail", i=i, err=str(e)[:80])
            continue
    if call:
        bo._set_node_pos(call, int(sn.node_pos_x + 350), int(sn.node_pos_y + 60))
        # disconnect existing then targets? just also fire in parallel via linking then->call
        link(sn, "then", call, "execute")
        call_nodes.append(call.get_name())
        L("hooked_set_ammo", i=i, call=call.get_name(), title=bo._node_title(call))

# BeginPlay
try:
    bp_node = editor.find_event_node("ReceiveBeginPlay")
except Exception:
    bp_node = None
if not bp_node:
    try:
        bp_node = editor.create_node_from_name("BeginPlay", unreal.Vector2D(-2200, 5200), [])
    except Exception:
        bp_node = None
if not bp_node:
    # custom event won't help; add Event BeginPlay via add_call? use K2Node_Event
    try:
        bp_node = editor.create_node_from_name("Event BeginPlay", unreal.Vector2D(-2200, 5200), [])
    except Exception as e:
        L("beginplay_fail", err=str(e)[:100])

if bp_node:
    bo._set_node_pos(bp_node, -2200, 5200)
    # Set CurrentAmmo = MaxAmmo then update screen
    get_max = editor.add_get_member_variable_node("MaxAmmo")
    bo._set_node_pos(get_max, -1900, 5300)
    set_cur = editor.add_set_member_variable_node("CurrentAmmo")
    bo._set_node_pos(set_cur, -1650, 5200)
    link(bp_node, "then", set_cur, "execute")
    link(get_max, "MaxAmmo", set_cur, "CurrentAmmo")
    # call update
    try:
        call_bp = editor.create_node_from_name("XRUpdateKitAmmoScreen", unreal.Vector2D(-1300, 5200), [])
    except Exception:
        call_bp = None
    if call_bp:
        bo._set_node_pos(call_bp, -1300, 5200)
        link(set_cur, "then", call_bp, "execute")
        L("beginplay_wired", ok=True)
    else:
        L("beginplay_no_call")

bel.compile_blueprint(bp)
st2 = bel.get_blueprint_compile_status(bp) if hasattr(bel, "get_blueprint_compile_status") else None
unreal.EditorAssetLibrary.save_asset(PATH)
L("final_compile", status=str(st2))

RESULT = {"log": log, "param": PARAM}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(RESULT, f, indent=2)
