$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root '.venv'
$PythonExe = Join-Path $Venv 'Scripts\python.exe'
$RuntimeDir = 'C:\aipi-upscale'
$NcnnDir = Join-Path $RuntimeDir 'realesrgan-ncnn-vulkan'

if (-not (Test-Path $PythonExe)) {
  throw 'Virtual environment not found. Run install.ps1 first.'
}

if (-not (Test-Path $NcnnDir)) {
  throw 'ncnn-vulkan executable not found. Run install.ps1 first.'
}

$env:NCNN_DIR = $NcnnDir
$env:OUTPUT_DIR = Join-Path $RuntimeDir 'outputs'
$env:TMP_DIR = Join-Path $RuntimeDir 'tmp'
$env:HOST_BASE_URL = 'http://127.0.0.1:7860'

if (-not $env:MODEL_NAME) { $env:MODEL_NAME = 'realesrgan-x4plus' }
if (-not $env:UPSCALE_OUTSCALE) { $env:UPSCALE_OUTSCALE = '4' }
if (-not $env:GPU_ID) { $env:GPU_ID = '0' }
if (-not $env:API_KEY) { $env:API_KEY = 'change-me' }

New-Item -ItemType Directory -Force -Path $env:OUTPUT_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:TMP_DIR | Out-Null

Push-Location $Root
try {
  & $PythonExe -m uvicorn app:app --host 0.0.0.0 --port 7860
}
finally {
  Pop-Location
}
