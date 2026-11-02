"""Kişiyi arka plandan ayırır (BiRefNet portrait, ONNX). Her kare için RGBA PNG yazar.

python maskele.py <video> --bas 0.1 --kare 135 --cikti <proje>/work/mk

Kare başına CPU'da ~10-15 sn sürer. Sadece kesik kullanılan saniyeleri maskele.
Çıkan kare numaraları teslim.py'deki maske kareleriyle birebir eşleşir.
"""
import argparse, glob, os, subprocess, sys, tempfile
import numpy as np, onnxruntime as ort
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAY = [os.path.join(KOK, "models", "birefnet-portrait.onnx"), os.path.expanduser("~/.u2net/birefnet-portrait.onnx")]
p = argparse.ArgumentParser(); p.add_argument("video"); p.add_argument("--bas", type=float, default=0.0)
p.add_argument("--kare", type=int, required=True); p.add_argument("--cikti", required=True); p.add_argument("--atla", type=int, default=0, help="bu numaradan önceki kareleri atla")
a = p.parse_args()
model = next((m for m in ADAY if os.path.exists(m)), None)
if not model: sys.exit("Model yok. Önce: bash scripts/kurulum.sh")
s = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
M = np.array([0.485, 0.456, 0.406], np.float32); SD = np.array([0.229, 0.224, 0.225], np.float32)
def maske(img):
    x = np.asarray(img.convert("RGB").resize((1024, 1024), Image.BILINEAR)).astype(np.float32) / 255
    o = s.run(None, {s.get_inputs()[0].name: ((x - M) / SD).transpose(2, 0, 1)[None]})[0][0, 0]
    o = 1 / (1 + np.exp(-o))
    return np.asarray(Image.fromarray((o * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR))

FL = "accurate_rnd+full_chroma_int+full_chroma_inp"
os.makedirs(a.cikti, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.bas), "-i", a.video, "-frames:v", str(a.kare), "-start_number", "0",
                    "-vf", f"scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags={FL},format=rgb24", os.path.join(tmp, "%04d.png")], check=True)
    for f in sorted(glob.glob(os.path.join(tmp, "*.png"))):
        i = int(os.path.basename(f)[:4]); o = os.path.join(a.cikti, os.path.basename(f))
        if i < a.atla or os.path.exists(o): continue
        im = Image.open(f).convert("RGB")
        Image.fromarray(np.dstack([np.asarray(im), maske(im)]), "RGBA").save(o)
        print(f"{i + 1}/{a.kare}", flush=True)
print("BITTI")
