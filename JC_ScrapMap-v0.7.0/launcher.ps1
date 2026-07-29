param(
    [string]$GamePath,
    [string]$UserPath,
    [string]$Save,
    [Nullable[int]]$Seed,
    [int]$Port = 8765,
    [switch]$NoBrowser,
    [switch]$DirectMap
)

$ErrorActionPreference = 'Stop'
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperPath = Join-Path $ProjectPath 'road-helper.ps1'
$ScriptPath = Join-Path $ProjectPath 'scrapmap.py'

if (-not $DirectMap) {
    & $HelperPath -Action Menu -GamePath $GamePath -UserPath $UserPath -Port $Port
    exit $LASTEXITCODE
}

$PythonPath = Join-Path $ProjectPath 'runtime\python\python.exe'
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-Error 'The private JC ScrapMap runtime is missing. Re-extract the complete release package.'
}

$Arguments = @($ScriptPath, '--port', $Port)
if ($GamePath) {
    $Arguments += @('--game-path', $GamePath)
}
if ($UserPath) {
    $Arguments += @('--user-path', $UserPath)
}
if ($Save) {
    $Arguments += @('--save', $Save)
}
if ($null -ne $Seed) {
    $Arguments += @('--seed', $Seed.Value)
}
if ($NoBrowser) {
    $Arguments += '--no-browser'
}

& $PythonPath @Arguments
exit $LASTEXITCODE
