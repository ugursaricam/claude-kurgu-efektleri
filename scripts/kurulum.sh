#!/usr/bin/env bash
# Bir kez çalıştır; tekrar çalıştırmak güvenli. Sonunda HAZIR yazar.
# Varsayılan: saç teli net kişi ayırma için BiRefNet (~970 MB) ve yedek olarak U2Net indirilir.
# --hizli: sadece U2Net (~170 MB); saç kenarı daha kaba olur.
set -e
KOK="$(cd "$(dirname "$0")/.." && pwd)"; cd "$KOK"
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo "EKSIK_FFMPEG  (Mac: brew install ffmpeg)"; exit 1; }
command -v npx >/dev/null || { echo "EKSIK_NODE  (Mac: brew install node)"; exit 1; }
PY=""
for v in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$v" >/dev/null && "$v" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 9) else 1)' 2>/dev/null; then PY="$v"; break; fi
done
[ -n "$PY" ] || { echo "EKSIK_PYTHON  (Mac: brew install python@3.12)"; exit 1; }
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -c "import numpy, PIL, onnxruntime, cv2" 2>/dev/null || .venv/bin/python -m pip install -q -r requirements.txt
mkdir -p models
indir() { [ -f "models/$1" ] || [ -f "$HOME/.u2net/$1" ] || { echo "$1 indiriliyor..."; curl -L --fail -o "models/$1.part" "$2" && mv "models/$1.part" "models/$1"; }; }
indir u2net_human_seg.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx
[ "$1" = "--hizli" ] || indir birefnet-portrait.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-portrait-epoch_150.onnx
npx --yes hyperframes@0.6.16 --version >/dev/null 2>&1 || true
echo HAZIR
