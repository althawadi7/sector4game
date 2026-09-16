# Checkpoint 20260916_TeleporterStandInside

Stand-inside-only stage teleporter.

## Fix
- BP_StageTeleporter distance gate was broken: both GetActorLocation nodes used Self, so XY distance was always 0 and teleport fired on any trigger touch.
- Wired ActorBeginOverlap.OtherActor into the pawn location node.
- Added MaxInsideDist (default 40 cm) and compare VSizeXY(other - self) <= MaxInsideDist before the busy/teleport chain.
- Shrunk Trigger box to 30x30x80 at Z=85 so you must step onto the pad.

## Assets
- /Game/Sector4/Shared/Gameplay/BP_StageTeleporter
- /Game/XRFramework/Levels/L_XRTemplate (instance trigger matched)

