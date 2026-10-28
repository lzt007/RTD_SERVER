param(
    [ValidateSet('api','resources','test')][string]$Service='api',
    [string]$Python='python'
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if ($Service -eq 'api') { & $Python -m rtd }
    elseif ($Service -eq 'resources') { & $Python -m rtd.resources }
    else {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & node --test tests/test_admin_web.mjs
    }
    exit $LASTEXITCODE
} finally { Pop-Location }
