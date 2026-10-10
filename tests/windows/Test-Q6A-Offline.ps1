<# Failure-path checks; extracts functions only, never executes USB stages. #>
$ErrorActionPreference = 'Stop'
$ToolRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../tools/windows/experimental'))
$ScriptPath = Join-Path $ToolRoot 'Install-Q6A-Android.ps1'
$Tokens = $null
$Errors = $null
$Ast = [Management.Automation.Language.Parser]::ParseFile($ScriptPath,[ref]$Tokens,[ref]$Errors)
if ($Errors.Count) { throw ($Errors | Out-String) }
foreach ($Name in @('Assert-Hash','Assert-Prefix','Assert-Board','Invoke-Edl','Assert-LiveSpi')) {
    $Function = $Ast.FindAll({ param($Node) $Node -is [Management.Automation.Language.FunctionDefinitionAst] },$true) | Where-Object Name -eq $Name
    if (@($Function).Count -ne 1) { throw "Missing or duplicate function: $Name" }
    Invoke-Expression $Function.Extent.Text
}
$BiosPath = Join-Path $ToolRoot 'Switch-Q6A-Bios.ps1'
$BiosAst = [Management.Automation.Language.Parser]::ParseFile($BiosPath,[ref]$Tokens,[ref]$Errors)
if ($Errors.Count) { throw ($Errors | Out-String) }
foreach ($Name in @('Get-BiosStages','Assert-NewBiosRun','Assert-BiosRunProfile','Invoke-BiosStages')) {
    $Function = $BiosAst.FindAll({ param($Node) $Node -is [Management.Automation.Language.FunctionDefinitionAst] },$true) | Where-Object Name -eq $Name
    if (@($Function).Count -ne 1) { throw "Missing or duplicate BIOS function: $Name" }
    Invoke-Expression $Function.Extent.Text
}
$TaskTestDir = Join-Path $PSScriptRoot ('offline-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $TaskTestDir | Out-Null
$RunDir = $TaskTestDir
$Stage = 'Offline'
$Tool = Join-Path $TaskTestDir 'mock-edl.ps1'
$Manifest = [pscustomobject]@{board_serial='7B57A3EB'}
$TaskPass = 0
function Expect-Failure([string]$Label,[scriptblock]$Action) {
    $Caught = $false
    try { & $Action } catch { $Caught = $true }
    if (-not $Caught) { throw "Guard did not stop: $Label" }
    $script:TaskPass++
    Write-Output "PASS: $Label"
}
try {
    @('$global:LASTEXITCODE = 0', "Write-Output '[ERROR] Configure command NAKed.'") | Set-Content -LiteralPath $Tool
    Expect-Failure 'ERROR stops even when exit code is zero' { Invoke-Edl @('configure') }
    @('$global:LASTEXITCODE = 1', "Write-Output '[INFO] Failure without error tag'") | Set-Content -LiteralPath $Tool
    Expect-Failure 'Nonzero exit code stops' { Invoke-Edl @('configure') }
    @('$global:LASTEXITCODE = 0', "Write-Output '[INFO] incomplete response'") | Set-Content -LiteralPath $Tool
    Expect-Failure 'Missing required success response stops' { Invoke-Edl @('read') 'Successfully read' }
    @('$global:LASTEXITCODE = 0', "Write-Output '[INFO] Successfully read'") | Set-Content -LiteralPath $Tool
    Invoke-Edl @('read') 'Successfully read'
    $TaskPass++
    Write-Output 'PASS: Correct success response accepted'
    $Data = Join-Path $TaskTestDir 'data.bin'
    $Prefix = Join-Path $TaskTestDir 'prefix.bin'
    [IO.File]::WriteAllBytes($Prefix,[byte[]](1,2,3))
    [IO.File]::WriteAllBytes($Data,[byte[]](1,2))
    Expect-Failure 'Truncated partition readback stops' { Assert-Prefix $Data $Prefix }
    [IO.File]::WriteAllBytes($Data,[byte[]](1,2,4,0))
    Expect-Failure 'Wrong image prefix stops' { Assert-Prefix $Data $Prefix }
    Expect-Failure 'Wrong SHA256 stops' { Assert-Hash $Data ('0' * 64) }
    function Get-PnpDevice { param([switch]$PresentOnly) [pscustomobject]@{InstanceId='USB\VID_05C6&PID_9008\test'} }
    function Get-PnpDeviceProperty { param($InstanceId,$KeyName) [pscustomobject]@{Data='QUSB_BULK_CID:042F_SN:AAAAAAAA'} }
    Expect-Failure 'Different EDL board serial stops' { Assert-Board }
    function Get-PnpDeviceProperty { param($InstanceId,$KeyName) [pscustomobject]@{Data='QUSB_BULK_CID:042F_SN:7B57A3EB'} }
    Assert-Board
    $TaskPass++
    Write-Output 'PASS: Matching EDL board serial accepted'
    function Get-PnpDevice { param([switch]$PresentOnly) @([pscustomobject]@{InstanceId='USB\VID_05C6&PID_9008\first'},[pscustomobject]@{InstanceId='USB\VID_05C6&PID_9008\second'}) }
    Expect-Failure 'Multiple EDL devices stop' { Assert-Board }
    $Installer = Join-Path $TaskTestDir 'mock-installer.ps1'
    $RunId = 'test-bios-run'
    $Bundle = $TaskTestDir
    $script:BiosCalls = New-Object 'System.Collections.Generic.List[string]'
    $InstallerText = @'
param($Stage,$RunId,$Bundle)
[void]$script:BiosCalls.Add($Stage)
if ($Stage -eq $script:FailStage) { throw 'Mocked device stage failure' }
'@
    # A called script has its own script scope; use a shared global for this mock only.
    $InstallerText = $InstallerText.Replace('$script:BiosCalls','$global:Q6AOfflineBiosCalls').Replace('$script:FailStage','$global:Q6AOfflineFailStage')
    $global:Q6AOfflineBiosCalls = $script:BiosCalls
    $global:Q6AOfflineFailStage = ''
    Set-Content -LiteralPath $Installer -Value $InstallerText
    foreach ($ProfileName in @('Linux','Android')) {
        $script:BiosCalls.Clear()
        Invoke-BiosStages @(Get-BiosStages $ProfileName 'Flash')
        $ExpectedWrite = if ($ProfileName -eq 'Linux') { 'RecoveryLinux' } else { 'FlashSpi' }
        if (($script:BiosCalls -join ',') -ne "BackupSpi,$ExpectedWrite") { throw 'BIOS write did not follow SPI backup' }
        $TaskPass++
        Write-Output "PASS: $ProfileName BIOS calls backup before SPI write and never writes UFS"
    }
    foreach ($Forbidden in @('Provision','FlashUfs','PatchUfs','RestoreUfs')) {
        $script:BiosCalls.Clear()
        Expect-Failure "BIOS entry point rejects $Forbidden" { Invoke-BiosStages @($Forbidden) }
        if ($script:BiosCalls.Count) { throw 'Forbidden UFS stage reached installer' }
    }
    $script:BiosCalls.Clear()
    $global:Q6AOfflineFailStage = 'BackupSpi'
    Expect-Failure 'Failed SPI backup stops BIOS write' { Invoke-BiosStages @(Get-BiosStages 'Android' 'Flash') }
    if (($script:BiosCalls -join ',') -ne 'BackupSpi') { throw 'BIOS write continued after failed backup' }
    $global:Q6AOfflineFailStage = ''
    Expect-Failure 'Existing BIOS RunId stops before backup can be reused' { Assert-NewBiosRun $TaskTestDir }
    $Record = Join-Path $TaskTestDir 'bios-switch.json'
    '{"profile":"Linux"}' | Set-Content -LiteralPath $Record
    Expect-Failure 'Boot/Restore rejects a RunId for the other profile' { Assert-BiosRunProfile $Record 'Android' }
    Expect-Failure 'Boot/Restore rejects an absent record' { Assert-BiosRunProfile (Join-Path $TaskTestDir 'absent.json') 'Linux' }
    Assert-BiosRunProfile $Record 'Linux'
    $TaskPass++
    Write-Output 'PASS: Matching BIOS switch record accepted'
    $script:BiosCalls.Clear()
    Invoke-BiosStages @(Get-BiosStages 'Linux' 'Boot')
    Invoke-BiosStages @(Get-BiosStages 'Android' 'Boot')
    Invoke-BiosStages @(Get-BiosStages 'Android' 'Restore')
    if (($script:BiosCalls -join ',') -ne 'BootLinux,Boot,RestoreSpi') { throw 'Unexpected BIOS boot/restore stage' }
    $TaskPass++
    Write-Output 'PASS: Boot and Restore select their SPI-only stages'
    # Exercise the live readback guard with a local mock: a previous good file
    # must not make an incomplete or different CURRENT SPI acceptable.
    $SpiOptions = @()
    $script:LiveSpiData = New-Object byte[] 33554432
    $Reference = Join-Path $TaskTestDir 'known-spi.bin'
    [IO.File]::WriteAllBytes($Reference,$script:LiveSpiData)
    $ExpectedSpiHash = (Get-FileHash -LiteralPath $Reference -Algorithm SHA256).Hash
    function Start-FreshEdl { param($Options) }
    function Invoke-Edl {
        param([string[]]$Arguments,[string]$ExpectedPattern)
        if ($Arguments[0] -ne 'read-sector') { throw 'Unexpected live SPI mock operation' }
        [IO.File]::WriteAllBytes($Arguments[3],$script:LiveSpiData)
    }
    $script:LiveSpiData[100] = 1
    Expect-Failure 'Boot rejects different current SPI despite saved good reference' { Assert-LiveSpi $ExpectedSpiHash }
    $script:LiveSpiData = [byte[]](0,0,0)
    Expect-Failure 'Boot rejects incomplete current SPI' { Assert-LiveSpi $ExpectedSpiHash }
    $script:LiveSpiData = New-Object byte[] 33554432
    Assert-LiveSpi $ExpectedSpiHash
    $TaskPass++
    Write-Output 'PASS: Boot accepts complete matching current SPI'
    Write-Output "OFFLINE TESTS PASSED: $TaskPass. No USB device or Android contacted."
} finally {
    Remove-Variable Q6AOfflineBiosCalls,Q6AOfflineFailStage -Scope Global -ErrorAction SilentlyContinue
    $TaskResolvedDir = [IO.Path]::GetFullPath($TaskTestDir)
    $TaskAllowedRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
    if (-not $TaskResolvedDir.StartsWith($TaskAllowedRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Test cleanup target escaped the kit folder' }
    Remove-Item -LiteralPath $TaskResolvedDir -Recurse -Force
}
