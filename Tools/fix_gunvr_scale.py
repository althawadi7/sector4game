"""
Fix GunVR weapon scale/visual size: hide huge helper meshes/widgets,
reset component transforms, respawn table guns at correct VR size.
Run: py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_gunvr_scale.py"
"""
import unreal

WEAPON_BPS = [
    '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
]

TABLE_SPAWNS = [
    ('GunVR_Weapon_UMP45_00', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-485, 415, 76), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_UMP45_01', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-500, 470, 71), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_UMP45_02', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-500, 320, 71), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_AK47_00', '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
     unreal.Vector(-437.36, 430.75, 76.24), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_AK47_01', '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
     unreal.Vector(-463.79, 450.61, 71.3), unreal.Rotator(90, 0, 0)),
    ('GunVR_Weapon_37Stakeout_00', '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
     unreal.Vector(-520.78, 287.55, 64.72), unreal.Rotator(-90, 0, 0)),
]

HIDE_MESH_NAMES = ('T_Hand_L', 'T_Hand_R', 'GripHand')
GRAB_PATH = '/Game/XRFramework/Blueprints/BP_GrabComponent'


def log(msg):
    print(msg)


def fix_blueprint_components(bp_path):
    bp = unreal.load_asset(bp_path)
    if not bp:
        log(f'MISSING {bp_path}')
        return
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary

    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or '')
        obj = lib.get_object(data)

        if name == 'GunMesh' and isinstance(obj, unreal.SceneComponent):
            obj.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
            obj.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))

        if name == 'AmmoCounter' and isinstance(obj, unreal.WidgetComponent):
            obj.set_editor_property('draw_size', unreal.IntPoint(200, 100))
            obj.set_editor_property('relative_scale3d', unreal.Vector(0.01, 0.01, 0.01))
            obj.set_editor_property('hidden_in_game', True)
            try:
                obj.set_editor_property('hidden_in_editor', True)
            except Exception:
                pass

        if name in HIDE_MESH_NAMES and isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property('hidden_in_game', True)
            obj.set_editor_property('visible', False)
            try:
                obj.set_editor_property('hidden_in_editor', True)
            except Exception:
                pass

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    log(f'fixed template {bp_path.split("/")[-1]}')


def gun_dim(actor):
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.get_name() == 'GunMesh':
            o, e, s = unreal.SystemLibrary.get_component_bounds(comp)
            return max(e.x, e.y, e.z) * 2
    return None


log('=== FIX GUNVR SCALE ===')

for path in WEAPON_BPS:
    fix_blueprint_components(path)

removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    cn = actor.get_class().get_name()
    label = actor.get_actor_label()
    if 'Weapon_' in cn or label.startswith('GunVR_'):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
log(f'removed {removed} gun actors')

placed = 0
for label, path, loc, rot in TABLE_SPAWNS:
    bp = unreal.load_asset(path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log(f'SKIP {label} status={bp.status if bp else None}')
        continue
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), loc, rot)
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    dim = gun_dim(actor)
    log(f'placed {label} gun_mesh_dim={dim}')
    placed += 1

unreal.EditorLevelLibrary.save_current_level()
log(f'DONE placed={placed} (target mesh size ~70-90 units, same as old SM_Rifle)')
