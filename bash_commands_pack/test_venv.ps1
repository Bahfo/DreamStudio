$VenvDir = ".\venv"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Virtual environment directory not found."
    exit 1
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $ActivateScript)) {
    Write-Host "Invalid virtual environment: activation script missing."
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "Invalid virtual environment: python executable missing."
    exit 1
}

try {
    & $PythonExe --version | Out-Null
    Write-Host "Virtual environment is valid and stable."
}
catch {
    Write-Host "Virtual environment is corrupted or unusable."
    exit 1
}