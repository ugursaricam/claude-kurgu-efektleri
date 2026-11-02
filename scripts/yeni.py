"""Şablondan yeni proje klasörü açar ve eksik görselleri videonun kendi karelerinden üretir.

python3 yeni.py <6-stil|7-efekt> <video> <proje klasörü>

Kendi görsellerin varsa (Reels kapakları, profil ızgarası, logolar) proje/assets'e
aynı adla koy; yeni.py var olan dosyaya dokunmaz.
"""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sab, video, proj = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
A = os.path.join(proj, "assets"); os.makedirs(os.path.join(A, "fonts"), exist_ok=True); os.makedirs(os.path.join(proj, "work"), exist_ok=True)
shutil.copy(os.path.join(KOK, "sablonlar", sab, "build.py"), os.path.join(proj, "build.py"))
for f in os.listdir(os.path.join(KOK, "sablonlar", "fontlar")):
    shutil.copy(os.path.join(KOK, "sablonlar", "fontlar", f), os.path.join(A, "fonts", f))
open(os.path.join(proj, "package.json"), "w").write('{"name":"kurgu","private":true}\n')
BEBAS = os.path.join(A, "fonts", "BebasNeue-Regular.ttf")

sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True).stdout or 3)
def kare(t, w=None):
    p = os.path.join(proj, "work", f"_k{t:.2f}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", p], check=True)
    im = Image.open(p).convert("RGB")
    return im.resize((w, int(im.height * w / im.width))) if w else im
def yaz(ad, im):
    p = os.path.join(A, ad)
    if not os.path.exists(p): im.save(p, quality=92); print("yer tutucu:", ad)
def etiket(im, metin):
    g = ImageDraw.Draw(im); f = ImageFont.truetype(BEBAS, im.width // 7)
    g.rectangle((0, int(im.height * .62), im.width, int(im.height * .78)), fill=(0, 0, 0))
    g.text((im.width // 2, int(im.height * .70)), metin, font=f, fill=(255, 220, 60), anchor="mm"); return im

zam = [sure * (i + 0.5) / 9 for i in range(9)]
# Reels kapakları (yörünge, profil ızgarası)
for i, n in enumerate(["insan", "claude", "gizli", "fincan", "komut", "sonuc", "diyet", "kopya", "internet"]):
    yaz(f"r_{n}.jpg", etiket(kare(zam[i], 360), f"REELS {i + 1}"))
# profil ızgarası 3x4
g = Image.new("RGB", (1080, 1920), (0, 0, 0))
for i in range(12):
    g.paste(kare(zam[i % 9], 356).crop((0, 0, 356, 474)), ((i % 3) * 362, 60 + (i // 3) * 480))
yaz("ig_grid.png", g)
# profil fotoğrafı: ilk karenin ortası
k0 = kare(zam[4]); s = min(k0.size) // 2
av = k0.crop(((k0.width - s) // 2, k0.height // 4, (k0.width + s) // 2, k0.height // 4 + s)).resize((200, 200))
m = Image.new("L", (200, 200), 0); ImageDraw.Draw(m).ellipse((0, 0, 199, 199), fill=255); av.putalpha(m); yaz("ig_avatar.png", av)
yaz("foto.jpg", kare(zam[2]).crop((0, 300, 1080, 1380)).resize((600, 600)))
st = Image.new("RGB", (1600, 160))
for i in range(16): st.paste(kare(zam[i % 9], 100).crop((0, 20, 100, 180)), (i * 100, 0))
yaz("strip.jpg", st)
# sıralama logoları: harfli yuvarlak (gerçek logoları kendin koy)
for n, c, h in [("claude", (217, 119, 87), "C"), ("chatgpt", (16, 163, 127), "G"), ("perplexity", (32, 128, 141), "P"), ("gemini", (66, 133, 244), "G"), ("deepseek", (77, 107, 254), "D")]:
    im = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 299, 299), 60, fill=c); d.text((150, 160), h, font=ImageFont.truetype(BEBAS, 200), fill="white", anchor="mm")
    yaz(f"logo_{n}.png", im)
for f in os.listdir(os.path.join(proj, "work")):
    if f.startswith("_k"): os.remove(os.path.join(proj, "work", f))
print("HAZIR", proj)
