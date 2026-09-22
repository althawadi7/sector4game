"""
After copy_gunvr_to_sector4v2.ps1: scan migrated GunVR assets, compile in dependency order,
place test spawns (does NOT touch XRFramework BP_Pistol/BP_Rifle/BP_GrenadeLauncher).
Run in Unreal Output Log:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/migrate_gunvr_import.py"
"""
import unreal

LOG = []
SCAN_PATHS = [
    '/Game/VirtualRealityBP',
    '/Game/VirtualReality',
    '/Game/Blueprints',
    '/Game/Weapons',
    '/Game/Glock',
    '/Game/FX',
    '/Game/Effects',
    '/Game/AnimStarterPack',
    '/Game/StarterContent',
    '/Game/UI',
]

# Compile parents before children.
COMPILE_ORDER = [
    '/Game/UI/WB_AmmoCounter',
    '/Game/Weapons/Core/Magazine',
    '/Game/Weapons/Core/WeaponBase',
    '/Game/VirtualRealityBP/Blueprints/BP_MotionController',
    '/Game/VirtualRealityBP/Blueprints/VRGunPawn',
    '/Game/Weapons/AK47/Blueprint/Magazine_AK47',
    '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    '/Game/Weapons/M14/Blueprint/Weapon_M14',
    '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
    '/Game/Blueprints/Projectiles/Projectile',
]

TEST_SPAWNS = [
    ('GunVR_Weapon_AK47', '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
     unreal.Vector(-600, 470, 71), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_UMP45', '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
     unreal.Vector(-600, 415, 71), unreal.Rotator(-90, 0, 0)),
    ('GunVR_Weapon_Stakeout', '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
     unreal.Vector(-600, 360, 71), unreal.Rotator(-90, 0, 0)),
]


def log(msg):
    LOG.append(msg)
    print(msg)


def compile_bp(path):
    bp = unreal.load_asset(path)
    if not bp:
        log(f'MISSING {path}')
        return None
    if bp.get_class().get_name() != 'Blueprint':
        log(f'SKIP non-blueprint {path}')
        return bp
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log(f'{path.split("/")[-1]} status={bp.status}')
    return bp


log('=== MIGRATE GUNVR IMPORT ===')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

ar = unreal.AssetRegistryHelpers.get_asset_registry()
for path in SCAN_PATHS:
    ar.scan_paths_synchronous([path], True)
    assets = ar.get_assets_by_path(path, recursive=True)
    log(f'scan {path}: {len(assets)} assets')

for bp_path in COMPILE_ORDER:
    try:
        compile_bp(bp_path)
    except Exception as exc:
        log(f'COMPILE FAIL {bp_path}: {exc}')

removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if actor.get_actor_label().startswith('GunVR_'):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
log(f'removed {removed} old GunVR test actors')

placed = 0
for label, path, loc, rot in TEST_SPAWNS:
    bp = unreal.load_asset(path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log(f'SKIP spawn {label} status={bp.status if bp else None}')
        continue
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), loc, rot)
    actor.set_actor_label(label)
    placed += 1
    log(f'placed {label}')

unreal.EditorLevelLibrary.save_current_level()
log(f'DONE placed={placed} (XRFramework guns untouched)')
RESULT = LOG
