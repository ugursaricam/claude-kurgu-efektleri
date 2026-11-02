"""Renk koruyan teslim: kaynağın çözünürlüğü, fps'i ve rengi değişmeden çıkar.

HyperFrames'in kendi mp4 çıkışı bt709 videoyu ~%5 koyulaştırıyor. Bu betik
klibi kayıpsız RGB'ye doğru dönüşümle açar, PNG dizisi render alır ve
x264'e doğru bt709 etiketleriyle geri kodlar.

python3 teslim.py <proje> <kaynak video> <maske klasörü> <maske başlangıç sn> <maske kare sayısı> <poster kare no> <çıktı.mp4>

HAZIRLA=1 ile çalıştırırsan render almadan durur (önizleme için).
"""
import sys, os, re, subprocess, glob, shutil
from PIL import Image

proj, src, mk, mk0, n, pk, out = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
src, mk, out = os.path.abspath(src), os.path.abspath(mk), os.path.abspath(out)
FL = "accurate_rnd+full_chroma_int+full_chroma_inp"
DEC = f"scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags={FL},format=rgb24"
ENC = f"scale=out_color_matrix=bt709:out_range=tv:flags={FL},format=yuv420p"
def R(*a): subprocess.run(list(a), check=True, cwd=proj)
A = os.path.join(proj, "assets"); W = os.path.join(proj, "work")
os.makedirs(W, exist_ok=True)

# 1) klip → kayıpsız RGB
R("ffmpeg", "-v", "error", "-y", "-i", src, "-vf", DEC, "-c:v", "png", "-an", "assets/klip.mov")
# 2) build.py'nin istediği poster kareleri (p_<sn>.jpg)
for t in sorted(set(re.findall(r"p_(\d+\.\d+)", open(os.path.join(proj, "build.py")).read()))):
    R("ffmpeg", "-v", "error", "-y", "-ss", t, "-i", "assets/klip.mov", "-frames:v", "1", "-q:v", "2", f"assets/p_{t}.jpg")
# 3) kesik: doğru renk + maske alfası
rgb = os.path.join(W, "rgb"); km = os.path.join(W, "kesikkare")
for d in (rgb, km): shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
R("ffmpeg", "-v", "error", "-y", "-ss", f"{mk0}", "-i", "assets/klip.mov", "-frames:v", str(n), "-start_number", "0", "work/rgb/%04d.png")
for i in range(n):
    c = Image.open(os.path.join(rgb, f"{i:04d}.png")).convert("RGB")
    try: al = Image.open(os.path.join(mk, f"{i:04d}.png")).split()[3]
    except Exception: al = Image.new("L", c.size, 0)   # maskesi olmayan kare saydam
    c.putalpha(al); c.save(os.path.join(km, f"{i:04d}.png"))
shutil.copy(os.path.join(km, f"{min(pk, n - 1):04d}.png"), os.path.join(A, "kesik_poster.png"))
fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip() or "50"
R("ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", "work/kesikkare/%04d.png", "-c:v", "png", "-pix_fmt", "rgba", "assets/kesik.mov")
# 4) kompozisyon
R(sys.executable, "build.py")
if os.environ.get("HAZIRLA"): sys.exit()
png = os.path.join(proj, "renders", "png"); shutil.rmtree(png, ignore_errors=True)
R("npx", "--yes", "hyperframes@0.6.16", "render", "-w", "1", "--fps", "50", "--format", "png-sequence", "--output", "renders/png", ".")
# 5) PNG → mp4 (doğru bt709)
os.makedirs(os.path.dirname(out), exist_ok=True)
R("ffmpeg", "-v", "error", "-y", "-framerate", "50", "-i", "renders/png/frame_%06d.png", "-i", "assets/sfx.wav", "-map", "0:v", "-map", "1:a",
  "-vf", ENC, "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
  "-c:a", "aac", "-b:a", "192k", "-shortest", "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0", "-movflags", "+faststart", out)
print(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,color_primaries,color_transfer,color_space:format=duration", "-of", "compact", out], capture_output=True, text=True).stdout)
print("BITTI", out)
