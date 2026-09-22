"""Remove broken GunVR blueprints that block Play (SteamVR/Oculus — not used by BP_GunVR_UMP45).
Run: py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/remove_broken_gunvr_compile_blockers.py"
"""
import unreal

BROKEN = [
    "/Game/VirtualReality/Mannequin/Animations/AnimBP_RightHand",
    "/Game/VirtualReality/Mannequin/Animations/AnimBP_TriggerHand",
    "/Game/VirtualRealityBP/Blueprints/BP_MotionController",
    "/Game/VirtualRealityBP/Blueprints/VRGunPawn",
    "/Game/Weapons/AK47/Animations/AnimBP_AK47",
    "/Game/Weapons/Core/Magazine",
    "/Game/Weapons/Core/WeaponBase",
    "/Game/Weapons/M14/Animations/AnimBP_M14",
    "/Game/Weapons/Stakeout/Animations/AnimBP_Stakeout",
    "/Game/Weapons/UMP45/Animations/AnimBP_UMP45",
]
REDIRECTORS = [
    "/Game/Blueprints/Magazines/Magazine",
    "/Game/Blueprints/Weapons/Weapon",
    "/Game/Blueprints/Weapons/WeaponBase",
    "/Game/VirtualRealityBP/Blueprints/MotionControllerPawn",
]
# Orphan GunVR UI/interaction BPs that error after core delete
ORPHANS = [
    "/Game/Blueprints/Weapons/Attachments/AttachmentBase",
    "/Game/Blueprints/Misc/AttachmentVolume",
    "/Game/Blueprints/Weapons/WeaponInteractions/Blueprints/WI_FireModeSelector",
    "/Game/Blueprints/Weapons/WeaponInteractions/Blueprints/WI_PumpAction",
    "/Game/UI/UI_GunPaintSelector",
    "/Game/UI/WB_AmmoCounter",
    "/Game/Weapons/Core/AmmoBeltMagazine",
    "/Game/Weapons/Core/WeaponSlider",
]
# GunVR paint/ammo UI — references deleted Magazine/PaintableWeapon
PAINT_AMMO = [
    "/Game/UI/PaintRoomSelector",
    "/Game/VirtualRealityBP/Blueprints/BP_AmmoBelt",
    "/Game/Weapons/Core/PaintableWeapon",
    "/Game/Weapons/Core/SprayCan",
    "/Game/Blueprints/Magazines/AmmoBeltMagazine_Shotgun",
    "/Game/Blueprints/Magazines/AmmoBeltMagazine_UMP45",
    "/Game/Weapons/Core/VRSaveGame",
    "/Game/Weapons/AK47/Blueprint/AmmoBeltMagazine_AK47",
    "/Game/Weapons/UMP45/Blueprint/Magazine_UMP45",
    "/Game/Weapons/AK47/Blueprint/Magazine_AK47",
    "/Game/Weapons/M14/Blueprint/Magazine_M14",
    "/Game/Weapons/Stakeout/Blueprint/Magazine_Shotgun",
]
# Native GunVR weapons (we use /Game/GunVR/BP_GunVR_* instead)
NATIVE_WEAPONS = [
    "/Game/Weapons/UMP45/Blueprint/Weapon_UMP45",
    "/Game/Weapons/AK47/Blueprint/Weapon_AK47",
    "/Game/Weapons/M14/Blueprint/Weapon_M14",
    "/Game/Weapons/Stakeout/Blueprint/Weapon_Stakeout",
    "/Game/Weapons/UMP45/Blueprint/Projectile_UMP45",
    "/Game/Weapons/AK47/Blueprint/Projectile_AK47",
    "/Game/Weapons/M14/Blueprint/Projectile_M14",
    "/Game/Blueprints/Weapons/Weapon_UMP45",
    "/Game/Blueprints/Weapons/Weapon_AK47",
    "/Game/Blueprints/Weapons/Weapon_37Stakeout",
    "/Game/VirtualRealityBP/Blueprints/HMDLocomotionPawn",
    "/Game/VirtualRealityBP/Blueprints/PickupActorInterface",
]

deleted = 0
for path in BROKEN + REDIRECTORS + ORPHANS + PAINT_AMMO + NATIVE_WEAPONS:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if unreal.EditorAssetLibrary.delete_asset(path):
            print("deleted", path)
            deleted += 1
        else:
            print("FAILED", path)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

ar = unreal.AssetRegistryHelpers.get_asset_registry()
remaining = []
for ap in ar.get_all_assets():
    cls = str(ap.asset_class_path.asset_name)
    if cls not in ("Blueprint", "AnimBlueprint", "WidgetBlueprint"):
        continue
    pkg = str(ap.package_name)
    a = unreal.load_asset(pkg)
    if a and getattr(a, "status", None) == unreal.BlueprintStatus.BS_ERROR:
        remaining.append(pkg)

print("deleted", deleted)
print("remaining BS_ERROR", remaining or "none")
gun = unreal.load_asset("/Game/GunVR/BP_GunVR_UMP45")
print("BP_GunVR_UMP45", gun.status if gun else "MISSING")
