# Checkpoint 2026-09-16 — Quest perfect (guns / SFX / smooth)

Verified on Meta Quest 3 standalone: clean, smooth, guns + SFX working.

## Build recipe (keep these)
- `bPackageDataInsideApk=True` (fat APK — do NOT ship APK without content)
- FFR High fixed: `xr.OpenXRFBFoveationLevel=3`, `bIsFBFoveationEnabled=True`
- PPV bloom/AO stripped; fill/spot lights Stationary, no shadows
- Playable content: `L_XRTemplate` + SciFi/Rifle ammo/reload/SFX

## Boot note
This verified playtest booted **directly** into `L_XRTemplate` (no Master PC).
Venue/Master flow uses `L_ClientWait` on Quest — restored in a follow-up commit after this snapshot.

## Rollback
`git checkout <this-commit> -- Config/`
