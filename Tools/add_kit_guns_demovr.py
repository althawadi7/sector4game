"""
Add kit guns to demovr: BP_Rifle + BP_GrenadeLauncher from BP_Pistol logic,
swap to kit meshes, place on VR table. Does NOT modify shoot/input logic.

Run in demovr Unreal (Output Log Python):
  exec(open('C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/add_kit_guns_demovr.py').read())
"""
import unreal

LOG = []
LEVEL = '/Game/XRFramework/Levels/L_XRTemplate'

GUNS = [
    {
        'path': '/Game/XRFramework/Blueprints/BP_Pistol',
        'meshes': [
            '/Game/Weapons/Pistol/Meshes/SKM_Pistol.SKM_Pistol',
            '/Game/Weapons/Pistol/Meshes/SK_Pistol.SK_Pistol',
            '/Game/Weapons/Pistol/Meshes/SM_Pistol.SM_Pistol',
        ],
    },
    {
        'path': '/Game/XRFramework/Blueprints/BP_Rifle',
        'meshes': [
            '/Game/Weapons/Rifle/Meshes/SKM_Rifle.SKM_Rifle',
            '/Game/Weapons/Rifle/Meshes/SK_Rifle.SK_Rifle',
            '/Game/Weapons/Rifle/Meshes/SM_Rifle.SM_Rifle',
        ],
    },
    {
        'path': '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
        'meshes': [
            '/Game/Weapons/GrenadeLauncher/Meshes/SKM_GrenadeLauncher.SKM_GrenadeLauncher',
            '/Game/Weapons/GrenadeLauncher/Meshes/SK_GrenadeLauncher.SK_GrenadeLauncher',
            '/Game/Weapons/GrenadeLauncher/Meshes/SM_GrenadeLauncher.SM_GrenadeLauncher',
        ],
    },
]

GUN_LAYOUT = [
    ('BP_Pistol_00', '/Game/XRFramework/Blueprints/BP_Pistol',
     unreal.Vector(-500, 470, 71), unreal.Rotator(-90, 0, 0)),
    ('BP_Pistol_01', '/Game/XRFramework/Blueprints/BP_Pistol',
     unreal.Vector(-485, 415, 76), unreal.Rotator(-90, 0, 0)),
    ('BP_Rifle_00', '/Game/XRFramework/Blueprints/BP_Rifle',
     unreal.Vector(-463.79, 450.61, 71.3), unreal.Rotator(90, 0, 0)),
    ('BP_Rifle_01', '/Game/XRFramework/Blueprints/BP_Rifle',
     unreal.Vector(-437.36, 430.75, 76.24), unreal.Rotator(-90, 0, 0)),
    ('BP_GrenadeLauncher_00', '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
     unreal.Vector(-520.78, 287.55, 64.72), unreal.Rotator(-90, 0, 0)),
]


def log(msg):
    LOG.append(msg)
    print(msg)


def ensure_blueprint(asset_path):
    """Load blueprint; duplicate from pistol if missing."""
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


def load_first(paths):
    for path in paths:
        asset = unreal.load_asset(path)
        if asset:
            return asset, path
    return None, None


def set_kit_mesh(bp, mesh_paths):
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
    except Exception as exc:
        log('CDO fail ' + bp.get_name() + ': ' + str(exc)[:80])
        return False

    skel_asset, skel_path = load_first([p for p in mesh_paths if 'SKM_' in p or '/SK_' in p])
    static_asset, static_path = load_first([p for p in mesh_paths if 'SM_' in p])

    changed = 0
    for comp in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
        if skel_asset:
            comp.set_editor_property('skeletal_mesh', skel_asset)
            changed += 1
    for comp in cdo.get_components_by_class(unreal.StaticMeshComponent):
        use = static_asset or skel_asset
        if use:
            if isinstance(use, unreal.StaticMesh):
                comp.set_editor_property('static_mesh', use)
            changed += 1

    asset_path = '/Game/XRFramework/Blueprints/' + bp.get_name()
    if changed:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(asset_path)
        log(bp.get_name() + ' mesh set (' + str(changed) + ' comps) using ' + str(skel_path or static_path))
        return True
    log(bp.get_name() + ' no mesh component found on CDO')
    return False


def compile_save(path):
    bp = unreal.load_asset(path)
    if not bp:
        log('MISSING ' + path)
        return False
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log(path.split('/')[-1] + ' status=' + str(bp.status))
    return bp.status == unreal.BlueprintStatus.BS_UP_TO_DATE


log('=== ADD KIT GUNS TO DEMOVR ===')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.scan_paths_synchronous(['/Game/XRFramework/Blueprints', '/Game/Weapons'], True)

for g in GUNS:
    path = g['path']
    ensure_blueprint(path)
    bp = unreal.load_asset(path)
    if bp:
        set_kit_mesh(bp, g['meshes'])
    compile_save(path)

if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
    removed = 0
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        cn = actor.get_class().get_name()
        if any(x in cn for x in ['BP_Pistol', 'BP_Rifle', 'BP_GrenadeLauncher']):
            unreal.EditorLevelLibrary.destroy_actor(actor)
            removed += 1
    log('removed ' + str(removed) + ' old table guns')

    for label, path, loc, rot in GUN_LAYOUT:
        bp = unreal.load_asset(path)
        if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
            log('SKIP ' + label)
            continue
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            bp.generated_class(), loc, rot)
        actor.set_actor_label(label)
        log('placed ' + label)
    unreal.EditorLevelLibrary.save_current_level()
else:
    log('Level not found: ' + LEVEL)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log('DONE — Play, grab each gun, tap trigger (same logic as pistol)')
RESULT = LOG
