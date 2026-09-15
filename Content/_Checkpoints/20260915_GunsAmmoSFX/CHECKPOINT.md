# Checkpoint 2026-09-15 — Guns / Ammo / Reload / SFX / Teleporter

Stable stage after restore from Content organize disaster.

## Working
- SciFi pistol + all BP_Rifle children (MG / Shotgun / Sniper / AR) fire
- Ammo depletes; empty click via EmptyFireSFX (not gunshot)
- Grip reload via HeldComponent → RelayReload
- Fire + reload SFX wired (WeaponFireCue / ReloadSFX_*)
- Stage teleporter present; trigger box shrunk
- Lighting restored from Auto6 — **do not delete/dim lights**

## Live assets
- Level: `/Game/XRFramework/Levels/L_XRTemplate`
- Guns: `/Game/XRFramework/Blueprints/BP_Rifle` + `SciFiWeapons/*`
- Grab/Pawn: `BP_GrabComponent`, `BP_XRPawn`
- Teleporter: `/Game/Sector4/Shared/Gameplay/BP_StageTeleporter`

## Restore copies in this folder
Duplicated `*_CHECKPOINT` blueprints/level snapshot for rollback.
