<# Switch SPI firmware profiles on the tested board. Never provisions or writes UFS.
Check is the default. Flash backs up the current SPI; Boot is a separate action.
Linux kernel configuration is described in docs/bios-profiles.md.
#>
param(
    [ValidateSet('Linux','Android')]
    [string]$Profile = 'Linux',
    [ValidateSet('Check','Flash','Boot','Restore')]
    [string]$Action = 'Check',
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')]
    [string]$RunId,
    [string]$Bundle
)
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Installer = Join-Path $PSScriptRoot 'Install-Q6A-Android.ps1'

function Get-BiosStages([string]$SelectedProfile,[string]$SelectedAction) {
    if ($SelectedProfile -notin @('Linux','Android')) { throw 'Unknown BIOS profile' }
    switch ($SelectedAction) {
        'Check' { return @('Check') }
        'Flash' {
            if ($SelectedProfile -eq 'Linux') { return @('BackupSpi','RecoveryLinux') }
            return @('BackupSpi','FlashSpi')
        }
        'Boot' {
            if ($SelectedProfile -eq 'Linux') { return @('BootLinux') }
            return @('Boot')
        }
        'Restore' { return @('RestoreSpi') }
        default { throw 'Unknown BIOS action' }
    }
}
function Assert-NewBiosRun([string]$Directory) {
    if (Test-Path -LiteralPath $Directory) { throw 'RunId already exists. Use a NEW RunId for each BIOS Flash; keep the old one for Restore.' }
}
function Assert-BiosRunProfile([string]$RecordPath,[string]$SelectedProfile) {
    if (-not (Test-Path -LiteralPath $RecordPath -PathType Leaf)) { throw 'No BIOS switch record for this RunId' }
    $Record = Get-Content -LiteralPath $RecordPath -Raw | ConvertFrom-Json
    if ($Record.profile -ne $SelectedProfile) { throw 'RunId belongs to a different BIOS profile' }
}
function Invoke-BiosStages([string[]]$Stages) {
    foreach ($SelectedStage in $Stages) {
        # Keep destructive UFS stages out of this entry point, even if a plan is changed.
        if ($SelectedStage -notin @('Check','BackupSpi','RecoveryLinux','FlashSpi','Boot','BootLinux','RestoreSpi')) {
            throw "Not a BIOS stage: $SelectedStage"
        }
        & $Installer -Stage $SelectedStage -RunId $RunId -Bundle $Bundle
    }
}

$Plan = @(Get-BiosStages $Profile $Action)
& $Installer -Stage Check -Bundle $Bundle
if ($Action -eq 'Check') {
    Write-Output "BIOS PROFILE CHECKED: $Profile. No USB device contacted. See docs/bios-profiles.md for boot requirements."
    return
}
if (-not $RunId) { throw 'BIOS device actions require -RunId. Each Flash needs a new RunId.' }
if (-not $Bundle) {
    $SavedPath = Join-Path $Repo 'artifacts\bundle-path.txt'
    if (Test-Path -LiteralPath $SavedPath) { $Bundle = (Get-Content -LiteralPath $SavedPath -Raw).Trim() }
    else {
        $Lock = Get-Content -LiteralPath (Join-Path $Repo 'manifests\bundle-lock.json') -Raw | ConvertFrom-Json
        $Bundle = Join-Path (Join-Path $Repo 'artifacts') $Lock.folder
    }
}
$Kit = (Resolve-Path -LiteralPath $Bundle).ProviderPath
$Directory = Join-Path (Join-Path $Kit 'runs') $RunId
$RecordPath = Join-Path $Directory 'bios-switch.json'
if ($Action -eq 'Flash') {
    Assert-NewBiosRun $Directory
    New-Item -ItemType Directory -Path $Directory | Out-Null
    @{profile=$Profile;run_id=$RunId;created_utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $RecordPath
} else {
    Assert-BiosRunProfile $RecordPath $Profile
}
Invoke-BiosStages $Plan
if ($Action -eq 'Flash') {
    Write-Output "BIOS FLASH VERIFIED: $Profile. SPI backup saved. Power off and cold boot with the intended OS medium, or use -Action Boot with the SAME RunId."
}
