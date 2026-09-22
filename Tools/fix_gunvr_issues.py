"""
Fix GunVR issues: correct gun size, respawn table guns, silence broken SteamVR pawn.
Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_gunvr_issues.py"
"""
import unreal

# ~0.55 matches old XR pistol/rifle feel in this project (GunVR meshes are ~2x template rifle visually).
GUN_MESH_SCALE = 0.55

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
BROKEN_PAWN = '/Game/VirtualRealityBP/Blueprints/BP_MotionController'


def log(msg):
    print(msg)


def gun_mesh_dim(actor):
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.get_name() == 'GunMesh':
            _, ext, _ = unreal.SystemLibrary.get_component_bounds(comp)
            return max(ext.x, ext.y, ext.z) * 2
    return None


def fix_weapon_blueprint(bp_path):
    bp = unreal.load_asset(bp_path)
    if not bp:
        log(f'MISSING {bp_path}')
        return
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    scale_vec = unreal.Vector(GUN_MESH_SCALE, GUN_MESH_SCALE, GUN_MESH_SCALE)

    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or '')
        obj = lib.get_object(data)

        if name == 'GunMesh' and isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
            obj.set_editor_property('relative_rotation', unreal.Rotator(0, 0, 0))
            obj.set_editor_property('relative_scale3d', scale_vec)
            # Stop editor anim preview stretching bounds to huge sizes.
            try:
                obj.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                obj.set_editor_property('anim_class', None)
            except Exception:
                pass
            try:
                obj.set_editor_property('visibility_based_anim_tick_option',
                                        unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
            except Exception:
                pass

        if name == 'AmmoCounter' and isinstance(obj, unreal.WidgetComponent):
            obj.set_editor_property('draw_size', unreal.IntPoint(64, 32))
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
    log(f'weapon {bp_path.split("/")[-1]} status={bp.status}')


def quarantine_broken_motion_controller():
    """Remove broken SteamVR component so compile errors stop spamming saves."""
    bp = unreal.load_asset(BROKEN_PAWN)
    if not bp:
        log('BP_MotionController missing')
        return
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    removed = 0
    for h in list(sub.k2_gather_subobject_data_for_blueprint(bp) or []):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or '')
        if 'SteamVR' in name or name == 'SteamVRChaperone':
            try:
                sub.delete_subobject(h)
                removed += 1
                log(f'deleted subobject {name}')
            except Exception as exc:
                log(f'could not delete {name}: {exc}')
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(BROKEN_PAWN)
    log(f'BP_MotionController status={bp.status} (errors may remain; not used by BP_XRPawn)')


log('=== FIX GUNVR ISSUES ===')

quarantine_broken_motion_controller()
for path in WEAPON_BPS:
    fix_weapon_blueprint(path)

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
    scale_vec = unreal.Vector(GUN_MESH_SCALE, GUN_MESH_SCALE, GUN_MESH_SCALE)
    actor.set_actor_scale3d(scale_vec)
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.get_name() == 'GunMesh':
            comp.set_editor_property('relative_scale3d', scale_vec)
    dim = gun_mesh_dim(actor)
    log(f'placed {label} gun_mesh_dim={dim}')
    placed += 1

unreal.EditorLevelLibrary.save_current_level()
log(f'DONE placed={placed} target_dim~{40}-{50} (scale={GUN_MESH_SCALE})')
