"""
Replace XRFramework table guns with GunVR weapons, delete old gun blueprints.
Keeps BP_XRPawn (grab/zombie flow). Compiles GunVR chain first.

Run in Unreal Output Log after editor is open:
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/replace_guns_with_gunvr.py"
"""
import unreal

LOG = []

OLD_GUN_CLASS_MARKERS = ('BP_Pistol', 'BP_Rifle', 'BP_GrenadeLauncher')
OLD_GUN_ASSETS = [
    '/Game/XRFramework/Blueprints/BP_Pistol',
    '/Game/XRFramework/Blueprints/BP_Rifle',
    '/Game/XRFramework/Blueprints/BP_GrenadeLauncher',
]

# Map old gun type -> GunVR replacement (pistol slot = UMP45, rifle = AK47, grenade = Stakeout shotgun)
REPLACEMENT_BY_OLD = {
    'BP_Pistol': '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    'BP_Rifle': '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    'BP_GrenadeLauncher': '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
}

COMPILE_ORDER = [
    '/Game/UI/WB_AmmoCounter',
    '/Game/Weapons/Core/Magazine',
    '/Game/Weapons/Core/WeaponBase',
    '/Game/VirtualRealityBP/Blueprints/BP_MotionController',
    '/Game/Weapons/AK47/Blueprint/Magazine_AK47',
    '/Game/Weapons/UMP45/Blueprint/Magazine_UMP45',
    '/Game/Weapons/Stakeout/Blueprint/Magazine_Shotgun',
    '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    '/Game/Weapons/M14/Blueprint/Weapon_M14',
    '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
    '/Game/Blueprints/Projectiles/Projectile',
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
        return bp
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log(f'compile {path.split("/")[-1]} -> {bp.status}')
    return bp


def old_gun_kind(class_name):
    for marker in OLD_GUN_CLASS_MARKERS:
        if marker in class_name:
            return marker
    return None


def pick_replacement(kind):
    path = REPLACEMENT_BY_OLD.get(kind)
    if not path:
        return None
    bp = unreal.load_asset(path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        log(f'REPLACEMENT NOT READY {path} status={bp.status if bp else None}')
        return None
    return bp


log('=== REPLACE GUNS WITH GUNVR ===')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

ar = unreal.AssetRegistryHelpers.get_asset_registry()
for root in ['/Game/UI', '/Game/Weapons', '/Game/VirtualRealityBP', '/Game/Blueprints']:
    ar.scan_paths_synchronous([root], True)

for bp_path in COMPILE_ORDER:
    try:
        compile_bp(bp_path)
    except Exception as exc:
        log(f'COMPILE FAIL {bp_path}: {exc}')

# Collect old gun transforms before destroy
slots = []
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    cn = actor.get_class().get_name()
    kind = old_gun_kind(cn)
    if not kind:
        continue
    t = actor.get_actor_transform()
    slots.append((actor.get_actor_label(), kind, t.translation, t.rotation.rotator()))
    log(f'found old {actor.get_actor_label()} ({cn})')

if not slots:
    log('no old guns in level — using default table layout')
    slots = [
        ('GunVR_UMP45_00', 'BP_Pistol', unreal.Vector(-500, 470, 71), unreal.Rotator(-90, 0, 0)),
        ('GunVR_UMP45_01', 'BP_Pistol', unreal.Vector(-485, 415, 76), unreal.Rotator(-90, 0, 0)),
        ('GunVR_AK47_00', 'BP_Rifle', unreal.Vector(-463.79, 450.61, 71.3), unreal.Rotator(90, 0, 0)),
        ('GunVR_AK47_01', 'BP_Rifle', unreal.Vector(-437.36, 430.75, 76.24), unreal.Rotator(-90, 0, 0)),
        ('GunVR_Stakeout_00', 'BP_GrenadeLauncher', unreal.Vector(-520.78, 287.55, 64.72), unreal.Rotator(-90, 0, 0)),
        ('GunVR_Stakeout_01', 'BP_GrenadeLauncher', unreal.Vector(-500, 320, 71), unreal.Rotator(-90, 0, 0)),
    ]

removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    if old_gun_kind(actor.get_class().get_name()):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
log(f'removed {removed} old gun actors')

# Also remove prior GunVR test spawns
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    label = actor.get_actor_label()
    if label.startswith('GunVR_') or label.startswith('BP_Pistol') or label.startswith('BP_Rifle'):
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1

placed = 0
for old_label, kind, loc, rot in slots:
    bp = pick_replacement(kind)
    if not bp:
        continue
    new_name = REPLACEMENT_BY_OLD[kind].split('/')[-1]
    label = f'GunVR_{new_name}_{placed:02d}'
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), loc, rot)
    actor.set_actor_label(label)
    placed += 1
    log(f'placed {label} at {loc} (was {kind})')

unreal.EditorLevelLibrary.save_current_level()
log(f'placed {placed} GunVR weapons')

deleted = 0
for asset_path in OLD_GUN_ASSETS:
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        ok = unreal.EditorAssetLibrary.delete_asset(asset_path)
        log(f'delete {asset_path}: {ok}')
        if ok:
            deleted += 1
    else:
        log(f'skip delete (missing) {asset_path}')

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log(f'DONE removed={removed} placed={placed} deleted_assets={deleted}')
log('NOTE: GunVR guns use their own grab/shoot (WeaponBase). Test on Quest — may need VRGunPawn if grab fails.')
RESULT = LOG
