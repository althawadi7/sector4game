# Flat script — no nested defs (UE Python RESULT nativize breaks on closures).
import unreal
import json

BEL = unreal.BlueprintEditorLibrary
PL = unreal.BlueprintGraphPinLibrary
OUT = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Saved\quest_fix_flat.json"
log = {"steps": []}

def pin_named(node, name):
    for p in list(BEL.list_all_pins(node) or []):
        if str(PL.get_pin_name(p)) == name:
            return p
    return None

def title_of(node):
    try:
        return str(BEL.get_node_title(node))
    except Exception:
        return node.get_name()

# ---- Master dilation ----
path = "/Game/LBVR/Blueprints/BP_MasterPlayerController"
bp = unreal.EditorAssetLibrary.load_asset(path)
ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(bp))
for n in list(ed.list_all_nodes() or []):
    if title_of(n) == "SetGlobalTimeDilation":
        p = pin_named(n, "TimeDilation")
        if p:
            PL.set_pin_value(p, "1.0")
            log["steps"].append("dilation1:" + n.get_name())
BEL.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(path)

# ---- Guns FX tune + replicates ----
# Use a simple mobile-friendly muzzle (NS_MuzzleFlash_00) — pistol-specific FX can fail silently on Quest Vulkan.
MUZZLE = "/Game/NW_MuzzleFX/Particle_FX/FXS_NS_MuzzleFlash_00.FXS_NS_MuzzleFlash_00"
SHOT = "/Game/FreeWeaponSounds/Cue/Handgun/Gunshots/handgun_gunshot_01_Cue.handgun_gunshot_01_Cue"
for gpath in ["/Game/XRFramework/Blueprints/BP_Pistol", "/Game/XRFramework/Blueprints/BP_Rifle"]:
    gbp = unreal.EditorAssetLibrary.load_asset(gpath)
    ged = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(gbp))
    for n in list(ged.list_all_nodes() or []):
        t = title_of(n)
        if t == "SpawnSystemAtLocation":
            p1 = pin_named(n, "bPreCullCheck")
            p2 = pin_named(n, "Scale")
            p3 = pin_named(n, "SystemTemplate")
            if p1:
                PL.set_pin_value(p1, "false")
            if p2:
                PL.set_pin_value(p2, "4.0,4.0,4.0")
            if p3:
                PL.set_pin_value(p3, MUZZLE)
            log["steps"].append("fx:" + gpath + ":" + n.get_name())
        if t == "PlaySoundAtLocation":
            ps = pin_named(n, "Sound")
            pv = pin_named(n, "VolumeMultiplier")
            if ps:
                PL.set_pin_value(ps, SHOT)
            if pv:
                PL.set_pin_value(pv, "2.0")
            log["steps"].append("sfx:" + gpath + ":" + n.get_name())
    cdo = unreal.get_default_object(gbp.generated_class)
    try:
        cdo.set_editor_property("replicates", True)
    except Exception as e:
        log["steps"].append("rep_err:" + str(e))
    BEL.compile_blueprint(gbp)
    unreal.EditorAssetLibrary.save_asset(gpath)

# ---- Zombie Length-1 ----
zpath = "/Game/Zombie/Blueprints/Behavior/BP_Zombie_AiController_Base"
zbp = unreal.EditorAssetLibrary.load_asset(zpath)
zed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(zbp))
length = None
getitem = None
sub = None
for n in list(zed.list_all_nodes() or []):
    nm = n.get_name()
    if nm == "K2Node_CallArrayFunction_1":
        length = n
    if nm == "K2Node_GetArrayItem_0":
        getitem = n
    if nm == "K2Node_PromotableOperator_3":
        sub = n
if length and getitem and sub:
    la = pin_named(length, "ReturnValue")
    sa = pin_named(sub, "A")
    sr = pin_named(sub, "ReturnValue")
    dim = pin_named(getitem, "Dimension 1")
    sb = pin_named(sub, "B")
    if sb:
        PL.set_pin_value(sb, "1")
    if la and sa:
        PL.try_create_connection(la, sa)
    if sr and dim:
        PL.try_create_connection(sr, dim)
    log["steps"].append("zombie_index_ok")
else:
    log["steps"].append("zombie_index_missing")
BEL.compile_blueprint(zbp)
unreal.EditorAssetLibrary.save_asset(zpath)

# ---- Zombie pawn replicate + always tick pose ----
ppath = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
if unreal.EditorAssetLibrary.does_asset_exist(ppath):
    pbp = unreal.EditorAssetLibrary.load_asset(ppath)
    pcdo = unreal.get_default_object(pbp.generated_class)
    for prop, val in (("replicates", True), ("replicate_movement", True), ("always_relevant", True)):
        try:
            pcdo.set_editor_property(prop, val)
            log["steps"].append("pawn:" + prop)
        except Exception as e:
            log["steps"].append("pawn_err:" + prop + ":" + str(e))
    try:
        mesh = pcdo.get_editor_property("mesh")
        if mesh:
            mesh.set_editor_property(
                "visibility_based_anim_tick_option",
                unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES,
            )
            log["steps"].append("mesh_always_tick")
    except Exception as e:
        log["steps"].append("mesh_err:" + str(e))
    BEL.compile_blueprint(pbp)
    unreal.EditorAssetLibrary.save_asset(ppath)

# ---- GrabComponent: Event Tick is empty but still costs if enabled — turn off ----
gpath = "/Game/XRFramework/Blueprints/BP_GrabComponent"
gbp = unreal.EditorAssetLibrary.load_asset(gpath)
gcdo = unreal.get_default_object(gbp.generated_class)
try:
    tick = gcdo.get_editor_property("primary_component_tick")
    try:
        tick.set_editor_property("b_start_with_tick_enabled", False)
        log["steps"].append("grab_tick_start_false")
    except Exception as e:
        log["steps"].append("grab_tick_prop_err:" + str(e))
except Exception as e:
    log["steps"].append("grab_tick_err:" + str(e))
BEL.compile_blueprint(gbp)
unreal.EditorAssetLibrary.save_asset(gpath)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(log, indent=2))
RESULT = "ok"
