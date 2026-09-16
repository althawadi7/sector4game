# Package sector4v2 for Meta Quest and install via USB (standalone APK).
# Run in PowerShell:
#   powershell -ExecutionPolicy Bypass -File "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/package_quest.ps1"

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$UProject    = Join-Path $ProjectRoot "sector4v2.uproject"
$UERoot      = "E:\Epic Games\UE_5.8"
$UAT         = Join-Path $UERoot "Engine\Build\BatchFiles\RunUAT.bat"
$ArchiveDir  = Join-Path $ProjectRoot "Builds\Quest"
$LogFile     = Join-Path $ArchiveDir "package.log"
$Adb         = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$Launcher    = "C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"

function Test-AndroidEngineSupport {
    # UE 5.8 InstalledPlatformInfo marks Android Downloaded when UnrealGame.target exists.
    # (Older check for Engine\Binaries\ThirdParty\Android is obsolete / always false on 5.8.)
    return Test-Path (Join-Path $UERoot "Engine\Binaries\Android\UnrealGame.target")
}

function Ensure-AndroidEngineSupport {
    if (Test-AndroidEngineSupport) { return $true }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host " ANDROID NOT INSTALLED IN UE 5.8" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "One-time fix in Epic Games Launcher:"
    Write-Host "  1. Library"
    Write-Host "  2. Unreal Engine 5.8  ->  ...  (three dots)  ->  Options"
    Write-Host "  3. Target Platforms: check ANDROID"
    Write-Host "  4. Apply / Install (may take several GB, 10-30 min)"
    Write-Host "  5. Re-run this script"
    Write-Host ""

    if (Test-Path $Launcher) {
        Write-Host "Opening Epic Games Launcher..." -ForegroundColor Cyan
        Start-Process $Launcher
    }

    return $false
}

function Find-Apk {
    param([string]$Root)
    Get-ChildItem -Path $Root -Filter "*.apk" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

New-Item -ItemType Directory -Force -Path $ArchiveDir | Out-Null

if (-not (Test-Path $UProject)) { throw "Project not found: $UProject" }
if (-not (Test-Path $UAT)) { throw "RunUAT not found: $UAT" }
if (-not (Ensure-AndroidEngineSupport)) { exit 2 }

Write-Host "Packaging Android ASTC for Quest..." -ForegroundColor Cyan
Write-Host "Log: $LogFile"
Write-Host "This usually takes 30-90 minutes on first build."

$EditorCmd = Join-Path $UERoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$args = @(
    "BuildCookRun",
    "-project=`"$UProject`"",
    "-noP4",
    "-platform=Android",
    "-clientconfig=Development",
    "-cook", "-stage", "-pak", "-package", "-archive",
    "-archivedirectory=`"$ArchiveDir`"",
    "-build", "-prereqs", "-compressed",
    "-CookFlavor=ASTC",
    "-installed",
    "-unattended",
    "-utf8output",
    "-nocompileeditor",
    # Blueprint projects with Intermediate/Source still look for a missing *Editor.target receipt;
    # force the installed engine editor for cook commandlets.
    "-unrealexe=`"$EditorCmd`"",
    # Ensures from marketplace/orphan BP nodes must not fail the cook.
    # 0 = fail on any ensure (wrong); 100 = allow ensures so cook can finish.
    "-handleensurepercent=100",
    # Marketplace/orphan BP ensures still count as cook Errors; continue to package APK.
    "-IgnoreCookErrors"
)

& $UAT @args 2>&1 | Tee-Object -FilePath $LogFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED. See $LogFile" -ForegroundColor Red
    exit $LASTEXITCODE
}

$apk = Find-Apk $ArchiveDir
if (-not $apk) {
    Write-Host "Build finished but no APK found under $ArchiveDir" -ForegroundColor Red
    exit 3
}

Write-Host "APK: $($apk.FullName)" -ForegroundColor Green

if (-not (Test-Path $Adb)) {
    Write-Host "adb not found. Install APK manually with Meta Quest Developer Hub." -ForegroundColor Yellow
    exit 0
}

Write-Host "Checking Quest USB connection..." -ForegroundColor Cyan
& $Adb devices
$devices = (& $Adb devices | Select-String "device$" | Where-Object { $_ -notmatch "List of devices" })
if (-not $devices) {
    Write-Host "No Quest detected. Connect USB, allow debugging, then run:" -ForegroundColor Yellow
    Write-Host "  & `"$Adb`" install -r `"$($apk.FullName)`""
    exit 0
}

Write-Host "Installing on Quest..." -ForegroundColor Cyan
& $Adb install -r $apk.FullName
if ($LASTEXITCODE -ne 0) {
    Write-Host "Install failed. Try Meta Quest Developer Hub -> Install APK." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "DONE!" -ForegroundColor Green
Write-Host "On Quest: App Library -> Unknown Sources -> sector4v2"
Write-Host "Standalone VR - no Link, no casting from UE."
