<# Parse the PowerShell examples without running any commands from them. #>
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$Count = 0
foreach ($File in Get-ChildItem -LiteralPath (Join-Path $Repo 'docs') -Filter '*.md' -Recurse) {
    $Text = Get-Content -LiteralPath $File.FullName -Raw -Encoding UTF8
    $Blocks = [regex]::Matches($Text,'(?ms)^```powershell\r?\n(.*?)^```[ \t]*(?:\r?\n|$)')
    foreach ($Block in $Blocks) {
        $Tokens = $null
        $Errors = $null
        [void][Management.Automation.Language.Parser]::ParseInput($Block.Groups[1].Value,[ref]$Tokens,[ref]$Errors)
        if ($Errors.Count) { throw "Invalid PowerShell example in $($File.FullName): $($Errors | Out-String)" }
        $Count++
    }
}
if ($Count -lt 1) { throw 'No PowerShell examples found' }
Write-Output "DOCUMENTATION CHECK PASSED: $Count PowerShell blocks parsed. No examples executed."
