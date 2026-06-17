$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root '.venv'
$RuntimeDir = 'C:\aipi-upscale'
$NcnnDir = Join-Path $RuntimeDir 'realesrgan-ncnn-vulkan'
$ZipPath = Join-Path $RuntimeDir 'realesrgan-ncnn-vulkan.zip'
$DownloadUrl = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip'

function Resolve-Python311 {
  $candidates = @(
    'C:\Users\Administrator\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe',
    'C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe'
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  throw 'Python 3.11 not found. Please install Python 3.11 first.'
}

$BasePython = Resolve-Python311

if (-not (Test-Path $Venv)) {
  & $BasePython -m venv $Venv
}

$PythonExe = Join-Path $Venv 'Scripts\python.exe'
$PipExe = Join-Path $Venv 'Scripts\pip.exe'

& $PythonExe -m pip install --upgrade pip
& $PipExe install -r (Join-Path $Root 'requirements.txt')

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

if (-not (Test-Path $NcnnDir)) {
  Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath
  Expand-Archive -Path $ZipPath -DestinationPath $NcnnDir -Force
}

Write-Host 'Install complete.'
