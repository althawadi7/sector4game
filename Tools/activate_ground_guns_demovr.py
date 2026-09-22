"""
Replace dead rifle/grenade-launcher mesh actors on the ground with working
BP_Rifle / BP_GrenadeLauncher (duplicated from BP_Pistol grab+shoot logic).

Run in demovr Unreal Output Log -> Python:
  exec(open('C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/activate_ground_guns_demovr.py').read())
"""
import unreal

LOG = []
LEVEL = '/Game/XRFramework/Levels/L_XRTemplate'

MESH_HINTS = {
    'rifle': [
        '/Game/XRFramework/Blueprints/BP_Rifle',
        [
            '/Game/Weapons/Rifle/Meshes/SKM_Rifle.SKM_Rifle',
            '/Game/Weapons/Rifle/Meshes/SK_Rifle.SK_Rifle',
            '/Game/Weapons/Rifle/Meshes/SM_Rifle.SM_Rifle',
        ],
    ],
    'grenadelauncher': [
        '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
        [
            '/Game/Weapons/GrenadeLauncher/Meshes/SKM_GrenadeLauncher.SKM_GrenadeLauncher',
            '/Game/Weapons/GrenadeLauncher/Meshes/SK_GrenadeLauncher.SK_GrenadeLauncher',
            '/Game/Weapons/GrenadeLauncher/Meshes/SM_GrenadeLauncher.SM_GrenadeLauncher',
        ],
    ],
}


def log(msg):
    LOG.append(msg)
    unreal.log(str(msg))


def load_first(paths):
    for path in paths:
        asset = unreal.load_asset(path)
        if asset:
            return asset, path
    return None, None


def ensure_blueprint(asset_path):
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return unreal.load_asset(asset_path)
    if asset_path in (
        '/Game/XRFramework/Blueprints/BP_Rifle',
        '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
    ):
        src = '/Game/XRFramework/Blueprints/BP_Pistol'
        if unreal.EditorAssetLibrary.duplicate_asset(src, asset_path):
            log('duplicated ' + src + ' -> ' + asset_path)
            return unreal.load_asset(asset_path)
    return unreal.load_asset(asset_path)


def set_kit_mesh(bp, mesh_paths):
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
    except Exception as exc:
        log('CDO fail ' + bp.get_name() + ': ' + str(exc)[:120])
        return False

    skel_asset, skel_path = load_first(
        [p for p in mesh_paths if 'SKM_' in p or '/SK_' in p]
    )
    static_asset, static_path = load_first([p for p in mesh_paths if 'SM_' in p])

    changed = 0
    for comp in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
        if skel_asset:
            comp.set_editor_property('skeletal_mesh', skel_asset)
            changed += 1
    for comp in cdo.get_components_by_class(unreal.StaticMeshComponent):
        use = static_asset or skel_asset
        if use and isinstance(use, unreal.StaticMesh):
            comp.set_editor_property('static_mesh', use)
            changed += 1

    asset_path = '/Game/XRFramework/Blueprints/' + bp.get_name()
    if changed:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(asset_path)
        log(bp.get_name() + ' mesh set (' + str(changed) + ' comps)')
        return True
    log(bp.get_name() + ' no mesh component found on CDO')
    return False


def compile_save(path):
    bp = unreal.load_asset(path)
    if not bp:
        log('MISSING ' + path)
        return None
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log(path.split('/')[-1] + ' status=' + str(bp.status))
    return bp if bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE else None


def actor_mesh_name(actor):
    names = []
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = comp.get_editor_property('static_mesh')
        if mesh:
            names.append(mesh.get_name().lower())
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = comp.get_editor_property('skeletal_mesh')
        if mesh:
            names.append(mesh.get_name().lower())
    return names


def classify_ground_gun(actor):
    label = actor.get_actor_label().lower()
    names = actor_mesh_name(actor)
    hay = ' '.join([label] + names)
    if 'grenadelauncher' in hay or 'grenade' in hay:
        return 'grenadelauncher'
    if 'rifle' in hay:
        return 'rifle'
    return None


def is_weapon_blueprint(actor):
    cn = actor.get_class().get_name()
    return any(x in cn for x in ['BP_Pistol', 'BP_Rifle', 'BP_GrenadeLauncher'])


log('=== ACTIVATE GROUND GUNS (demovr) ===')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.scan_paths_synchronous(['/Game/XRFramework/Blueprints', '/Game/Weapons'], True)

for key, (bp_path, mesh_paths) in MESH_HINTS.items():
    ensure_blueprint(bp_path)
    bp = unreal.load_asset(bp_path)
    if bp:
        set_kit_mesh(bp, mesh_paths)
    compile_save(bp_path)

if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)

ground_slots = []
removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if is_weapon_blueprint(actor):
        continue
    kind = classify_ground_gun(actor)
    if not kind:
        continue
    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    label = actor.get_actor_label()
    ground_slots.append((kind, loc, rot, label))
    unreal.EditorLevelLibrary.destroy_actor(actor)
    removed += 1
    log('removed dead mesh actor: ' + label)

if not ground_slots:
    log('no ground mesh guns found — using default floor positions')
    ground_slots = [
        ('rifle', unreal.Vector(-520, 350, 12), unreal.Rotator(0, 90, 0), 'BP_Rifle_ground'),
        (
            'grenadelauncher',
            unreal.Vector(-470, 350, 12),
            unreal.Rotator(0, -90, 0),
            'BP_GrenadeLauncher_ground',
        ),
    ]

spawned = 0
for kind, loc, rot, label in ground_slots:
    bp_path, _ = MESH_HINTS[kind]
    bp = unreal.load_asset(bp_path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log('SKIP spawn ' + label + ' — blueprint not ready')
        continue
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        bp.generated_class(), loc, rot
    )
    actor.set_actor_label(label if label else ('BP_' + kind + '_ground'))
    log('spawned working ' + actor.get_actor_label() + ' at ' + str(loc))
    spawned += 1

unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log('DONE — removed ' + str(removed) + ' mesh-only guns, spawned ' + str(spawned) + ' working guns')
log('Play VR Preview: grab with grip, shoot with trigger (same as table pistols)')
RESULT = LOG
