"""
Restore working XRFramework guns from git and respawn on weapon table.
Run AFTER closing save-error dialogs (or restart Unreal once).
  py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/restore_xr_guns_from_git.py"
"""
import unreal
import subprocess

PROJECT = r"C:\Users\Rashid AlAwadhi\Documents\Unreal Projects\sector4v2"
GUNS = [
    "Content/XRFramework/Blueprints/BP_Pistol.uasset",
    "Content/XRFramework/Blueprints/BP_Rifle.uasset",
    "Content/XRFramework/Blueprints/BP_GrenadeLauncher.uasset",
]

TABLE = [
    ("BP_Pistol_00", "/Game/XRFramework/Blueprints/BP_Pistol",
     unreal.Vector(-500, 470, 71), unreal.Rotator(-90, 0, 0)),
    ("BP_Pistol_01", "/Game/XRFramework/Blueprints/BP_Pistol",
     unreal.Vector(-485, 415, 76), unreal.Rotator(-90, 0, 0)),
    ("BP_Rifle_00", "/Game/XRFramework/Blueprints/BP_Rifle",
     unreal.Vector(-463.79, 450.61, 71.3), unreal.Rotator(90, 0, 0)),
    ("BP_Rifle_01", "/Game/XRFramework/Blueprints/BP_Rifle",
     unreal.Vector(-437.36, 430.75, 76.24), unreal.Rotator(-90, 0, 0)),
    ("BP_GrenadeLauncher_00", "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
     unreal.Vector(-520.78, 287.55, 64.72), unreal.Rotator(-90, 0, 0)),
    ("BP_GrenadeLauncher_01", "/Game/XRFramework/Blueprints/BP_GrenadeLauncher",
     unreal.Vector(-500, 320, 71), unreal.Rotator(-90, 0, 0)),
]

print("=== RESTORE XR GUNS FROM GIT ===")
r = subprocess.run(["git", "checkout", "HEAD", "--"] + GUNS, cwd=PROJECT, capture_output=True, text=True)
print(r.stdout or r.stderr or "git ok")

ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.scan_paths_synchronous(["/Game/XRFramework/Blueprints"], True)

for path in ["/Game/XRFramework/Blueprints/BP_Pistol",
             "/Game/XRFramework/Blueprints/BP_Rifle",
             "/Game/XRFramework/Blueprints/BP_GrenadeLauncher"]:
    bp = unreal.load_asset(path)
    if bp:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        print(path.split("/")[-1], bp.status)

removed = 0
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
    cn = actor.get_class().get_name()
    label = actor.get_actor_label()
    if "Weapon_" in cn or label.startswith("GunVR_") or "BP_Pistol" in cn or "BP_Rifle" in cn or "BP_GrenadeLauncher" in cn:
        unreal.EditorLevelLibrary.destroy_actor(actor)
        removed += 1
print(f"removed {removed} gun actors")

placed = 0
for label, path, loc, rot in TABLE:
    bp = unreal.load_asset(path)
    if not bp or bp.status != unreal.BlueprintStatus.BS_UP_TO_DATE:
        print(f"SKIP {label} status={bp.status if bp else None}")
        continue
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), loc, rot)
    actor.set_actor_label(label)
    placed += 1
    print(f"placed {label}")

unreal.EditorLevelLibrary.save_current_level()
print(f"DONE placed={placed} XR guns (correct VR size + grab/shoot)")
