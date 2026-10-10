<#
Staged replay of the Q6A / THGJFCT2T84BAKCB experiment, 2026-10-10.
Check is offline. Other stages require an explicit Stage and RunId.
Bundle defaults to the locally prepared path; all paths resolve from this repository.
Full reinstall overwrites Android data. See README.md before device stages.
PowerShell 5.1+; run hardware stages from an elevated PowerShell.
#>
param(
    [ValidateSet('Check','BackupSpi','Provision','FlashUfs','PatchUfs','FlashSpi','Boot','BootLinux','RestoreSpi','RestoreUfs','RecoveryLinux')]
    [string]$Stage = 'Check',
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')]
    [string]$RunId,
    [string]$Bundle
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$Lock = Get-Content -LiteralPath (Join-Path $Repo 'firmware\android15-ufs-toshiba512\bundle.lock.json') -Raw | ConvertFrom-Json
if (-not $Bundle) {
    $SavedPath = Join-Path $Repo 'artifacts\bundle-path.txt'
    if (Test-Path -LiteralPath $SavedPath) { $Bundle = (Get-Content -LiteralPath $SavedPath -Raw).Trim() }
    else { $Bundle = Join-Path (Join-Path $Repo 'artifacts') $Lock.folder }
}
if (-not (Test-Path -LiteralPath (Join-Path $Bundle 'manifest.json'))) { throw 'Bundle not found. Run tools/windows/experimental/Prepare-Bundle.ps1 -Source <folder-or-zip> first, or pass -Bundle.' }
$Kit = (Resolve-Path -LiteralPath $Bundle).ProviderPath
$ManifestHash = (Get-FileHash -LiteralPath (Join-Path $Kit 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ManifestHash -ne $Lock.manifest_sha256) { throw 'Bundle manifest SHA256 does not match bundle-lock.json' }
$Manifest = Get-Content -LiteralPath (Join-Path $Kit 'manifest.json') -Raw | ConvertFrom-Json
$Tool = Join-Path $Kit 'tools\edl-ng.exe'
$Ufs = Join-Path $Kit 'firmware\ufs\asic'
$Spi = Join-Path $Kit 'firmware\spinor'
$Candidate = Join-Path $Kit 'images\xbl-ufs30-power-test.elf'
$SpiCandidate = Join-Path $Kit 'images\spi-android-ufs30-power-test.bin'
$UfsOptions = @('--memory','ufs','--maxpayload','16384','--loader',(Join-Path $Ufs 'prog_firehose_lite.elf'))
$SpiOptions = @('--memory','spinor','--loader',(Join-Path $Spi 'prog_firehose_ddr.elf'))
$Xmls = @('rawprogram_unsparse0.xml','patch0.xml','rawprogram1.xml','patch1.xml','rawprogram2.xml','patch2.xml','rawprogram3.xml','patch3.xml','rawprogram4.xml','patch4.xml','rawprogram5.xml','patch5.xml')

function Assert-Hash([string]$Path,[string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected.ToLowerInvariant()) { throw "SHA256 mismatch: $Path" }
}
function Assert-Prefix([string]$Path,[string]$PrefixPath) {
    $Actual = [IO.File]::ReadAllBytes($Path)
    $Expected = [IO.File]::ReadAllBytes($PrefixPath)
    if ($Actual.Length -lt $Expected.Length) { throw "Truncated image: $Path" }
    for ($i=0; $i -lt $Expected.Length; $i++) {
        if ($Actual[$i] -ne $Expected[$i]) { throw "Unexpected image prefix at byte ${i}: $Path" }
    }
}
function Assert-Backup([string]$Path,[long]$Bytes) {
    if ((Get-Item -LiteralPath $Path).Length -ne $Bytes) { throw "Incomplete backup: $Path" }
    Assert-Hash $Path ((Get-Content -LiteralPath ($Path + '.sha256') -Raw).Trim())
}
function Save-Hash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() | Set-Content -LiteralPath ($Path + '.sha256')
}
function Assert-Board {
    $Devices = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_9008\\' })
    if ($Devices.Count -ne 1) { throw 'Expected exactly one USB 05C6:9008 device. Enter EDL and disconnect other EDL devices.' }
    $Description = (Get-PnpDeviceProperty -InstanceId $Devices[0].InstanceId -KeyName 'DEVPKEY_Device_BusReportedDeviceDesc').Data
    if ($Description -notmatch ('(?i)SN:' + [regex]::Escape($Manifest.board_serial) + '(?:\b|$)')) {
        throw "Board serial does not match this kit ($($Manifest.board_serial)): $Description"
    }
}
function Invoke-Edl([string[]]$Arguments,[string]$ExpectedPattern) {
    $Lines = New-Object 'System.Collections.Generic.List[string]'
    & $Tool @Arguments 2>&1 | ForEach-Object {
        $Line = $_.ToString()
        [void]$Lines.Add($Line)
        $Line
    } | Tee-Object -FilePath (Join-Path $RunDir ($Stage + '.log')) -Append | Out-Host
    $Code = $LASTEXITCODE
    if ($Code -ne 0 -or ($Lines -match '\[ERROR\]')) { throw "EDL failed (exit $Code). Stage stopped; inspect its log." }
    if ($ExpectedPattern -and -not ($Lines -match $ExpectedPattern)) { throw "Missing success response: $ExpectedPattern" }
}
function Start-FreshEdl([string[]]$Options) {
    # --loader does not replace a programmer that is already running.
    # The power handler needs no storage configure; reset first, then upload
    # the selected programmer on the next command from fresh Sahara.
    Invoke-Edl ($Options + @('reset','--mode','Edl','--delay','1')) "Power command 'Edl' sent successfully"
    Start-Sleep -Seconds 2
    Assert-Board
}
function Read-BackupSpi {
    $Path = Join-Path $RunDir 'spi-before.bin'
    if (Test-Path -LiteralPath $Path) { Assert-Backup $Path 33554432; return }
    Invoke-Edl ($SpiOptions + @('read-sector','0','8192',$Path,'--lun','0')) 'Successfully read'
    if ((Get-Item -LiteralPath $Path).Length -ne 33554432) { throw 'Incomplete SPI backup' }
    Save-Hash $Path
}
function Read-Xbl([string]$Name,[int]$Lun,[string]$Path) {
    Invoke-Edl ($UfsOptions + @('read-part',$Name,$Path,'--lun',[string]$Lun)) 'Successfully read partition'
    if ((Get-Item -LiteralPath $Path).Length -ne 3690496) { throw "Unexpected XBL partition size: $Name" }
}
function Assert-LiveSpi([string]$ExpectedHash) {
    Start-FreshEdl $SpiOptions
    $LiveSpi = Join-Path $RunDir ($Stage + '-live-spi.bin')
    Invoke-Edl ($SpiOptions + @('read-sector','0','8192',$LiveSpi,'--lun','0')) 'Successfully read'
    if ((Get-Item -LiteralPath $LiveSpi).Length -ne 33554432) { throw 'Incomplete live SPI readback' }
    Assert-Hash $LiveSpi $ExpectedHash
}

# Validate the frozen executable, loaders, XMLs, every referenced image and
# preservation files before touching a USB device. Never regenerate hashes
# automatically to make an unexpected file pass.
foreach ($Entry in $Manifest.files) {
    if ($Entry.path -match '(^|[\\/])\.\.([\\/]|$)' -or [IO.Path]::IsPathRooted($Entry.path)) { throw 'Invalid manifest path' }
    $Path = Join-Path $Kit $Entry.path
    Assert-Hash $Path $Entry.sha256
    if ((Get-Item -LiteralPath $Path).Length -ne $Entry.bytes) { throw "File size mismatch: $Path" }
}
if ($Manifest.board_serial -ne '7B57A3EB' -or $Manifest.chip -ne 'THGJFCT2T84BAKCB') { throw 'This kit is bound to the tested board and UFS model' }
if ($Stage -eq 'Check') {
    Write-Output "CHECK PASSED: $($Manifest.files.Count) frozen files. No USB device contacted."
    return
}
if (-not $RunId) { throw 'Hardware stages require -RunId, for example reinstall-20261010. Use the SAME RunId for all stages of one installation.' }
$RunDir = Join-Path (Join-Path $Kit 'runs') $RunId
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
Assert-Board

switch ($Stage) {
    'BackupSpi' {
        Start-FreshEdl $SpiOptions
        Read-BackupSpi
        Write-Output 'SAVED: full pre-installation SPI with SHA256 sidecar.'
    }
    'Provision' {
        Assert-Backup (Join-Path $RunDir 'spi-before.bin') 33554432
        Start-FreshEdl $UfsOptions
        Invoke-Edl ($UfsOptions + @('--loglevel','Debug','provision',(Join-Path $Kit 'provision_ufs31.xml'))) 'All 10/10 commands sent and ACKed successfully'
        Write-Output 'Provision ACKed. POWER OFF, wait 10 seconds, then enter EDL again before FlashUfs.'
    }
    'FlashUfs' {
        Assert-Backup (Join-Path $RunDir 'spi-before.bin') 33554432
        Start-FreshEdl $UfsOptions
        Push-Location $Ufs
        try { Invoke-Edl ($UfsOptions + @('rawprogram') + $Xmls) "'rawprogram' command finished successfully" }
        finally { Pop-Location }
        'Completed; patch XBL before normal boot.' | Set-Content -LiteralPath (Join-Path $RunDir 'ufs-flashed.txt')
    }
    'PatchUfs' {
        Assert-Backup (Join-Path $RunDir 'spi-before.bin') 33554432
        Start-FreshEdl $UfsOptions
        $Before = Join-Path $RunDir 'xbl_a-before.bin'
        if (-not (Test-Path -LiteralPath $Before)) {
            Read-Xbl 'xbl_a' 1 $Before
            Assert-Prefix $Before (Join-Path $Ufs 'xbl.elf')
            Save-Hash $Before
        }
        Assert-Backup $Before 3690496
        Assert-Prefix $Before (Join-Path $Ufs 'xbl.elf')
        $B = Join-Path $RunDir 'xbl_b-before.bin'
        if (-not (Test-Path -LiteralPath $B)) { Read-Xbl 'xbl_b' 2 $B; Save-Hash $B }
        Assert-Backup $B 3690496
        foreach ($Byte in [IO.File]::ReadAllBytes($B)) { if ($Byte -ne 0) { throw 'Unexpected populated B slot. Stop and inspect before writing.' } }
        $Target = Join-Path $RunDir 'xbl_a-candidate.bin'
        $Image = [IO.File]::ReadAllBytes($Before)
        $Patch = [IO.File]::ReadAllBytes($Candidate)
        [Array]::Copy($Patch,0,$Image,0,$Patch.Length)
        [IO.File]::WriteAllBytes($Target,$Image)
        Invoke-Edl ($UfsOptions + @('write-part','xbl_a',$Target,'--lun','1')) 'Successfully'
        $Readback = Join-Path $RunDir 'xbl_a-readback.bin'
        Read-Xbl 'xbl_a' 1 $Readback
        Assert-Hash $Readback (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
        Write-Output 'VERIFIED: full UFS xbl_a. Empty xbl_b left unchanged.'
    }
    'FlashSpi' {
        Assert-Backup (Join-Path $RunDir 'spi-before.bin') 33554432
        # Check the CURRENT board, rather than trusting an old readback file.
        Start-FreshEdl $UfsOptions
        $LiveXbl = Join-Path $RunDir 'xbl_a-before-spi.bin'
        Read-Xbl 'xbl_a' 1 $LiveXbl
        Assert-Prefix $LiveXbl $Candidate
        Start-FreshEdl $SpiOptions
        Invoke-Edl ($SpiOptions + @('write-sector','0',$SpiCandidate,'--lun','0')) 'Successfully wrote'
        $Readback = Join-Path $RunDir 'spi-readback.bin'
        Invoke-Edl ($SpiOptions + @('read-sector','0','8192',$Readback,'--lun','0')) 'Successfully read'
        Assert-Hash $Readback $Manifest.spi_candidate_sha256
        Write-Output 'VERIFIED: full 32 MiB Android SPI.'
    }
    'Boot' {
        Assert-Hash (Join-Path $RunDir 'spi-readback.bin') $Manifest.spi_candidate_sha256
        Assert-LiveSpi $Manifest.spi_candidate_sha256
        Invoke-Edl ($SpiOptions + @('reset','--mode','Reset','--delay','1')) "Power command 'Reset' sent successfully"
        Write-Output 'Normal boot requested. Check UART and adb sys.boot_completed.'
    }
    'BootLinux' {
        $Image = Join-Path $Kit 'recovery\spi-after-linux-restore.bin'
        $ExpectedHash = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash
        Assert-Hash (Join-Path $RunDir 'spi-linux-readback.bin') $ExpectedHash
        Assert-LiveSpi $ExpectedHash
        Invoke-Edl ($SpiOptions + @('reset','--mode','Reset','--delay','1')) "Power command 'Reset' sent successfully"
        Write-Output 'Linux boot requested. Check the kernel command line and UART; readback alone is not an OS boot test.'
    }
    'RestoreSpi' {
        $Before = Join-Path $RunDir 'spi-before.bin'
        Assert-Backup $Before 33554432
        Start-FreshEdl $SpiOptions
        Invoke-Edl ($SpiOptions + @('write-sector','0',$Before,'--lun','0')) 'Successfully wrote'
        $Readback = Join-Path $RunDir 'spi-restored.bin'
        Invoke-Edl ($SpiOptions + @('read-sector','0','8192',$Readback,'--lun','0')) 'Successfully read'
        Assert-Hash $Readback (Get-FileHash -LiteralPath $Before -Algorithm SHA256).Hash
        Write-Output 'VERIFIED: SPI restored to the state before this installation.'
    }
    'RestoreUfs' {
        $Before = Join-Path $RunDir 'xbl_a-before.bin'
        Assert-Backup $Before 3690496
        Assert-Prefix $Before (Join-Path $Ufs 'xbl.elf')
        Start-FreshEdl $UfsOptions
        Invoke-Edl ($UfsOptions + @('write-part','xbl_a',$Before,'--lun','1')) 'Successfully'
        $Readback = Join-Path $RunDir 'xbl_a-restored.bin'
        Read-Xbl 'xbl_a' 1 $Readback
        Assert-Hash $Readback (Get-FileHash -LiteralPath $Before -Algorithm SHA256).Hash
        Write-Output 'VERIFIED: original Android xbl_a restored. Full Android data/provisioning is NOT rolled back.'
    }
    'RecoveryLinux' {
        Assert-Backup (Join-Path $RunDir 'spi-before.bin') 33554432
        $Image = Join-Path $Kit 'recovery\spi-after-linux-restore.bin'
        Start-FreshEdl $SpiOptions
        Invoke-Edl ($SpiOptions + @('write-sector','0',$Image,'--lun','0')) 'Successfully wrote'
        $Readback = Join-Path $RunDir 'spi-linux-readback.bin'
        Invoke-Edl ($SpiOptions + @('read-sector','0','8192',$Readback,'--lun','0')) 'Successfully read'
        Assert-Hash $Readback (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash
        Write-Output 'VERIFIED: saved Linux BIOS restored. Boot NVMe with the I2C-disabled fallback entry.'
    }
}
