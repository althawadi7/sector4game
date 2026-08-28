# sector4game (sector4v2)

Lean Git sync for the VR shooter project. **~45 MB** on GitHub — not the full ~9 GB project.

## What IS in git

| Area | Why |
|------|-----|
| `Config/` | Engine, input, game settings |
| `Content/XRFramework/Blueprints/` | Guns, game mode, VR logic |
| `Content/XRFramework/Levels/` | `L_XRTemplate` — lighting, gun placement |
| `Content/XRFramework/Input/` | Enhanced Input (IA/IMC) |
| `Content/XRFramework/VFX`, `Materials`, `Audio`, `UI` | Small gameplay assets |
| `Content/Zombie/Blueprints/` | Spawner, zombie AI logic |
| `Content/Weapons/` | Weapon meshes (small) |
| `Plugins/`, `Tools/`, `Content/Python/` | Project tooling |

## What is NOT in git (keep local)

Marketplace packs: Paragon, NiagaraExamples, Laboratory, SciFiWorld, zombie textures/audio, FootPrintsFX, etc.

## Roll back weapons / level

```powershell
git checkout restored-aug28
```

Or browse commits: `git log --oneline`

## Clone on another PC

1. Clone this repo
2. Copy marketplace Content folders from your backup / original project
3. Open `sector4v2.uproject` in UE 5.8

## Git LFS

Blueprints and levels use Git LFS (fits GitHub free tier for this lean set).
