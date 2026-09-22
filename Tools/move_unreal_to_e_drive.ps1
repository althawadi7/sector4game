# Safe move of Unreal data from C: to E: using directory junctions.
# Old paths keep working — Cursor, Epic, and project links stay valid.
#
# Close Unreal Editor and Epic Launcher before running.
# Run PowerShell as Administrator if you also want Epic Launcher cache moved.
#
#   powershell -ExecutionPolicy Bypass -File "E:\Unreal Projects\sector4v2\Tools\move_unreal_to_e_drive.ps1"
#   powershell -ExecutionPolicy Bypass -File "...\move_unreal_to_e_drive.ps1" -SkipProjects
#   powershell -ExecutionPolicy Bypass -File "...\move_unreal_to_e_drive.ps1" -ProjectsOnly

param(
    [switch]$SkipProjects,
    [switch]$ProjectsOnly,
    [switch]$SkipTempRedirect
)

$ErrorActionPreference = "Stop"
$LogFile = "E:\UnrealEngine\move_to_e_log.txt"
New-Item -ItemType Directory -Force -Path "E:\UnrealEngine" | Out-Null

function Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Get-FolderSizeGB($path) {
    if (-not (Test-Path $path)) { return 0 }
    $sum = (Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    return [math]::Round($sum / 1GB, 2)
}

function Move-FolderWithJunction {
    param(
        [Parameter(Mandatory)] [string]$Source,
        [Parameter(Mandatory)] [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        Log "SKIP (not found): $Source"
        return
    }

    $item = Get-Item $Source -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Log "SKIP (already a junction): $Source -> $(($item.Target -join '; '))"
        return
    }

    if (Test-Path $Destination) {
        throw "Destination already exists: $Destination"
    }

    $beforeGB = Get-FolderSizeGB $Source
    Log "Moving ${beforeGB} GB: $Source -> $Destination"

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    & robocopy $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:3 /NFL /NDL /NP /NJH /NJS
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        throw "robocopy failed ($rc) for $Source"
    }

    Remove-Item -LiteralPath $Source -Recurse -Force
    cmd /c "mklink /J `"$Source`" `"$Destination`""
    if ($LASTEXITCODE -ne 0) {
        throw "mklink failed for $Source"
    }

    Log "OK junction: $Source -> $Destination"
}

function Clear-OldTempFiles {
    param([string]$TempRoot = $env:TEMP, [int]$DaysOld = 5)
    if (-not (Test-Path $TempRoot)) { return 0 }

    $cutoff = (Get-Date).AddDays(-$DaysOld)
    $freed = 0
    Get-ChildItem $TempRoot -Force -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            if ($_.LastWriteTime -lt $cutoff) {
                $size = if ($_.PSIsContainer) { Get-FolderSizeGB $_.FullName } else { $_.Length / 1GB }
                Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop
                $freed += $size
                Log ("Removed old temp: {0} ({1:N2} GB)" -f $_.Name, $size)
            }
        } catch {
            Log ("Could not remove temp item: {0} ({1})" -f $_.FullName, $_.Exception.Message)
        }
    }
    return $freed
}

Log "=== Move Unreal data C: -> E: ==="
$freeBefore = (Get-Volume C).SizeRemaining / 1GB
Log ("C: free before: {0:N1} GB" -f $freeBefore)

if (-not $SkipTempRedirect) {
    New-Item -ItemType Directory -Force -Path "E:\Temp" | Out-Null
    [Environment]::SetEnvironmentVariable("TEMP", "E:\Temp", "User")
    [Environment]::SetEnvironmentVariable("TMP", "E:\Temp", "User")
    $env:TEMP = "E:\Temp"
    $env:TMP = "E:\Temp"
    Log "TEMP/TMP redirected to E:\Temp (helps Epic Android downloads)"
}

if (-not $ProjectsOnly) {
    Log "--- Clean old TEMP files on C (5+ days) ---"
    $oldTemp = "C:\Users\Rashid AlAwadhi\AppData\Local\Temp"
    $freed = Clear-OldTempFiles -TempRoot $oldTemp -DaysOld 5
    Log ("Temp cleanup freed about {0:N1} GB" -f $freed)

    Log "--- Derived Data Cache ---"
    Move-FolderWithJunction `
        -Source "C:\Users\Rashid AlAwadhi\AppData\Local\UnrealEngine\Common\DerivedDataCache" `
        -Destination "E:\UnrealEngine\DerivedDataCache"

    Log "--- Android SDK ---"
    Move-FolderWithJunction `
        -Source "C:\Users\Rashid AlAwadhi\AppData\Local\Android\Sdk" `
        -Destination "E:\Dev\Android\Sdk"

    # Epic download cache (~19 GB) — needs admin for ProgramData junction
    $epicCache = "C:\ProgramData\Epic\EpicGamesLauncher"
    $epicDest  = "E:\Epic\EpicGamesLauncher"
    if ((Test-Path $epicCache) -and -not (Get-Item $epicCache -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) {
        $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) {
            Log "--- Epic Launcher cache (ProgramData) ---"
            Move-FolderWithJunction -Source $epicCache -Destination $epicDest
        } else {
            Log "SKIP Epic cache (run script as Administrator to move C:\ProgramData\Epic\EpicGamesLauncher)"
        }
    }
}

if (-not $SkipProjects) {
    Log "--- Unreal Projects (largest move, ~90+ GB) ---"
    Move-FolderWithJunction `
        -Source "C:\Users\Rashid AlAwadhi\Documents\Unreal Projects" `
        -Destination "E:\Unreal Projects"
}

$freeAfter = (Get-Volume C).SizeRemaining / 1GB
Log ("C: free after: {0:N1} GB" -f $freeAfter)
Log "=== Done ==="
Log ""
Log "Next steps:"
Log "  1. Restart PC (or at least Epic Launcher)"
Log "  2. Epic Launcher -> UE 5.8 -> Options -> enable Android"
Log "  3. Run Tools\package_quest.ps1"
Log ""
Log "Engine is already on E:\Epic Games\UE_5.8"
Log "Projects path unchanged in apps (junction): ...\Documents\Unreal Projects"
