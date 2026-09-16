# Checkpoint 2026-09-16 — Stage org + Stage2 teleport/nav

Pre-Quest-perf rollback point.

## Included
- L_XRTemplate Outliner folders (Lighting / Models / Stages / Gameplay)
- Stage 2 = teleport destination pad (moved out) + SM_Teleport2 / Stage2_TeleportLanding
- NavMeshBoundsVolume_Stage2 (Quest locomotion teleport works on Stage 2)
- Stage1 local DecorFill lights under Stages/Stage1/Lighting
- Global sky/sun left global

## Rollback
git checkout  <this-commit> -- Content/XRFramework/Levels/ Config/
Or reset hard to this commit if needed.

## Do NOT use for
Post-this-commit Quest FFR / PPV / light-mobility perf experiments — those come after.
