"""One-shot: fresh duplicate from pistol + mesh + complete shoot wire.

WARNING: Crashes Unreal if run via Python bridge — use manual editor wiring instead.
"""
import sys
import unreal

_BRIDGE = unreal.Paths.project_dir() + "Plugins/CursorUnrealBridge/Content/Python"
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)

GUN = "/Game/GunVR/BP_GunVR_UMP45"
PISTOL = "/Game/XRFramework/Blueprints/BP_Pistol"
UMP_MESH = "/Game/Weapons/UMP45/Mesh/StaticMesh/SM_UMP45"

if unreal.EditorAssetLibrary.does_asset_exist(GUN):
    unreal.EditorAssetLibrary.delete_asset(GUN)
if not unreal.EditorAssetLibrary.does_directory_exist("/Game/GunVR"):
    unreal.EditorAssetLibrary.make_directory("/Game/GunVR")
unreal.EditorAssetLibrary.duplicate_asset(PISTOL, GUN)

bp = unreal.load_asset(GUN)
mesh_asset = unreal.load_asset(UMP_MESH)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    data = sub.k2_find_subobject_data_from_handle(h)
    name = str(lib.get_variable_name(data) or "")
    obj = lib.get_object(data)
    if isinstance(obj, unreal.StaticMeshComponent) and name in ("SM_Pistol", "GunMesh", "Mesh"):
        obj.set_static_mesh(mesh_asset)
        obj.set_editor_property("relative_scale3d", unreal.Vector(0.85, 0.85, 0.85))

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(GUN)
print("fresh duplicate status", bp.status)

exec(open(unreal.Paths.project_dir() + "Tools/wire_ump45_shoot_complete.py", encoding="utf-8").read())
