param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$mcdkPath = 'D:\MCDevTool\v1.6.1\mcdk.exe'
$mutex = New-Object System.Threading.Mutex($false, 'Local\BongoCatMCMcdkLauncher')
$ownsMutex = $false
try {
    if (-not $CheckOnly) {
        try { $ownsMutex = $mutex.WaitOne(0) }
        catch [System.Threading.AbandonedMutexException] { $ownsMutex = $true }
        if (-not $ownsMutex) { throw 'BongoCatMC is already starting. Use the existing window.' }
    }
    $config = Get-Content -LiteralPath (Join-Path $projectRoot '.mcdev.json') -Raw | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath $mcdkPath -PathType Leaf)) { throw 'MCDK executable not found.' }
    if (-not (Test-Path -LiteralPath $config.game_executable_path -PathType Leaf)) { throw 'Configured Minecraft executable not found.' }
    if ($config.reset_world -or $config.world_folder_name -ne 'BONGOCATMC_HUD_001') { throw 'Unexpected development world configuration.' }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'addon\resource_pack\textures\models\bongocatmc\poses.png'))) { throw 'Animation data is missing. Run tools/build_cat.py first.' }
    if ($CheckOnly) { Write-Output 'Checks passed. No process started or renderer setting changed.'; return }
    if (@(Get-Process -Name 'mcdk','Minecraft.Windows' -ErrorAction SilentlyContinue).Count -gt 0) {
        throw 'Minecraft or MCDK is already running. Close it before starting this separate preview.'
    }
    $sessionDir = Join-Path $projectRoot ('diagnostics\launcher\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null
    # This prototype ships GLSL. Select the tested backend before MC starts.
    $optionsPath = Join-Path $env:APPDATA 'MinecraftPE_Netease\minecraftpe\options.txt'
    $optionsText = [IO.File]::ReadAllText($optionsPath)
    $backendPattern = '(?m)^gfx_renderengine:[^\r\n]*'
    $backendBefore = [regex]::Match($optionsText, $backendPattern).Value
    if (-not $backendBefore) { throw 'Minecraft renderer setting was not found.' }
    $backendBefore | Set-Content -LiteralPath (Join-Path $sessionDir 'backend-before.txt')
    if ($backendBefore -ne 'gfx_renderengine:0') {
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($optionsPath, [regex]::Replace($optionsText, $backendPattern, 'gfx_renderengine:0'), $utf8)
    }
    $process = Start-Process -FilePath $mcdkPath -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $sessionDir 'stdout.log') -RedirectStandardError (Join-Path $sessionDir 'stderr.log')
    $process.Id | Set-Content -LiteralPath (Join-Path $sessionDir 'mcdk.pid')
    # Keep the startup lock while this MCDK session exists. No automatic game shutdown.
    Wait-Process -Id $process.Id
}
catch {
    if ($CheckOnly) { throw }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'BongoCatMC') | Out-Null
}
finally {
    if ($ownsMutex) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
