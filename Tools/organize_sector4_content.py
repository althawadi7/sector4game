"""
sector4v2 content organize — GUI-safe (skip corrupt FootPrintsFX Demo / Screen_Damage packs).
"""
from __future__ import annotations

import os
import unreal

CONTENT = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Content"
LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    unreal.log(f"[OrganizeS4] {msg}")


def disk_n(rel: str) -> int:
    p = os.path.join(CONTENT, *rel.split("/"))
    if not os.path.isdir(p):
        return 0
    n = 0
    for _r, _d, fs in os.walk(p):
        for f in fs:
            if f.endswith((".uasset", ".umap")):
                n += 1
    return n


def ensure_dir(path: str) -> None:
    sub = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    try:
        if not sub.does_directory_exist(path):
            sub.make_directory(path)
    except Exception:
        sub.make_directory(path)


def move_dir(src: str, dst: str) -> str:
    sub = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    src_rel = src.replace("/Game/", "")
    dst_rel = dst.replace("/Game/", "")
    src_n = disk_n(src_rel)
    reg_n = len(ar.get_assets_by_path(src, True) or [])
    if src_n == 0 and reg_n == 0:
        log(f"SKIP missing {src}")
        return "skip"
    if disk_n(dst_rel) > 0:
        log(f"SKIP dst nonempty {dst} disk={disk_n(dst_rel)}")
        return "skip"
    ensure_dir(dst.rsplit("/", 1)[0])
    ok = False
    try:
        ok = bool(sub.rename_directory(src, dst))
    except Exception as e:
        log(f"rename_directory exc {src}: {e}")
    if not ok:
        try:
            ok = bool(unreal.EditorAssetLibrary.rename_directory(src, dst))
        except Exception as e:
            log(f"EAL rename_directory exc {src}: {e}")
    after = disk_n(dst_rel)
    if after > 0 or ok:
        log(f"OK move_dir {src} -> {dst} disk={after}")
        return "ok"
    log(f"FAIL move_dir {src} -> {dst}")
    return "fail"


def move_asset(src_pkg: str, dst_pkg: str) -> str:
    sub = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ads = list(ar.get_assets_by_package_name(src_pkg) or [])
    if not ads:
        name = src_pkg.rsplit("/", 1)[-1]
        ad = ar.get_asset_by_object_path(f"{src_pkg}.{name}")
        if ad and ad.is_valid():
            ads = [ad]
    if not ads:
        # already moved?
        if disk_n(dst_pkg.replace("/Game/", "").rsplit("/", 1)[0]) and os.path.isfile(
            os.path.join(CONTENT, *dst_pkg.replace("/Game/", "").split("/")) + ".uasset"
        ):
            log(f"SKIP already {dst_pkg}")
            return "skip"
        log(f"SKIP asset {src_pkg}")
        return "skip"
    ad = ads[0]
    name = str(ad.asset_name)
    dst_path = dst_pkg.rsplit("/", 1)[0]
    ensure_dir(dst_path)
    obj = None
    try:
        obj = unreal.AssetRegistryHelpers.get_asset(ad)
    except Exception:
        obj = None
    if not obj:
        try:
            obj = unreal.load_object(None, f"{ad.package_name}.{name}")
        except Exception:
            obj = None
    ok = False
    if obj:
        rd = unreal.AssetRenameData(obj, dst_path, name)
        ok = bool(unreal.AssetToolsHelpers.get_asset_tools().rename_assets([rd]))
    else:
        try:
            ok = bool(sub.rename_asset(src_pkg, dst_pkg))
        except Exception as e:
            log(f"rename_asset exc {e}")
    log(f"{'OK' if ok else 'FAIL'} asset {src_pkg} -> {dst_pkg}")
    return "ok" if ok else "fail"


def fixup() -> int:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    redirectors = []
    try:
        filt = unreal.ARFilter(
            class_paths=[unreal.TopLevelAssetPath("/Script/CoreUObject", "ObjectRedirector")],
            package_paths=["/Game"],
            recursive_paths=True,
        )
        for ad in ar.get_assets(filt) or []:
            try:
                obj = unreal.AssetRegistryHelpers.get_asset(ad)
                if obj:
                    redirectors.append(obj)
            except Exception:
                pass
    except Exception as e:
        log(f"fixup filter err {e}")
    if not redirectors:
        log("fixup: none")
        return 0
    unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(redirectors)
    log(f"fixup: {len(redirectors)}")
    return len(redirectors)


def main() -> dict:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        ar.scan_paths_synchronous(["/Game/Sector4"], True)
    except Exception as e:
        log(f"scan {e}")

    # Unload project maps
    try:
        unreal.EditorLoadingAndSavingUtils.load_map("/Engine/Maps/Templates/Template_Default")
        log("loaded Template_Default")
    except Exception as e:
        log(f"template {e}")

    for p in [
        "/Game/Sector4",
        "/Game/Sector4/Maps",
        "/Game/Sector4/Weapons",
        "/Game/Sector4/Weapons/Blueprints",
        "/Game/Sector4/Audio",
        "/Game/Sector4/VFX",
        "/Game/_Archive",
        "/Game/_Marketplace",
    ]:
        ensure_dir(p)

    counts = {"ok": 0, "fail": 0, "skip": 0}

    def tally(r: str) -> None:
        counts[r] = counts.get(r, 0) + 1

    # Project moves (avoid FootPrintsFX — corrupt Demo mannequin anims crash editor)
    for src, dst in [
        ("/Game/LBVR/Maps", "/Game/Sector4/Maps/Lobby"),
        ("/Game/XRFramework/Levels", "/Game/Sector4/Maps/Play"),
        ("/Game/Weapons", "/Game/Sector4/Weapons/Kits"),
        ("/Game/NW_MuzzleFX", "/Game/Sector4/VFX/NW_MuzzleFX"),
        ("/Game/TraceVFX", "/Game/Sector4/VFX/TraceVFX"),
        ("/Game/SFX", "/Game/Sector4/Audio/SFX"),
        ("/Game/LBVR", "/Game/Sector4/LBVR"),
        ("/Game/CursorTest", "/Game/_Archive/CursorTest"),
        ("/Game/Blueprints", "/Game/Sector4/Weapons/RootBlueprints"),
    ]:
        tally(move_dir(src, dst))

    # Live BPs (may already be under Sector4)
    for src, dst in [
        ("/Game/XRFramework/Blueprints/BP_Pistol", "/Game/Sector4/Weapons/Blueprints/BP_Pistol"),
        ("/Game/XRFramework/Blueprints/BP_Rifle", "/Game/Sector4/Weapons/Blueprints/BP_Rifle"),
        ("/Game/XRFramework/Blueprints/BP_GrenadeLauncher", "/Game/Sector4/Weapons/Blueprints/BP_GrenadeLauncher"),
        ("/Game/XRFramework/Blueprints/BP_ActorPool", "/Game/Sector4/Weapons/Blueprints/BP_ActorPool"),
        ("/Game/XRFramework/Blueprints/BP_XRGameMode", "/Game/Sector4/Weapons/Blueprints/BP_XRGameMode"),
    ]:
        tally(move_asset(src, dst))

    for name in [
        "BP_Pistol_DEMOVR",
        "BP_Pistol_Fix",
        "BP_Pistol_Fix2",
        "BP_Rifle_DEMOVR",
        "BP_Rifle_RESTORE",
        "BP_Rifle_TEST",
        "BP_Rifle_CHECKPOINT",
        "BP_GrenadeLauncher_DEMOVR",
        "BP_Projectile_DEMOVREF",
    ]:
        tally(
            move_asset(
                f"/Game/XRFramework/Blueprints/{name}",
                f"/Game/_Archive/XRFramework_BP/{name}",
            )
        )

    # Marketplace — skip FootPrintsFX + Screen_Damage_Indicator (corrupt anims)
    marketplace = [
        "AnimStarterPack",
        "Fab",
        "Glock",
        "GunVR",
        "Laboratory",
        "LevelPrototyping",
        "Modular_Scifi_Mechanic_Base",
        "NiagaraExamples",
        "ParagonRampage",
        "Sci-Fi_Weapon_Starter_Pack",
        "SciFiCharacterPack",
        "SciFITrooper_Man_03",
        "SciFiWarrior",
        "SciFiWorld",
        "SoundsOfHorror",
        "StarterContent",
        "VirtualReality",
        "VirtualRealityBP",
        "VRSpectator",
        "XRMannequins",
        "Zombie",
        "Generated_Materials",
    ]
    for name in marketplace:
        tally(move_dir(f"/Game/{name}", f"/Game/_Marketplace/{name}"))

    # Park risky packs under _Marketplace without loading Demo by filesystem note:
    # Leave FootPrintsFX + Screen_Damage_Indicator at root OR move only if rename_directory doesn't load assets.
    for name in ["FootPrintsFX", "Screen_Damage_Indicator"]:
        tally(move_dir(f"/Game/{name}", f"/Game/_Marketplace/{name}"))

    nfix = fixup()
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as e:
        log(f"save {e}")

    verify = {
        "lobby": disk_n("Sector4/Maps/Lobby"),
        "play": disk_n("Sector4/Maps/Play"),
        "kits": disk_n("Sector4/Weapons/Kits"),
        "audioW": disk_n("Sector4/Audio/Weapons"),
        "bps": disk_n("Sector4/Weapons/Blueprints"),
        "marketplace": disk_n("_Marketplace"),
        "archive": disk_n("_Archive"),
    }
    result = {"counts": counts, "fixup": nfix, "verify": verify, "log": LOG}
    out_path = os.path.join(
        r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2\Tools",
        "organize_sector4_last_result.txt",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(str(result))
    log(str({"counts": counts, "verify": verify, "fixup": nfix}))
    return result


RESULT = main()
