$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$serverPath = Join-Path $repositoryRoot "mcp_server.py"
$mcpUrl = "http://127.0.0.1:8000"
$healthUrl = "$mcpUrl/health"

function Write-LauncherError {
    param([string]$Message)

    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Get-PythonEnvironment {
    if ($env:VIRTUAL_ENV) {
        $activatedPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
        if (Test-Path -LiteralPath $activatedPython -PathType Leaf) {
            return [pscustomobject]@{
                PythonPath = (Resolve-Path -LiteralPath $activatedPython).Path
                EnvironmentPath = (Resolve-Path -LiteralPath $env:VIRTUAL_ENV).Path
            }
        }
    }

    $environmentNames = @(".venv", "venv", "env", "microsoftVenv")
    foreach ($environmentName in $environmentNames) {
        $environmentPath = Join-Path $repositoryRoot $environmentName
        $pythonPath = Join-Path $environmentPath "Scripts\python.exe"
        if (Test-Path -LiteralPath $pythonPath -PathType Leaf) {
            return [pscustomobject]@{
                PythonPath = (Resolve-Path -LiteralPath $pythonPath).Path
                EnvironmentPath = (Resolve-Path -LiteralPath $environmentPath).Path
            }
        }
    }

    return $null
}

function Test-McpHealth {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -Method Get -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $serverPath -PathType Leaf)) {
    Write-LauncherError "MCP server was not found at $serverPath"
}

if (Test-McpHealth) {
    Write-Host "MCP server already appears to be running on"
    Write-Host $mcpUrl
    exit 0
}

$portInUse = $false
try {
    $portInUse = [bool](Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
}
catch {
    $portInUse = $false
}

if ($portInUse) {
    Write-LauncherError "Port 8000 is already in use, but $healthUrl did not respond as a healthy MCP server. Stop the process using port 8000 and try again."
}

$pythonEnvironment = Get-PythonEnvironment
if ($null -eq $pythonEnvironment) {
    Write-Host "ERROR: No project Python virtual environment was found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Searched:"
    if ($env:VIRTUAL_ENV) {
        Write-Host "    $($env:VIRTUAL_ENV)\Scripts\python.exe (activated environment)"
    }
    foreach ($environmentName in @(".venv", "venv", "env", "microsoftVenv")) {
        Write-Host "    $(Join-Path $repositoryRoot $environmentName)\Scripts\python.exe"
    }
    Write-Host ""
    Write-Host "Please create/configure a project virtual environment first, for example:"
    Write-Host "    python -m venv .venv"
    Write-Host ""
    Write-Host "Then install the project requirements and run:"
    Write-Host "    .\start_mcp.ps1"
    exit 1
}

Set-Location -LiteralPath $repositoryRoot

Write-Host "========================================"
Write-Host " AI IT SUPPORT - MCP SERVER"
Write-Host "========================================"
Write-Host ""
Write-Host "Repository:"
Write-Host $repositoryRoot
Write-Host ""
Write-Host "Python:"
Write-Host $pythonEnvironment.PythonPath
Write-Host ""
Write-Host "Environment:"
Write-Host $pythonEnvironment.EnvironmentPath
Write-Host ""
Write-Host "MCP:"
Write-Host $mcpUrl
Write-Host ""
Write-Host "Starting MCP server..."
Write-Host ""

& $pythonEnvironment.PythonPath $serverPath

Write-Host ""
Write-Host "MCP server stopped."
