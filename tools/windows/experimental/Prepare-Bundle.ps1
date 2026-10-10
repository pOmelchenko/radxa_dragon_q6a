<# Connect a frozen bundle or extract its exact ZIP. No USB access. #>
param([Parameter(Mandatory=$true)][string]$Source)
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$Lock = Get-Content -LiteralPath (Join-Path $Repo 'firmware\android15-ufs-toshiba512\bundle.lock.json') -Raw | ConvertFrom-Json
$SourcePath = (Resolve-Path -LiteralPath $Source).ProviderPath
$Artifacts = Join-Path $Repo 'artifacts'
if (Test-Path -LiteralPath $SourcePath -PathType Container) {
    $BundlePath = $SourcePath
} else {
    if ((Get-Item -LiteralPath $SourcePath).Length -ne $Lock.archive_bytes) { throw 'Archive size does not match bundle-lock.json' }
    $Hash = (Get-FileHash -LiteralPath $SourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne $Lock.archive_sha256) { throw 'Archive SHA256 does not match bundle-lock.json' }
    $BundlePath = Join-Path $Artifacts $Lock.folder
    if (Test-Path -LiteralPath $BundlePath) { throw 'Bundle target already exists. Use -Source with the existing folder to verify it.' }
    New-Item -ItemType Directory -Path $Artifacts -Force | Out-Null
    $TaskDrive = New-Object System.IO.DriveInfo ([IO.Path]::GetPathRoot($Artifacts))
    if ($TaskDrive.AvailableFreeSpace -lt ($Lock.uncompressed_bytes + 67108864)) { throw 'Insufficient free space to extract the full bundle (more than 4 GB required).' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($SourcePath,$Artifacts)
}
# Validate using our source script; never execute code from an unchecked bundle.
& (Join-Path $PSScriptRoot 'Install-Q6A-Android.ps1') -Stage Check -Bundle $BundlePath
New-Item -ItemType Directory -Path $Artifacts -Force | Out-Null
$BundlePath | Set-Content -LiteralPath (Join-Path $Artifacts 'bundle-path.txt') -Encoding UTF8
Write-Output "BUNDLE READY: $BundlePath"
Write-Output 'No USB device contacted. Use Install-Q6A-Android.ps1 -Stage Check before device stages.'
