"""
Fix GunVR compile errors + replace XR guns with GunVR weapons.
Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/fix_gunvr_everything.py"
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

GUN_MESH_SCALE = 0.55
SCALE_VEC = unreal.Vector(GUN_MESH_SCALE, GUN_MESH_SCALE, GUN_MESH_SCALE)

WEAPON_BPS = [
    '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
]

CORE_BPS = [
    '/Game/Weapons/Core/Magazine',
    '/Game/Weapons/Core/WeaponBase',
    '/Game/VirtualRealityBP/Blueprints/BP_MotionController',
    '/Game/VirtualRealityBP/Blueprints/VRGunPawn',
    '/Game/Weapons/Core/SprayCan',
]

ANIM_BPS = [
    '/Game/VirtualReality/Mannequin/Animations/AnimBP_RightHand',
    '/Game/VirtualReality/Mannequin/Animations/AnimBP_TriggerHand',
    '/Game/Weapons/AK47/Mesh/AnimBP_AK47',
    '/Game/Weapons/UMP45/Mesh/AnimBP_UMP45',
    '/Game/Weapons/M14/Mesh/AnimBP_M14',
    '/Game/Weapons/Stakeout/Mesh/AnimBP_Stakeout',
]

OLD_GUN_ASSETS = [
    '/Game/XRFramework/Blueprints/BP_Pistol',
    '/Game/XRFramework/Blueprints/BP_Rifle',
    '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
]

TABLE_SPAWNS = [
    ('GunVR_UMP45_00', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-500, 470, 71), unreal.Rotator(-90, 0, 0)),
    ('GunVR_UMP45_01', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-485, 415, 76), unreal.Rotator(-90, 0, 0)),
    ('GunVR_AK47_00', '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
     unreal.Vector(-463.79, 450.61, 71.3), unreal.Rotator(90, 0, 0)),
    ('GunVR_AK47_01', '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
     unreal.Vector(-437.36, 430.75, 76.24), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Stakeout_00', '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
     unreal.Vector(-520.78, 287.55, 64.72), unreal.Rotator(-90, 0, 0)),
    ('GunVR_UMP45_02', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-500, 320, 71), unreal.Rotator(-90, 0, 0)),
]

BAD_NODE_KEYWORDS = (
    'Motion Controller', 'MotionController', 'ControllerMesh', 'SteamVR',
    'Project Point to Navigation', 'ProjectPointToNavigation', 'Get Bounds',
    'MinAreaRectangle', 'Set Hand', 'Spray Can', 'Spraying', 'Teleporter',
    'Teleport', 'Chaperone', 'Navigation',
)

HIDE_MESH = ('T_Hand_L', 'T_Hand_R', 'GripHand')


def log(msg):
    print(msg)


def compile_bp(path):
    bp = unreal.load_asset(path)
    if not bp or bp.get_class().get_name() != 'Blueprint':
        return bp, None
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp, bp.status


def strip_broken_nodes(bp_path):
    bp = unreal.load_asset(bp_path)
    if not bp:
        return 0
    bel = unreal.BlueprintEditorLibrary
    graphs = []
    for fn in ('list_graph_names', 'get_graph_names'):
        f = getattr(bel, fn, None)
        if callable(f):
            try:
                graphs = list(f(bp) or [])
                break
            except Exception:
                pass
    if not graphs:
        graphs = ['EventGraph', 'UserConstructionScript']
    removed = 0
    for gname in graphs:
        try:
            ed, _ = bo._editor_for(bp, gname)
        except Exception:
            continue
        to_remove = []
        for node in list(ed.list_all_nodes() or []):
            title = bo._node_title(node)
            if any(k in title for k in BAD_NODE_KEYWORDS):
                to_remove.append(node)
                continue
            if 'Cast' in title:
                to_remove.append(node)
        if to_remove:
            ed.remove_nodes(to_remove)
            removed += len(to_remove)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path)
    log(f'strip {bp_path.split("/")[-1]} removed={removed} status={bp.status}')
    return removed


def fix_weapon_template(bp_path):
    bp = unreal.load_asset(bp_path)
    if not bp:
        return
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    grab_cls = unreal.load_asset('/Game/XRFramework/Blueprints/BP_GrabComponent').generated_class()
    has_grab = False
    gunmesh_h = None

    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or '')
        obj = lib.get_object(data)
        if 'Grab' in name:
            has_grab = True
        if name == 'GunMesh':
            gunmesh_h = h
            if isinstance(obj, unreal.SkeletalMeshComponent):
                obj.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
                obj.set_editor_property('relative_scale3d', SCALE_VEC)
                try:
                    obj.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                    obj.set_editor_property('anim_class', None)
                except Exception:
                    pass
        if name == 'AmmoCounter' and isinstance(obj, unreal.WidgetComponent):
            obj.set_editor_property('draw_size', unreal.IntPoint(64, 32))
            obj.set_editor_property('relative_scale3d', unreal.Vector(0.01, 0.01, 0.01))
            obj.set_editor_property('hidden_in_game', True)
        if name in HIDE_MESH and isinstance(obj, unreal.SkeletalMeshComponent):
            obj.set_editor_property('hidden_in_game', True)
            obj.set_editor_property('visible', False)

    if not has_grab and gunmesh_h and grab_cls:
        params = unreal.AddNewSubobjectParams()
        params.parent_handle = gunmesh_h
        params.new_class = grab_cls
        params.blueprint_context = bp
        sub.add_new_subobject(params)

    compile_bp(bp_path)
    unreal.EditorAssetLibrary.save_asset(bp_path)


def cdo_component_count(bp_path):
    bp = unreal.load_asset(bp_path)
    if not bp or bp.get_class().get_name() != 'Blueprint':
        return -1
    cdo = unreal.get_default_object(bp.generated_class())
    return len(cdo.get_components_by_class(unreal.ActorComponent))


log('=== FIX GUNVR EVERYTHING ===')

# 1) Strip broken SteamVR / nav nodes from core blueprints
for p in CORE_BPS:
    strip_broken_nodes(p)

for p in ANIM_BPS:
    bp, st = compile_bp(p)
    if bp and st != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log(f'AnimBP skip {p.split("/")[-1]} status={st}')

# 2) Recompile dependency chain
for p in ['/Game/UI/WB_AmmoCounter', '/Game/Weapons/Core/Magazine',
          '/Game/Weapons/Core/WeaponBase'] + WEAPON_BPS:
    bp, st = compile_bp(p)
    log(f'compile {p.split("/")[-1]} {st} cdo={cdo_component_count(p)}')

# 3) Fix weapon templates + grab for BP_XRPawn
for p in WEAPON_BPS:
    fix_weapon_template(p)
    log(f'fixed {p.split("/")[-1]} cdo={cdo_component_count(p)}')

# 4) Remove ALL old + broken gun actors
removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    cn = actor.get_class().get_name()
    label = actor.get_actor_label()
    if any(x in cn for x in ['BP_Pistol', 'BP_Rifle', 'BP_GrenadeLauncher', 'Weapon_UMP', 'Weapon_AK', 'Weapon_Stake', 'Weapon_37']):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
    elif label.startswith('GunVR_'):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
log(f'removed {removed} gun actors')

# 5) Spawn GunVR guns
placed = 0
for label, path, loc, rot in TABLE_SPAWNS:
    bp = unreal.load_asset(path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log(f'SKIP {label} status={bp.status if bp else None} cdo={cdo_component_count(path)}')
        continue
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), loc, rot)
    actor.set_actor_label(label)
    actor.set_actor_scale3d(SCALE_VEC)
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if 'Gun' in c.get_name():
            c.set_editor_property('relative_scale3d', SCALE_VEC)
    placed += 1
    log(f'placed {label} comps={len(actor.get_components_by_class(unreal.ActorComponent))}')
log(f'placed {placed} GunVR guns')

# 6) Delete old XR gun blueprints
for path in OLD_GUN_ASSETS:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        ok = unreal.EditorAssetLibrary.delete_asset(path)
        log(f'delete old {path.split("/")[-1]}: {ok}')

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log('DONE — try Play again')
