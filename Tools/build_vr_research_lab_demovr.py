"""
Build sci-fi lab on the CURRENTLY OPEN level. No load_map. No duplicate. No crash.

1. Open L_XRTemplate in Unreal (your guns + VR level)
2. Run ONCE:
   py C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/build_vr_research_lab_demovr.py
3. File -> Save Current Level As -> L_VR_ResearchLab (optional, manual)

Preserves: guns, VR, nav, lights. Removes only template cubes/floors.
"""
import gc

import unreal

LOG = []
PLAY_HALF_X = 1500.0
PLAY_HALF_Y = 750.0
CEILING_Z = 350.0
TILE = 350.0

FLOOR_MESH = "/Game/SciFiWorld/Modules/Meshes/SM_MFloor02-350x350-1"
WALL_MESH = "/Game/SciFiWorld/Modules/Meshes/SM_MWall03-350x350-1"
CEILING_MESH = "/Game/SciFiWorld/Modules/Meshes/SM_MCeiling03-350x350-1"

PRESERVE = [
    "PlayerStart", "VRSpectator", "Passthrough", "Pistol", "Rifle",
    "GrenadeLauncher", "RecastNavMesh", "NavMeshBounds", "NavModifier",
    "DirectionalLight", "SkyLight", "SkySphere", "PointLight",
    "ReflectionCapture", "LightmassImportance", "WorldSettings", "Brush",
    "InstancedFoliage",
]
REMOVE = ["TemplateFloor", "1M_Cube", "Cube_FireLog", "Cube13", "Fire_Cue", "TextRenderActor"]

LAB_BPS = [
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule01", unreal.Vector(-1200, -500, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule02_1", unreal.Vector(-1200, 0, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule02_2", unreal.Vector(-1200, 500, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule05", unreal.Vector(1200, -500, 0), 180),
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule10", unreal.Vector(1200, 0, 0), 180),
    ("/Game/SciFiWorld/Blueprints/BP_LabCapsule11_1", unreal.Vector(1200, 500, 0), 180),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien01-Hologram", unreal.Vector(-900, -600, 0), 90),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien02-Hologram", unreal.Vector(-900, 600, 0), 90),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien03-Hologram", unreal.Vector(900, -600, 0), -90),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien04-Hologram", unreal.Vector(900, 600, 0), -90),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien05-Hologram", unreal.Vector(0, -650, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_CreatureAlien06-Hologram", unreal.Vector(0, 650, 0), 180),
    ("/Game/SciFiWorld/Blueprints/BP_LabHoloProjector01", unreal.Vector(-600, -550, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabHoloProjector01", unreal.Vector(-600, 550, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabHoloProjector01", unreal.Vector(600, -550, 0), 0),
    ("/Game/SciFiWorld/Blueprints/BP_LabHoloProjector01", unreal.Vector(600, 550, 0), 0),
]

LAB_MESHES = [
    ("/Game/SciFiWorld/Meshes/SM_LabDesk03_2", unreal.Vector(200, 0, 0), unreal.Rotator(0, -90, 0)),
    ("/Game/SciFiWorld/Meshes/SM_Chair09", unreal.Vector(350, 0, 0), unreal.Rotator(0, 90, 0)),
    ("/Game/SciFiWorld/Modules/Meshes/SM_MFloor02-Steps-50-1", unreal.Vector(-400, 0, 0), unreal.Rotator(0, 90, 0)),
    ("/Game/SciFiWorld/Modules/Meshes/SM_MFloor01-700x350-1", unreal.Vector(-400, 0, 50), unreal.Rotator(0, 90, 0)),
]


def log(m):
    LOG.append(str(m))
    unreal.log(str(m))


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def kept(a):
    n, c = a.get_name(), a.get_class().get_name()
    return any(x in n or x in c for x in PRESERVE)


def junk(a):
    if kept(a):
        return False
    n = a.get_name()
    return n.startswith("LabEnv_") or n.startswith("VR_PlayBoundary_") or any(x in n for x in REMOVE)


def tiles(span):
    n = max(1, int(round(span / TILE)))
    s = -((n - 1) * TILE) * 0.5
    return [s + i * TILE for i in range(n)]


def smesh(path, loc, rot=None, label="LabEnv"):
    m = unreal.load_asset(path)
    if not m:
        return
    a = actors().spawn_actor_from_class(unreal.StaticMeshActor, loc, rot or unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(m)


def sbp(path, loc, yaw, label):
    bp = unreal.load_asset(path)
    if not bp:
        return
    a = actors().spawn_actor_from_class(bp.generated_class(), loc, unreal.Rotator(0, yaw, 0))
    a.set_actor_label(label)


log("=== BUILD LAB (safe) on " + unreal.EditorLevelLibrary.get_editor_world().get_name() + " ===")

for a in list(actors().get_all_level_actors()):
    if junk(a):
        actors().destroy_actor(a)

n = 0
for x in tiles(PLAY_HALF_X * 2):
    for y in tiles(PLAY_HALF_Y * 2):
        smesh(FLOOR_MESH, unreal.Vector(x, y, 0), label="LabEnv_Floor_" + str(n))
        smesh(CEILING_MESH, unreal.Vector(x, y, CEILING_Z), label="LabEnv_Ceil_" + str(n))
        n += 1
log("Floor/ceiling: " + str(n))

for i, (p, l, y) in enumerate(LAB_BPS):
    sbp(p, l, y, "LabEnv_BP_" + str(i))
for i, (p, l, r) in enumerate(LAB_MESHES):
    smesh(p, l, r, "LabEnv_SM_" + str(i))

for a in list(actors().get_all_level_actors()):
    if a.get_name().startswith("VR_PlayBoundary_"):
        actors().destroy_actor(a)
hz = CEILING_Z * 0.5
t = 40.0
for name, loc, sc in [
    ("N", unreal.Vector(0, PLAY_HALF_Y + t * 0.5, hz), unreal.Vector(PLAY_HALF_X / 64, t / 64, hz / 64)),
    ("S", unreal.Vector(0, -PLAY_HALF_Y - t * 0.5, hz), unreal.Vector(PLAY_HALF_X / 64, t / 64, hz / 64)),
    ("E", unreal.Vector(PLAY_HALF_X + t * 0.5, 0, hz), unreal.Vector(t / 64, PLAY_HALF_Y / 64, hz / 64)),
    ("W", unreal.Vector(-PLAY_HALF_X - t * 0.5, 0, hz), unreal.Vector(t / 64, PLAY_HALF_Y / 64, hz / 64)),
]:
    v = actors().spawn_actor_from_class(unreal.BlockingVolume, loc, unreal.Rotator(0, 0, 0))
    v.set_actor_label("VR_PlayBoundary_" + name)
    v.set_actor_scale3d(sc)

vols = [a for a in actors().get_all_level_actors() if isinstance(a, unreal.NavMeshBoundsVolume)]
if vols:
    vols[0].set_actor_scale3d(unreal.Vector(PLAY_HALF_X / 100, PLAY_HALF_Y / 100, 3))

names = [a.get_name() for a in actors().get_all_level_actors()]
for k in ["PlayerStart", "VRSpectator", "Pistol", "Rifle", "GrenadeLauncher"]:
    log(("OK " if any(k in n for n in names) else "MISSING ") + k)

unreal.EditorLevelLibrary.save_current_level()
log("DONE - save level + restart VR Preview")
gc.collect()
