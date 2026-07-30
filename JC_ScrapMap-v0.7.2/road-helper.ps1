param(
    [ValidateSet('Menu', 'Status', 'Generate', 'Enable', 'Disable')]
    [string]$Action = 'Menu',
    [string]$GamePath,
    [string]$UserPath,
    [int]$Port = 8765,
    [switch]$TestMode
)

$ErrorActionPreference = 'Stop'
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperStatePath = Join-Path $ProjectPath '.road-helper'
$StateFile = Join-Path $HelperStatePath 'state.json'
$LastGenerationFile = Join-Path $HelperStatePath 'last-generation.json'
$DiagnosticPath = Join-Path $ProjectPath 'JC_ScrapMap_Diagnostic.txt'
$BackupFile = Join-Path $HelperStatePath 'terrain_overworld.original.lua'
$HookBegin = '-- JC_SCRAPMAP_ROAD_HELPER_BEGIN'
$HookEnd = '-- JC_SCRAPMAP_ROAD_HELPER_END'
$HookLine = 'dofile("$CONTENT_8f3672f0-1d70-4a65-a47b-fd411c8cbf60/Scripts/terrain_road_export.lua")'
$ModId = '8f3672f0-1d70-4a65-a47b-fd411c8cbf60'
$script:ReportLines = [System.Collections.Generic.List[string]]::new()

function Protect-DiagnosticText([string]$Text) {
    if ($null -eq $Text) { return '' }
    $safe = $Text
    foreach ($item in @(
        @{ Path = $ProjectPath; Label = '<app-folder>' },
        @{ Path = $GamePath; Label = '<game-folder>' },
        @{ Path = $UserPath; Label = '<user-folder>' }
    )) {
        if ($item.Path) {
            $safe = $safe.Replace([string]$item.Path, [string]$item.Label)
        }
    }
    $safe = [regex]::Replace(
        $safe,
        '(?i)[A-Z]:\\Users\\[^\\\r\n]+',
        '<Windows-user-folder>'
    )
    return $safe
}

function Add-Diagnostic([string]$Stage, [string]$Message) {
    $line = "$([DateTime]::UtcNow.ToString('o')) [$Stage] $(Protect-DiagnosticText $Message)"
    $script:ReportLines.Add($line)
    Write-Host "[$Stage] $Message"
}

function Save-Diagnostic([string]$Result) {
    $header = @(
        'JC ScrapMap diagnostic report'
        'Version: 0.7.2'
        "Result: $Result"
        'This report excludes save contents and replaces personal folder names.'
        ''
    )
    New-Item -ItemType Directory -Force -Path $ProjectPath | Out-Null
    Set-Content -LiteralPath $DiagnosticPath -Value ($header + $script:ReportLines) -Encoding UTF8
}

function Show-Diagnostic {
    if (-not (Test-Path -LiteralPath $DiagnosticPath -PathType Leaf)) {
        Write-Warning 'No diagnostic report exists yet. Generate roads first.'
        return
    }
    Start-Process notepad.exe -ArgumentList "`"$DiagnosticPath`""
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-ElevatedAction([string]$RequestedAction, [switch]$NoWait) {
    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSCommandPath`"",
        '-Action', $RequestedAction,
        '-Port', $Port
    )
    if ($GamePath) { $arguments += @('-GamePath', "`"$GamePath`"") }
    if ($UserPath) { $arguments += @('-UserPath', "`"$UserPath`"") }
    $startParameters = @{
        FilePath = 'powershell.exe'
        Verb = 'RunAs'
        ArgumentList = $arguments
        PassThru = $true
    }
    if (-not $NoWait) { $startParameters.Wait = $true }
    $process = Start-Process @startParameters
    if ($NoWait) { return $process }
    if ($process.ExitCode -ne 0) { throw "$RequestedAction failed with exit code $($process.ExitCode)." }
}

function Start-GenerateWindow {
    if ($null -ne (Read-State)) {
        throw 'The road helper is already active. Choose Disable/repair road helper before starting another generation.'
    }
    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSCommandPath`"",
        '-Action', 'Generate',
        '-Port', $Port
    )
    if ($GamePath) { $arguments += @('-GamePath', "`"$GamePath`"") }
    if ($UserPath) { $arguments += @('-UserPath', "`"$UserPath`"") }
    if (Test-Administrator) {
        Start-Process powershell.exe -ArgumentList $arguments | Out-Null
    } else {
        Invoke-ElevatedAction 'Generate' -NoWait | Out-Null
    }
    Write-Host 'Generation started in a separate helper window. This menu remains available.'
}

function Start-MapServer([Nullable[int]]$Seed) {
    $launcher = Join-Path $ProjectPath 'launcher.ps1'
    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', "`"$launcher`"",
        '-DirectMap',
        '-NoBrowser',
        '-Port', $Port
    )
    if ($GamePath) { $arguments += @('-GamePath', "`"$GamePath`"") }
    if ($UserPath) { $arguments += @('-UserPath', "`"$UserPath`"") }
    if ($null -ne $Seed) { $arguments += @('-Seed', $Seed.Value) }
    Start-Process powershell.exe -ArgumentList $arguments | Out-Null
}

function Open-Or-RefreshMap([Nullable[int]]$Seed) {
    $baseUri = "http://127.0.0.1:$Port"
    $mapUri = "$baseUri/web/index.html"
    try {
        $status = Invoke-RestMethod -Method Get -Uri "$baseUri/api/status" -TimeoutSec 2
    } catch {
        Start-MapServer $Seed
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            Start-Sleep -Milliseconds 250
            try {
                $status = Invoke-RestMethod -Method Get -Uri "$baseUri/api/status" -TimeoutSec 1
                if ($status.ok -and $status.service -eq 'jc-scrapmap') {
                    $ready = $true
                    break
                }
            } catch {}
        }
        if (-not $ready) {
            throw 'The map server did not start. The road capture is safe, but its matching save may be missing.'
        }
        Start-Process $mapUri
        Write-Host 'Map opened with the latest saved state.'
        return $true
    }
    if (-not $status.ok -or $status.service -ne 'jc-scrapmap') {
        throw "Port $Port is occupied by another service; the map was not opened."
    }
    try {
        if ($null -ne $Seed) {
            $body = @{ seed = $Seed.Value } | ConvertTo-Json
            Invoke-RestMethod -Method Post -Uri "$baseUri/api/select-seed" -ContentType 'application/json' -Body $body -TimeoutSec 30 | Out-Null
        } else {
            Invoke-RestMethod -Method Post -Uri "$baseUri/api/refresh" -ContentType 'application/json' -Body '{}' -TimeoutSec 30 | Out-Null
        }
        Start-Process $mapUri
        Write-Host 'Map data refreshed from the latest saved state.'
        return $true
    } catch {
        throw "The existing map could not select the captured world: $($_.Exception.Message)"
    }
}

function Assert-TestModeScope {
    if (-not $TestMode) { return }
    $projectRoot = [System.IO.Path]::GetFullPath($ProjectPath).TrimEnd('\') + '\'
    foreach ($candidate in @($GamePath, $UserPath)) {
        if (-not $candidate) { throw 'TestMode requires explicit GamePath and UserPath.' }
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (-not $resolved.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "TestMode path is outside the project workspace: $resolved"
        }
    }
}

function Get-DefaultGamePath([string[]]$SteamRootsOverride) {
    $steamRoots = New-Object System.Collections.Generic.List[string]
    if ($SteamRootsOverride) {
        foreach ($value in $SteamRootsOverride) {
            if ($value -and -not $steamRoots.Contains($value)) {
                $steamRoots.Add($value)
            }
        }
    } else {
        foreach ($registryPath in @(
            'HKCU:\Software\Valve\Steam',
            'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam',
            'HKLM:\SOFTWARE\Valve\Steam'
        )) {
            try {
                $properties = Get-ItemProperty -Path $registryPath -ErrorAction Stop
                foreach ($value in @($properties.SteamPath, $properties.InstallPath)) {
                    if ($value -and -not $steamRoots.Contains([string]$value)) {
                        $steamRoots.Add([string]$value)
                    }
                }
            } catch {}
        }
        $standardRoot = Join-Path ${env:ProgramFiles(x86)} 'Steam'
        if (-not $steamRoots.Contains($standardRoot)) { $steamRoots.Add($standardRoot) }
    }

    $libraryRoots = New-Object System.Collections.Generic.List[string]
    foreach ($steamRoot in $steamRoots) {
        if (-not $libraryRoots.Contains($steamRoot)) { $libraryRoots.Add($steamRoot) }
        $libraryFile = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
        if (-not (Test-Path -LiteralPath $libraryFile -PathType Leaf)) { continue }
        foreach ($line in Get-Content -LiteralPath $libraryFile -ErrorAction SilentlyContinue) {
            if ($line -match '^\s*"path"\s+"(?<path>.+)"\s*$') {
                $libraryRoot = $Matches.path -replace '\\\\', '\'
                if (-not $libraryRoots.Contains($libraryRoot)) {
                    $libraryRoots.Add($libraryRoot)
                }
            }
        }
    }

    foreach ($libraryRoot in $libraryRoots) {
        $candidate = Join-Path $libraryRoot 'steamapps\common\Scrap Mechanic'
        $terrain = Join-Path $candidate 'Survival\Scripts\terrain\terrain_overworld.lua'
        if (Test-Path -LiteralPath $terrain -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    Write-Host 'Scrap Mechanic was not found in the registered Steam libraries.'
    $manualPath = Read-Host 'Enter the full Scrap Mechanic installation folder'
    if (-not $manualPath) { throw 'A Scrap Mechanic installation folder is required.' }
    $manualTerrain = Join-Path $manualPath 'Survival\Scripts\terrain\terrain_overworld.lua'
    if (-not (Test-Path -LiteralPath $manualTerrain -PathType Leaf)) {
        throw "That folder is not a valid Scrap Mechanic installation: $manualPath"
    }
    return (Resolve-Path -LiteralPath $manualPath).Path
}

function Get-DefaultUserRoot {
    return Join-Path $env:APPDATA 'Axolot Games\Scrap Mechanic\User'
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Test-GameRunning {
    return $null -ne (Get-Process -Name ScrapMechanic -ErrorAction SilentlyContinue)
}

function Get-UserDirectory([string]$RequestedPath) {
    $root = if ($RequestedPath) { $RequestedPath } else { Get-DefaultUserRoot }
    if ((Split-Path -Leaf $root) -like 'User_*') {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            throw "Scrap Mechanic user directory does not exist: $root"
        }
        return (Resolve-Path -LiteralPath $root).Path
    }
    $choices = @(Get-ChildItem -LiteralPath $root -Directory -Filter 'User_*' -ErrorAction Stop)
    if ($choices.Count -eq 0) { throw "No Scrap Mechanic User_* directory was found under $root" }
    if ($choices.Count -eq 1) { return $choices[0].FullName }
    Write-Host 'Choose the Scrap Mechanic player profile:'
    for ($index = 0; $index -lt $choices.Count; $index++) {
        Write-Host "  $($index + 1). $($choices[$index].Name)"
    }
    $selection = [int](Read-Host 'Profile number')
    if ($selection -lt 1 -or $selection -gt $choices.Count) { throw 'Invalid profile selection.' }
    return $choices[$selection - 1].FullName
}

function Get-Paths {
    $resolvedGame = if ($GamePath) { $GamePath } else { Get-DefaultGamePath }
    $resolvedGame = (Resolve-Path -LiteralPath $resolvedGame).Path
    $userDirectory = Get-UserDirectory $UserPath
    return @{
        Game = $resolvedGame
        User = $userDirectory
        Terrain = Join-Path $resolvedGame 'Survival\Scripts\terrain\terrain_overworld.lua'
        Mod = Join-Path $userDirectory 'Mods\JC_ScrapMap_RoadExporter'
    }
}

function Read-State {
    if (-not (Test-Path -LiteralPath $StateFile -PathType Leaf)) { return $null }
    return Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
}

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Enable-Helper {
    if (Test-GameRunning) { throw 'Close Scrap Mechanic before enabling the road helper.' }
    $paths = Get-Paths
    if (-not (Test-Path -LiteralPath $paths.Terrain -PathType Leaf)) {
        throw "Active terrain script was not found: $($paths.Terrain)"
    }
    $sourceMod = Join-Path $ProjectPath 'game-side\mod'
    $originalText = Get-Content -LiteralPath $paths.Terrain -Raw
    if ($originalText.Contains($HookBegin)) {
        $existing = Read-State
        if ($null -eq $existing) {
            throw 'A JC ScrapMap hook exists but its recovery state is missing. Refusing an unsafe change.'
        }
        Write-Host 'Road helper is already enabled.'
        return $paths
    }

    New-Item -ItemType Directory -Force -Path $HelperStatePath | Out-Null
    Copy-Item -LiteralPath $paths.Terrain -Destination $BackupFile -Force
    $originalHash = Get-Hash $BackupFile
    $hookBlock = "`r`n$HookBegin`r`n$HookLine`r`n$HookEnd`r`n"
    $temporary = "$($paths.Terrain).jc-scrapmap.tmp"
    Write-Utf8NoBom $temporary ($originalText.TrimEnd("`r", "`n") + $hookBlock)
    Move-Item -LiteralPath $temporary -Destination $paths.Terrain -Force
    $patchedHash = Get-Hash $paths.Terrain

    if (Test-Path -LiteralPath $paths.Mod) {
        $description = Join-Path $paths.Mod 'description.json'
        if (-not (Test-Path -LiteralPath $description -PathType Leaf) -or
            -not (Get-Content -LiteralPath $description -Raw).Contains($ModId)) {
            throw "Refusing to replace a non-JC directory: $($paths.Mod)"
        }
        Remove-Item -LiteralPath $paths.Mod -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $paths.Mod | Out-Null
    Copy-Item -Path (Join-Path $sourceMod '*') -Destination $paths.Mod -Recurse -Force

    @{
        schemaVersion = 1
        enabledUtc = [DateTime]::UtcNow.ToString('o')
        gamePath = $paths.Game
        userPath = $paths.User
        terrainPath = $paths.Terrain
        modPath = $paths.Mod
        originalHash = $originalHash
        patchedHash = $patchedHash
    } | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding UTF8
    Write-Host 'Exact-road helper enabled temporarily.'
    return $paths
}

function Disable-Helper {
    if (Test-GameRunning) { throw 'Close Scrap Mechanic before restoring its terrain script.' }
    $state = Read-State
    if ($null -eq $state) {
        Write-Host 'No managed road-helper activation is recorded.'
        return
    }
    if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
        throw 'The recovery backup is missing. Refusing to alter the installed script.'
    }
    if ((Get-Hash $BackupFile) -ne $state.originalHash) {
        throw 'The recovery backup hash does not match its recorded hash.'
    }
    $currentHash = Get-Hash $state.terrainPath
    if ($currentHash -ne $state.patchedHash -and $currentHash -ne $state.originalHash) {
        throw 'The installed terrain script changed after activation. Refusing to overwrite it.'
    }
    if ($currentHash -eq $state.patchedHash) {
        Copy-Item -LiteralPath $BackupFile -Destination $state.terrainPath -Force
    }
    if ((Get-Hash $state.terrainPath) -ne $state.originalHash) {
        throw 'Installed terrain-script restoration verification failed.'
    }
    if (Test-Path -LiteralPath $state.modPath) {
        $description = Join-Path $state.modPath 'description.json'
        if ((Test-Path -LiteralPath $description -PathType Leaf) -and
            (Get-Content -LiteralPath $description -Raw).Contains($ModId)) {
            Remove-Item -LiteralPath $state.modPath -Recurse -Force
        }
    }
    Remove-Item -LiteralPath $StateFile -Force
    Write-Host 'Road helper disabled; original installed script restored and verified.'
}

function Show-Status {
    $state = Read-State
    if ($null -eq $state) {
        Write-Host 'Road helper status: disabled'
    } else {
        if (Test-GameRunning) {
            Write-Host 'Road helper status: ENABLED (Scrap Mechanic is running)'
        } else {
            Write-Host 'Road helper status: RECOVERY REQUIRED (game is not running)'
        }
        Write-Host "Installed script: $($state.terrainPath)"
        Write-Host "Enabled UTC: $($state.enabledUtc)"
    }
}

function Generate-Roads {
    Add-Diagnostic 'START' 'Exact-road generation started.'
    $paths = Enable-Helper
    Add-Diagnostic 'HELPER' 'Temporary game helper enabled.'
    $exportPath = Join-Path $paths.Mod 'roads-export.json'
    $previousTimestamp = if (Test-Path -LiteralPath $exportPath) {
        (Get-Item -LiteralPath $exportPath).LastWriteTimeUtc
    } else { [DateTime]::MinValue }

    Write-Host ''
    Write-Host 'Scrap Mechanic will start now.'
    Write-Host 'Load the Survival world you want to map. Roads, terrain regions, and Schematic Stations export automatically.'
    Write-Host 'When finished playing, close Scrap Mechanic; this window will restore the game files.'
    Start-Process 'steam://rungameid/387990'

    $deadline = [DateTime]::UtcNow.AddMinutes(30)
    $startupDeadline = [DateTime]::UtcNow.AddMinutes(5)
    $gameWasRunning = $false
    $document = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $gameIsRunning = Test-GameRunning
        if ($gameIsRunning) {
            $gameWasRunning = $true
        } elseif ($gameWasRunning) {
            throw 'Scrap Mechanic exited or crashed before terrain data was captured.'
        } elseif ([DateTime]::UtcNow -ge $startupDeadline) {
            throw 'Scrap Mechanic did not start within five minutes. The helper will be restored automatically.'
        }
        if (Test-Path -LiteralPath $exportPath -PathType Leaf) {
            $item = Get-Item -LiteralPath $exportPath
            if ($item.LastWriteTimeUtc -gt $previousTimestamp) {
                try {
                    $candidate = Get-Content -LiteralPath $exportPath -Raw | ConvertFrom-Json
                    if ($candidate.protocol -eq 'jc-scrapmap-roads-v1' -and
                        [int]$candidate.seed -ne 0 -and $candidate.roads.Count -gt 0) {
                        $document = $candidate
                        Add-Diagnostic 'CAPTURE' "Captured seed $([int]$candidate.seed) with $($candidate.roads.Count) road cells."
                        break
                    }
                } catch {}
            }
        }
    }
    if ($null -eq $document) {
        throw 'No valid road export appeared within 30 minutes.'
    }

    $managedOutput = Join-Path $ProjectPath "imports\roads-$([int]$document.seed).json"
    Copy-Item -LiteralPath $exportPath -Destination $managedOutput -Force
    $waterCount = if ($null -ne $document.water) { $document.water.Count } else { 0 }
    $desertCount = if ($null -ne $document.desert) { $document.desert.Count } else { 0 }
    $burntForestCount = if ($null -ne $document.burntForest) { $document.burntForest.Count } else { 0 }
    $schematicStationCount = if ($null -ne $document.schematicStations) { $document.schematicStations.Count } else { 0 }
    Write-Host "Captured $($document.roads.Count) road cells; $waterCount water, $desertCount desert, and $burntForestCount burnt forest cells; and $schematicStationCount Schematic Stations for seed $([int]$document.seed)."
    Write-Host 'Close Scrap Mechanic to complete automatic cleanup and open the map.'
    while (Test-GameRunning) { Start-Sleep -Seconds 2 }
    Disable-Helper
    Add-Diagnostic 'CLEANUP' 'Original game script restored and verified.'

    New-Item -ItemType Directory -Force -Path $HelperStatePath | Out-Null
    @{
        seed = [int]$document.seed
        roadCount = $document.roads.Count
        waterCount = $waterCount
        desertCount = $desertCount
        burntForestCount = $burntForestCount
        schematicStationCount = $schematicStationCount
        generatedUtc = [DateTime]::UtcNow.ToString('o')
        outputPath = $managedOutput
    } | ConvertTo-Json | Set-Content -LiteralPath $LastGenerationFile -Encoding UTF8
    Add-Diagnostic 'SUCCESS' "Generation completed for seed $([int]$document.seed): $($document.roads.Count) roads, $waterCount water, $desertCount desert, $burntForestCount burnt forest, $schematicStationCount Schematic Stations."
    Save-Diagnostic 'SUCCESS'
    Write-Host ''
    Write-Host 'SUCCESS: Your map is ready.' -ForegroundColor Green
    Write-Host "Captured world seed: $([int]$document.seed)"
    Write-Host "Diagnostic report: $DiagnosticPath"
    Open-Or-RefreshMap ([int]$document.seed) | Out-Null
    Add-Diagnostic 'MAP' "Opened the matching save for seed $([int]$document.seed)."
    Save-Diagnostic 'SUCCESS'
    Write-Host ''
    Read-Host 'Press Enter after you have seen this result'
}

function Invoke-GenerateSafely {
    try {
        Generate-Roads
    } catch {
        Add-Diagnostic 'ERROR' "$($_.Exception.GetType().Name): $($_.Exception.Message)"
        Write-Warning "Generation failed: $($_.Exception.Message)"
        if (-not (Test-GameRunning) -and $null -ne (Read-State)) {
            Write-Host 'Attempting automatic road-helper recovery...'
            Disable-Helper
        } elseif ($null -ne (Read-State)) {
            Write-Warning 'The helper remains enabled while Scrap Mechanic is running. Close the game, then choose Disable/repair road helper.'
        }
        Save-Diagnostic 'ERROR'
        Write-Host ''
        Write-Host 'JC ScrapMap could not finish.' -ForegroundColor Red
        Write-Host "A privacy-conscious report was saved here: $DiagnosticPath"
        Read-Host 'Press Enter after you have noted the report location'
        throw
    }
}

if ($Action -eq 'Menu') {
    while ($true) {
        Write-Host ''
        Write-Host 'JC ScrapMap'
        Write-Host '1. Open map'
        Write-Host '2. Generate exact roads (temporarily enables helper)'
        Write-Host '3. Disable/repair road helper'
        Write-Host '4. Show road-helper status'
        Write-Host '5. Open diagnostic report'
        Write-Host '6. Exit'
        $selection = Read-Host 'Choose an action'
        try {
            switch ($selection) {
                '1' { Open-Or-RefreshMap $null }
                '2' { Start-GenerateWindow }
                '3' {
                    if (Test-Administrator) { Disable-Helper } else { Invoke-ElevatedAction 'Disable' }
                }
                '4' { Show-Status }
                '5' { Show-Diagnostic }
                '6' { return }
                default { Write-Warning 'Choose a number from 1 to 6.' }
            }
        } catch {
            Write-Warning "Action failed: $($_.Exception.Message)"
            Write-Host 'The menu is still available.'
        }
    }
} elseif ($Action -eq 'Generate') {
    Assert-TestModeScope
    if (-not $TestMode -and -not (Test-Administrator)) { Invoke-ElevatedAction 'Generate'; return }
    Invoke-GenerateSafely
} elseif ($Action -eq 'Enable') {
    Assert-TestModeScope
    if (-not $TestMode -and -not (Test-Administrator)) { Invoke-ElevatedAction 'Enable'; return }
    Enable-Helper | Out-Null
} elseif ($Action -eq 'Disable') {
    Assert-TestModeScope
    if (-not $TestMode -and -not (Test-Administrator)) { Invoke-ElevatedAction 'Disable'; return }
    Disable-Helper
} else {
    Show-Status
}
