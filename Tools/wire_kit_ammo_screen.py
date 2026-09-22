"""
Wire kit built-in ammo screens (material scalar 'Ammo Сount' with Cyrillic С)
into BP_Rifle: XRUpdateKitAmmoScreen + BeginPlay + calls after ammo changes.
"""
import unreal
import sys

sys.path.insert(
    0,
    r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Plugins/CursorUnrealBridge/Content/Python",
)
import cursor_unreal_bridge.blueprint_ops as bo

PATH = "/Game/XRFramework/Blueprints/BP_Rifle"
PARAM = "Ammo \u0421ount"  # Cyrillic С (U+0421)
FOREACH = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop"
Y = 5200
X0 = -2000

RESULT = {"steps": []}


def log(msg, **kw):
    RESULT["steps"].append({"msg": msg, **kw})


bp = unreal.load_asset(PATH)
editor, graph = bo._editor_for(bp)
pinlib = unreal.BlueprintGraphPinLibrary
bel = unreal.BlueprintEditorLibrary

# Remove prior attempt nodes if any (by title markers)
old = []
for n in editor.list_all_nodes():
    t = bo._node_title(n) or ""
    if t.startswith("XRUpdateKitAmmoScreen") or "XRUpdateKitAmmo" in t:
        old.append(n.get_name())
if old:
    bo.remove_blueprint_nodes(PATH, old, compile=False, save=False)
    bp = unreal.load_asset(PATH)
    editor, graph = bo._editor_for(bp)
    log("removed_old", names=old)

# --- Create custom event + graph ---
nodes_spec = [
    {"id": "evt", "type": "custom_event", "event_name": "XRUpdateKitAmmoScreen", "x": X0, "y": Y},
    {"id": "getAmmo", "type": "palette", "palette": "Variables|CurrentAmmo|Get", "x": X0 + 250, "y": Y + 120},
    {"id": "toFloat", "type": "call", "function_path": "/Script/Engine.KismetMathLibrary.Conv_IntToFloat", "x": X0 + 500, "y": Y + 120},
    # Own skeletal meshes (pistol)
    {"id": "getOwnSK", "type": "call", "function_path": "/Script/Engine.Actor.GetComponentsByClass", "x": X0 + 250, "y": Y + 280},
    # ChildActorComponents
    {"id": "getCAC", "type": "call", "function_path": "/Script/Engine.Actor.GetComponentsByClass", "x": X0 + 250, "y": Y + 480},
]

created = bo.add_blueprint_nodes(PATH, nodes_spec, compile=False, save=False)
log("base_nodes", created=created.get("created"))

bp = unreal.load_asset(PATH)
editor, graph = bo._editor_for(bp)

# Add macros and more nodes via editor API directly for reliability
def add_macro(path, x, y):
    node = editor.add_macro_node(path)
    bo._set_node_pos(node, x, y)
    return node


def add_call(fpath, x, y):
    node = editor.add_call_function_node(fpath)
    bo._set_node_pos(node, x, y)
    return node


def add_get_var(varname, x, y):
    node = editor.add_get_member_variable_node(varname)
    bo._set_node_pos(node, x, y)
    return node


def find(title_or_name):
    return bo._find_node(editor, title_or_name)


def link(a, ap, b, bp_):
    na = find(a) if isinstance(a, str) else a
    nb = find(b) if isinstance(b, str) else b
    pa = bo._find_pin(na, ap, "output") or bo._find_pin(na, ap)
    pb = bo._find_pin(nb, bp_, "input") or bo._find_pin(nb, bp_)
    if not pa or not pb:
        return False, f"pins {ap}->{bp_} on {bo._node_title(na)}/{bo._node_title(nb)}"
    ok = pinlib.try_create_connection(pa, pb)
    return bool(ok), "ok" if ok else "fail"


def set_pin(node, pname, value):
    pin = bo._find_pin(node, pname)
    if not pin:
        return False
    pinlib.set_pin_value(pin, str(value))
    return True


evt = find("XRUpdateKitAmmoScreen")
get_ammo = None
for n in editor.list_all_nodes():
    if bo._node_title(n) == "Get CurrentAmmo" and abs(n.node_pos_y - (Y + 120)) < 80:
        get_ammo = n
        break
if get_ammo is None:
    get_ammo = add_get_var("CurrentAmmo", X0 + 250, Y + 120)

to_float = find("To Float (Integer)")
get_own_sk = None
get_cac = None
for n in editor.list_all_nodes():
    t = bo._node_title(n)
    if t == "Get Components By Class":
        if abs(getattr(n, "node_pos_y", 0) - (Y + 280)) < 50:
            get_own_sk = n
        if abs(getattr(n, "node_pos_y", 0) - (Y + 480)) < 50:
            get_cac = n

# Set class pins on GetComponentsByClass
for node, cls_path in (
    (get_own_sk, "/Script/Engine.SkeletalMeshComponent"),
    (get_cac, "/Script/Engine.ChildActorComponent"),
):
    if not node:
        continue
    # pin often named ComponentClass
    for pname in ("ComponentClass", "Component Class", "Class"):
        pin = bo._find_pin(node, pname)
        if pin:
            try:
                pinlib.set_pin_type_object(pin, unreal.load_object(None, cls_path))
            except Exception:
                try:
                    pinlib.set_pin_value(pin, cls_path)
                except Exception as e:
                    log("set_class_fail", err=str(e)[:80], pname=pname)
            break

# ForEach own SK
fe_own = add_macro(FOREACH, X0 + 700, Y + 250)
# Inside loop: apply ammo to mesh slots 0..3
# Sequence for 4 slots
# CreateDynamicMaterialInstance needs target = Array Element

# Helper to build apply-chain for one mesh pin source node/pin
# We'll wire: fe_own LoopBody -> CDMI0 -> SetScalar Ammo -> SetScalar Backlight -> SetScalar Interface -> CDMI1 ...

def make_apply_chain(start_x, start_y, mesh_node, mesh_pin_name, ammo_node, prefix):
    """Returns (first_exec_node, last_then_pin_node) and list of created nodes."""
    nodes = []
    prev = None
    first = None
    for slot in range(4):
        cdmi = add_call("/Script/Engine.PrimitiveComponent.CreateDynamicMaterialInstance", start_x + slot * 450, start_y)
        set_pin(cdmi, "ElementIndex", str(slot))
        # SourceMaterial optional - leave empty to use current
        ssp_ammo = add_call("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue", start_x + slot * 450 + 200, start_y + 80)
        set_pin(ssp_ammo, "ParameterName", PARAM)
        ssp_bl = add_call("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue", start_x + slot * 450 + 200, start_y + 180)
        set_pin(ssp_bl, "ParameterName", "Backlight Display")
        set_pin(ssp_bl, "Value", "8.0")
        ssp_if = add_call("/Script/Engine.MaterialInstanceDynamic.SetScalarParameterValue", start_x + slot * 450 + 200, start_y + 280)
        set_pin(ssp_if, "ParameterName", "Interface Brightness")
        set_pin(ssp_if, "Value", "8.0")
        nodes.extend([cdmi, ssp_ammo, ssp_bl, ssp_if])
        # data: mesh -> cdmi self/target
        link(mesh_node, mesh_pin_name, cdmi, "self")
        # cdmi ReturnValue -> ssp targets
        for ssp in (ssp_ammo, ssp_bl, ssp_if):
            link(cdmi, "ReturnValue", ssp, "self")
        # ammo float -> ssp_ammo Value
        link(ammo_node, "ReturnValue", ssp_ammo, "Value")
        # exec chain
        if prev is None:
            first = cdmi
        else:
            link(prev, "then", cdmi, "execute")
        link(cdmi, "then", ssp_ammo, "execute")
        link(ssp_ammo, "then", ssp_bl, "execute")
        link(ssp_bl, "then", ssp_if, "execute")
        prev = ssp_if
    return first, prev, nodes


# Wire event -> get components
ok, msg = link(evt, "then", get_own_sk, "execute")
log("evt_to_ownsk", ok=ok, msg=msg)
ok, msg = link(get_own_sk, "ReturnValue", fe_own, "Array")
log("ownsk_to_fe", ok=ok, msg=msg)

# CurrentAmmo -> float
ok, msg = link(get_ammo, "CurrentAmmo", to_float, "In")
log("ammo_to_float", ok=ok, msg=msg)

# ForEach own: LoopBody -> apply chain; Array Element is the mesh
# Macro pins typically: Exec, Array, LoopBody, Array Element, Array Index, Completed
first, last, _ = make_apply_chain(X0 + 1100, Y + 200, fe_own, "Array Element", to_float, "own")
ok, msg = link(get_own_sk, "then", fe_own, "Exec")
log("ownsk_exec_fe", ok=ok, msg=msg)
ok, msg = link(fe_own, "LoopBody", first, "execute")
log("fe_own_body", ok=ok, msg=msg)

# After own completed -> get CAC
ok, msg = link(fe_own, "Completed", get_cac, "execute")
log("fe_own_done_cac", ok=ok, msg=msg)

fe_cac = add_macro(FOREACH, X0 + 700, Y + 700)
ok, msg = link(get_cac, "ReturnValue", fe_cac, "Array")
log("cac_arr", ok=ok, msg=msg)
ok, msg = link(get_cac, "then", fe_cac, "Exec")
log("cac_exec", ok=ok, msg=msg)

# For each CAC: Get Child Actor
get_child = add_call("/Script/Engine.ChildActorComponent.GetChildActor", X0 + 1000, Y + 700)
ok, msg = link(fe_cac, "Array Element", get_child, "self")
log("cac_elem_child", ok=ok, msg=msg)

# IsValid on child
is_valid = add_call("/Script/Engine.KismetSystemLibrary.IsValid", X0 + 1200, Y + 700)
ok, msg = link(get_child, "ReturnValue", is_valid, "Object")
log("child_valid_data", ok=ok, msg=msg)
branch = editor.add_branch_node()
bo._set_node_pos(branch, X0 + 1400, Y + 650)
ok, msg = link(fe_cac, "LoopBody", get_child, "execute")
log("cac_body_getchild", ok=ok, msg=msg)
# GetChildActor may be pure - if no execute pin, wire LoopBody to IsValid/Branch
# Check pins - if get_child has no execute, link LoopBody -> branch
if bo._find_pin(get_child, "execute"):
    link(get_child, "then", is_valid, "execute") if bo._find_pin(is_valid, "execute") else None
    link(get_child, "then", branch, "execute")
else:
    ok, msg = link(fe_cac, "LoopBody", branch, "execute")
    log("cac_body_branch", ok=ok, msg=msg)
ok, msg = link(is_valid, "ReturnValue", branch, "Condition")
log("valid_cond", ok=ok, msg=msg)

# True: get SK comps on child actor
get_child_sk = add_call("/Script/Engine.Actor.GetComponentsByClass", X0 + 1650, Y + 620)
for pname in ("ComponentClass", "Component Class", "Class"):
    pin = bo._find_pin(get_child_sk, pname)
    if pin:
        try:
            pinlib.set_pin_value(pin, "/Script/Engine.SkeletalMeshComponent")
        except Exception:
            pass
        break
ok, msg = link(get_child, "ReturnValue", get_child_sk, "self")
log("child_as_self_sk", ok=ok, msg=msg)
ok, msg = link(branch, "True", get_child_sk, "execute")
log("branch_true_sk", ok=ok, msg=msg)

fe_child_sk = add_macro(FOREACH, X0 + 1950, Y + 620)
ok, msg = link(get_child_sk, "ReturnValue", fe_child_sk, "Array")
ok, msg = link(get_child_sk, "then", fe_child_sk, "Exec")
first2, last2, _ = make_apply_chain(X0 + 2300, Y + 580, fe_child_sk, "Array Element", to_float, "childsk")
ok, msg = link(fe_child_sk, "LoopBody", first2, "execute")
log("child_sk_apply", ok=ok, msg=msg)

# Also static meshes on child after SK completed
get_child_sm = add_call("/Script/Engine.Actor.GetComponentsByClass", X0 + 1650, Y + 980)
for pname in ("ComponentClass", "Component Class", "Class"):
    pin = bo._find_pin(get_child_sm, pname)
    if pin:
        try:
            pinlib.set_pin_value(pin, "/Script/Engine.StaticMeshComponent")
        except Exception:
            pass
        break
ok, msg = link(get_child, "ReturnValue", get_child_sm, "self")
ok, msg = link(fe_child_sk, "Completed", get_child_sm, "execute")
fe_child_sm = add_macro(FOREACH, X0 + 1950, Y + 980)
ok, msg = link(get_child_sm, "ReturnValue", fe_child_sm, "Array")
ok, msg = link(get_child_sm, "then", fe_child_sm, "Exec")
first3, last3, _ = make_apply_chain(X0 + 2300, Y + 940, fe_child_sm, "Array Element", to_float, "childsm")
ok, msg = link(fe_child_sm, "LoopBody", first3, "execute")
log("child_sm_apply", ok=ok, msg=msg)

# Also update AmmoTextRender as fallback (keep visible text off for guns with mat screens - still set text)
# Get AmmoTextRender -> SetText
get_tr = add_get_var("AmmoTextRender", X0 + 700, Y + 1400)
to_text = add_call("/Script/Engine.KismetTextLibrary.Conv_IntToText", X0 + 950, Y + 1450)
set_text = add_call("/Script/Engine.TextRenderComponent.SetText", X0 + 1200, Y + 1400)
ok, msg = link(get_ammo, "CurrentAmmo", to_text, "InInt")
# pin might be InInt or Value
if not ok:
    ok, msg = link(get_ammo, "CurrentAmmo", to_text, "Int")
ok, msg = link(get_tr, "AmmoTextRender", set_text, "self")
ok, msg = link(to_text, "ReturnValue", set_text, "Value")
# Chain text update at start after event in parallel via Sequence
seq = add_call("/Script/Engine.KismetMathLibrary.Add_IntInt", X0, Y)  # placeholder wrong
# Use Sequence node via palette
try:
    seq_node = editor.create_node_from_name("Sequence", unreal.Vector2D(float(X0 + 150), float(Y)), [])
except Exception:
    seq_node = None
if not seq_node:
    try:
        seq_node = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.ExecuteRearScript")  # bad
        seq_node = None
    except Exception:
        seq_node = None

# Simpler: wire text update from fe_cac Completed
ok, msg = link(fe_cac, "Completed", set_text, "execute")
log("text_on_complete", ok=ok, msg=msg)

bel.compile_blueprint(bp)
status = str(bel.get_blueprint_compile_status(bp)) if hasattr(bel, "get_blueprint_compile_status") else "compiled"
unreal.EditorAssetLibrary.save_asset(PATH)
log("compiled", status=status)

RESULT["status"] = status
RESULT["param"] = PARAM
