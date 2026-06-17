#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
REALESRGAN_DIR="$ROOT/Real-ESRGAN"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
python -m pip install --upgrade pip
pip install -r "$ROOT/requirements.txt"
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

if [ ! -d "$REALESRGAN_DIR" ]; then
  git clone https://github.com/xinntao/Real-ESRGAN.git "$REALESRGAN_DIR"
fi

cd "$REALESRGAN_DIR"
pip install --upgrade setuptools wheel
pip install facexlib gfpgan
pip install "git+https://github.com/xinntao/BasicSR.git"
if [ -f requirements.txt ]; then
  pip install -r requirements.txt --no-deps
fi
if [ ! -f "./realesrgan/version.py" ]; then
  cat > ./realesrgan/version.py <<'EOF'
# GENERATED VERSION FILE
__version__ = '0.3.0'
__gitsha__ = 'unknown'
version_info = ('0', '3', '0')
EOF
fi
python setup.py develop

export REALESRGAN_DIR="$REALESRGAN_DIR"
export OUTPUT_DIR="$ROOT/data/outputs"
export TMP_DIR="$ROOT/tmp"
export HOST_BASE_URL="${HOST_BASE_URL:-http://127.0.0.1:7860}"
export MODEL_NAME="${MODEL_NAME:-RealESRGAN_x4plus}"
export UPSCALE_OUTSCALE="${UPSCALE_OUTSCALE:-4}"
export API_KEY="${API_KEY:-change-me}"

mkdir -p "$OUTPUT_DIR" "$TMP_DIR"

cd "$ROOT"
python -m uvicorn app:app --host 0.0.0.0 --port 7860
