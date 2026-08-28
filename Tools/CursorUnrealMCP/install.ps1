param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
$McpDir = Join-Path $ProjectRoot "Tools\CursorUnrealMCP"
$Python = (Get-Command python).Source
$ServerPy = Join-Path $McpDir "server.py"
$CursorMcp = Join-Path $env:USERPROFILE ".cursor\mcp.json"

Write-Host "Installing MCP deps with: $Python"
& $Python -m pip install -r (Join-Path $McpDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

$env:CURSOR_MCP_PATH = $CursorMcp
$env:CURSOR_UNREAL_PYTHON = $Python
$env:CURSOR_UNREAL_SERVER = $ServerPy
& $Python (Join-Path $McpDir "merge_mcp_config.py")
if ($LASTEXITCODE -ne 0) { throw "mcp.json merge failed" }

Write-Host ""
Write-Host "OK"
Write-Host "Next:"
Write-Host "  1) Restart Unreal project sector4v2"
Write-Host "  2) Confirm Output Log: [CursorUnrealBridge] Started"
Write-Host "  3) Restart Cursor / reload MCP"
Write-Host "  4) Test: Invoke-RestMethod http://127.0.0.1:27182/status"
