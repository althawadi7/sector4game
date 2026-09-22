# Reinstall Monolith MCP plugin (UE 5.8 prebuilt, no compile)
$ErrorActionPreference = "Stop"
$version = "v0.22.0"
$zipUrl = "https://github.com/tumourlove/monolith/releases/download/$version/Monolith-$version-UE5.8.zip"
$project = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$plugins = Join-Path $project "Plugins"
$dest = Join-Path $plugins "Monolith"
$zip = Join-Path $env:TEMP "Monolith-$version-UE5.8.zip"

Write-Host "Downloading Monolith $version for UE 5.8..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zip -UseBasicParsing

if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Expand-Archive -Path $zip -DestinationPath $plugins -Force

if (Test-Path (Join-Path $plugins "Monolith.uplugin")) {
  $items = @(
    ".github", "Binaries", "Config", "Docs", "MCP", "Scripts", "Skills", "Source", "Templates", "Tools",
    ".gitattributes", ".gitignore", "ATTRIBUTION.md", "CHANGELOG.md", "CONTRIBUTING.md", "LICENSE",
    "Monolith.uplugin", "README.md", "SECURITY.md"
  )
  foreach ($item in $items) {
    $src = Join-Path $plugins $item
    if (Test-Path $src) { Move-Item -Path $src -Destination $dest -Force }
  }
}

if (-not (Test-Path (Join-Path $dest "Binaries\monolith_proxy.exe"))) {
  throw "Install failed: monolith_proxy.exe not found in $dest"
}

Write-Host "OK: $dest"
Write-Host "Restart Unreal. Log should show: Monolith MCP server listening on port 9316"
