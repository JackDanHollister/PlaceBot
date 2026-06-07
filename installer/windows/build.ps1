<#
.SYNOPSIS
    Assemble a self-contained PlaceBot runtime for the Windows installer.

.DESCRIPTION
    Downloads the official Python *embeddable* package (a minimal, no-installer
    CPython), enables site-packages, bootstraps pip, and pip-installs the
    PlaceBot wheel (with the [gui] extra) into it. The result in -StageDir is a
    fully portable directory that the Inno Setup script (placebot.iss) packages.

    Because PlaceBot is installed as a normal wheel (not frozen with
    PyInstaller), the GUI launcher's Path(__file__) / importlib.resources lookups
    all resolve correctly - no freeze-time asset/metadata collection needed.

.PARAMETER WheelPath
    Path to the built placebot wheel (e.g. dist\placebot-1.2.5-py3-none-any.whl).

.PARAMETER PythonVersion
    CPython version to embed (e.g. 3.11.9).

.PARAMETER StageDir
    Output directory for the assembled runtime (default: build\win\PlaceBot).
#>
param(
    [Parameter(Mandatory = $true)][string]$WheelPath,
    [Parameter(Mandatory = $true)][string]$PythonVersion,
    [string]$StageDir = "build\win\PlaceBot"
)

$ErrorActionPreference = "Stop"

$pyShort = ($PythonVersion -split '\.')[0..1] -join ''   # e.g. 3.11.9 -> 311
$runtime = Join-Path $StageDir "python"

Write-Host "==> Staging PlaceBot runtime in $StageDir (Python $PythonVersion)"
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

# 1. Download + extract the embeddable Python.
$embedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$embedZip = Join-Path $env:TEMP "python-embed.zip"
Write-Host "==> Downloading $embedUrl"
Invoke-WebRequest -Uri $embedUrl -OutFile $embedZip
Expand-Archive -Path $embedZip -DestinationPath $runtime -Force

# 2. Enable site-packages: uncomment "import site" and add the site dir to the
#    embeddable distribution's path file (python<ver>._pth).
$pthFile = Join-Path $runtime "python$pyShort._pth"
Write-Host "==> Enabling site-packages via $pthFile"
$pth = Get-Content $pthFile
$pth = $pth -replace '^#\s*import site', 'import site'
($pth + "Lib\site-packages") | Set-Content -Encoding ascii $pthFile

# 3. Bootstrap pip.
$getPip = Join-Path $env:TEMP "get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
& "$runtime\python.exe" $getPip --no-warn-script-location

# 4. Install the wheel + the [gui] extra. The PEP 508 "name[extra] @ file://"
#    form installs THIS wheel as placebot (pinning the version) while pulling
#    streamlit and the runtime deps from PyPI.
$wheelFull = (Resolve-Path $WheelPath).Path
$wheelUri = "file:///" + ($wheelFull -replace '\\', '/')
Write-Host "==> Installing placebot[gui] from $wheelFull"
& "$runtime\python.exe" -m pip install --no-warn-script-location "placebot[gui] @ $wheelUri"

# 5. Smoke-test the import path used by the desktop shortcut.
& "$runtime\python.exe" -c "import placebot, streamlit; print('placebot', placebot.__version__, '/ streamlit', streamlit.__version__)"

Write-Host "==> Runtime staged successfully at $StageDir"
