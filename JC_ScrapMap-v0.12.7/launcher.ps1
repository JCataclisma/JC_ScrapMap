param(
    [string]$GamePath,
    [string]$UserPath,
    [string]$Save,
    [Nullable[int]]$Seed,
    [int]$Port = 8765,
    [switch]$Overlay,
    [switch]$NoBrowser,
    [switch]$NoServer
)

$ErrorActionPreference = 'Stop'
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectPath 'runtime\python\python.exe'
$ScriptPath = Join-Path $ProjectPath 'scrapmap.py'

if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-Error 'The private JC ScrapMap runtime is missing. Re-extract the complete package.'
}
if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    Write-Error 'The JC ScrapMap application is missing. Re-extract the complete package.'
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
    $Arguments += @('--seed', [int]$Seed)
}
if ($NoBrowser) {
    $Arguments += '--no-browser'
}
if ($Overlay) {
    $Arguments += '--overlay'
}
if ($NoServer) {
    $Arguments += '--no-server'
}

& $PythonPath @Arguments
exit $LASTEXITCODE
