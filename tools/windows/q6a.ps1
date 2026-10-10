<# Common Q6A tools; Python 3.10+ must be available as python. #>
& python (Join-Path $PSScriptRoot '../q6a.py') @args
exit $LASTEXITCODE
