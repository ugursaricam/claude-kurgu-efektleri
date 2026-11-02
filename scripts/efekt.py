#!/usr/bin/env python3
"""25 kurgu efekti: konuşan kafa videosunun istenen saniyesine efekt bindirir.

Tek efekt:   python efekt.py yorunge video.mp4 cikti.mp4 --bas 3 --bit 6 --opt metin=CLAUDE
Plan:        python efekt.py --plan plan.json video.mp4 cikti.mp4
Kontrol:     python efekt.py --plan plan.json video.mp4 kontrol.jpg --kare 4.5,9.2
Liste:       python efekt.py --liste

Yüz YuNet ile takip edilir; kişi arka plandan ayrılır (varsayılan: BiRefNet, saç teli net; --hizli: U2Net).
Animasyonlar HyperFrames + GSAP ile çizilir; çıktı kaynağın rengini birebir korur (bt709) ve
orijinal sesi aynen taşır.
"""
import argparse, glob, hashlib, json, math, os, random, shutil, subprocess, sys
import numpy as np
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTLAR = os.path.join(KOK, "sablonlar", "fontlar")
FL = "accurate_rnd+full_chroma_int+full_chroma_inp"
DEC = f"scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags={FL},format=rgb24"
ENC = f"scale=out_color_matrix=bt709:out_range=tv:flags={FL},format=yuv420p"
W, H = 1080, 1920
TURUNCU, KREM, MUREKKEP = "#F06A1F", "#f3efe6", "#1d1d1b"
EFEKTLER, TAKMA = {}, {}


def efekt(ad, aciklama, kesik=False, ust=False, takma=()):
    def deco(fn):
        EFEKTLER[ad] = dict(fn=fn, aciklama=aciklama, kesik=kesik, ust=ust)
        for t in takma: TAKMA[t] = ad
        return fn
    return deco


# ---------------------------------------------------------------- yardımcılar
def sh(*a, **k): return subprocess.run(list(a), check=True, **k)
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def parca(s, ayrac="|"): return [x.strip() for x in str(s).split(ayrac) if x.strip()] if s else []


class Baglam:
    """Bir render'ın ortak durumu: GSAP satırları, CSS, yüz izi, kesik pencereleri."""

    def __init__(self, fps, dur, yuz, kartlar):
        self.fps, self.dur, self.yuzler, self.kartlar = fps, dur, yuz, kartlar
        self.J, self.CSS, self.kesikler, self.videolar, self.iz = [], {}, [], 0, 100

    # zaman: kare ızgarasına oturt
    def fr(self, t): return max(0.0, math.ceil(t * self.fps - 1e-6) / self.fps - 0.0005) if t > 0.001 else 0.0
    def S(self, sel, p, t): self.J.append(f'tl.set("{sel}", {p}, {self.fr(t):.4f});')
    def T(self, sel, a, b, t, d, ease="power3.out"):
        self.J.append(f'tl.fromTo("{sel}", {a}, {{...{b}, duration:{d}, ease:"{ease}"}}, {self.fr(t):.4f});')
    def css(self, ad, kural): self.CSS[ad] = kural
    def yuzen(self, sel, t, amp=12, d=0.6, n=1):
        self.J.append(f'tl.fromTo("{sel}", {{y:0}}, {{y:{-amp}, duration:{d}, ease:"sine.inOut", yoyo:true, repeat:{2 * n - 1}}}, {self.fr(t):.4f});')

    # yüz: (x, y, genişlik) 1080x1920 koordinatında
    def yuz(self, t):
        z = self.yuzler
        if t <= z[0][0]: return tuple(z[0][1:])
        for a, b in zip(z, z[1:]):
            if a[0] <= t <= b[0]:
                k = (t - a[0]) / max(b[0] - a[0], 1e-6)
                return tuple(a[i] + (b[i] - a[i]) * k for i in (1, 2, 3))
        return tuple(z[-1][1:])
    def yuz_ort(self, a, b):
        p = [self.yuz(a + (b - a) * i / 10) for i in range(11)]
        return tuple(sum(q[i] for q in p) / len(p) for i in range(3))

    # medya
    def video(self, bas, bit, stil="", media=None):
        self.videolar += 1; self.iz += 1
        return (f'<video id="v{self.videolar}" class="clip" data-start="{bas:.4f}" data-duration="{bit - bas + 0.05:.3f}" '
                f'data-track-index="{self.iz}" data-media-start="{bas if media is None else media:.3f}" src="assets/klip.mov" muted playsinline '
                f'style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover;{stil}"></video>')
    def kesik(self, bas, bit, stil=""):
        i = len(self.kesikler); self.kesikler.append((bas, bit)); self.iz += 1
        return (f'<video id="k{i}" class="clip" data-start="{bas:.4f}" data-duration="{bit - bas + 0.05:.3f}" data-track-index="{self.iz}" '
                f'data-media-start="0" src="assets/kesik{i}.mov" muted playsinline '
                f'style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;{stil}"></video>')
    def kart(self, i): return self.kartlar[i % len(self.kartlar)]


def spark(sz, col="#D97757"):
    r = []
    for i in range(12):
        a = math.radians(i * 30 + 8); L = 0.48 if i % 2 else 0.36
        r.append(f'<line x1="50" y1="50" x2="{50 + L * 100 * math.cos(a):.1f}" y2="{50 + L * 100 * math.sin(a):.1f}" stroke="{col}" stroke-width="9" stroke-linecap="round"/>')
    return f'<svg width="{sz}" height="{sz}" viewBox="0 0 100 100" style="flex:none">{"".join(r)}</svg>'


IMLEC = ('<svg width="64" height="80" viewBox="0 0 16 20"><path d="M1 1 L1 16 L5 12.5 L8 19 L10.5 18 L7.6 11.6 L13 11.6 Z" '
         'fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg>')


def giris(c, sel, t, n=0, ara=0.08, kimden="{opacity:0,scale:0.8}", ease="back.out(1.6)", d=0.35):
    c.T(sel, kimden, "{opacity:1,scale:1}", t + n * ara, d, ease)


def pencere_yuz(c, e, x, y, w, h, s=None, tasma=70):
    """Kişiyi bir pencereye koyar: yüz yatayda ortada, saçın üstü pencereden `tasma` px taşar.
    Dönen: (pencere html, sayfa koordinatında kesik stili)."""
    fx, fy, fw = c.yuz_ort(e["bas"], e["bit"])
    sac = fy - 0.95 * fw
    s = s or max(1.0, (w + 2 * abs(fx - W / 2)) / W + 0.02)
    left = w / 2 - fx * s; top = -sac * s - tasma
    left = min(0, max(w - W * s, left))
    vst = f"left:{left:.0f}px;top:{top:.0f}px;width:{W * s:.0f}px;height:{H * s:.0f}px;"
    kx, ky = x + left, y + top
    clip = f"clip-path:inset(0px {W * s - (w - left):.0f}px {ky + H * s - (y + h):.0f}px {-left:.0f}px);"
    return vst, f"left:{kx:.0f}px;top:{ky:.0f}px;width:{W * s:.0f}px;height:{H * s:.0f}px;{clip}"


# ================================================================ EFEKTLER
# Her efekt: fn(c, e, P) -> html. e: bas, bit ve seçenekler. P: benzersiz önek.
# Kesik isteyen efekt c.kesik(...) ile kişiyi istediği katmana koyar.

@efekt("cam-paneller", "Buzlu cam paneller başının arkasında süzülür, altta 'Claude ile düzenlendi'", kesik=True, takma=("glass-widgets", "cam", "paneller"))
def fx_cam(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    ust = max(60, fy - 820)
    buyuk, etiket = e.get("metin", "1"), e.get("etiket", "klip · Claude ile")
    ad, kul = e.get("ad", "Adın Soyadın"), e.get("kullanici", "@kullanici")
    vals = [float(v) for v in parca(e.get("degerler", "9|7|5|3|2|1"))]
    mx = max(vals) or 1
    bars = "".join(f'<i style="height:{max(5, v / mx * 100):.0f}px;background:{"#F2B33D" if j == 0 else "#D9583D"}"></i>' for j, v in enumerate(vals))
    c.css("cam", """.gls{position:absolute;border-radius:34px;background:rgba(255,248,240,.2);backdrop-filter:blur(24px) saturate(1.2);-webkit-backdrop-filter:blur(24px) saturate(1.2);border:1.5px solid rgba(255,255,255,.4);box-shadow:0 14px 40px rgba(0,0,0,.18);color:#fff;zoom:1.2}
.gs{font-size:30px;font-weight:600;display:flex;align-items:center;gap:12px}.gs2{font-size:26px;font-weight:500;opacity:.85;line-height:1.3}
.gdot{width:16px;height:16px;border-radius:50%;background:#e8644a;display:inline-block}.gbig{font-size:130px;font-weight:800;line-height:1;margin:4px 0 6px}
.gmono{font:20px Menlo,monospace;opacity:.8;margin:0 0 12px 6px;white-space:nowrap}.gwin{background:#fbf8f3;border-radius:18px;padding:12px 16px;height:250px;position:relative;color:#1d1d1b}
.gwt{font-size:28px;font-weight:800;margin-top:8px}.gwd{display:flex;gap:7px}.gwd b{width:12px;height:12px;border-radius:50%}.gwv{font:400 54px Bebas;color:#C9452E;line-height:1}
.glab{font-size:20px;font-weight:700;letter-spacing:2px;color:#fff;opacity:.85}.gmid{font-size:70px;font-weight:800;line-height:1;margin:4px 0 10px}
.gred{display:inline-block;background:#E0563B;border-radius:12px;padding:6px 16px;font-size:24px;font-weight:600}
.gico{width:76px;height:76px;border-radius:18px;background:#E0563B;display:flex;align-items:center;justify-content:center;flex:none}
.gpb{height:8px;border-radius:4px;background:rgba(255,255,255,.3);margin:22px 0 10px;overflow:hidden}.gpb div{height:100%;width:60%;background:#fff}
.gctl{display:flex;justify-content:center;align-items:center;gap:56px;font-size:36px}.gch{position:absolute;left:16px;right:16px;bottom:14px;height:100px;display:flex;align-items:flex-end;gap:10px}.gch i{flex:1}
.gbar{height:16px;border-radius:8px;background:rgba(255,255,255,.3);margin:18px 0 14px;overflow:hidden}.gbf{height:100%;width:71%;background:#fff;border-radius:8px}
.gname{font-size:32px;font-weight:800;white-space:nowrap}.gav{width:84px;height:84px;border-radius:50%;border:3px solid rgba(255,255,255,.8);object-fit:cover}
.gring{width:210px;height:210px;border-radius:50%;background:conic-gradient(#3ddc84 300deg,rgba(255,255,255,.3) 0);display:flex;align-items:center;justify-content:center}
.gring div{width:166px;height:166px;border-radius:50%;background:rgba(40,36,32,.5);display:flex;align-items:center;justify-content:center;text-align:center;font-size:56px;font-weight:800;line-height:.9}.gring span{font-size:26px;font-weight:600}
.gpill{position:absolute;left:50%;margin-left:-260px;top:1660px;width:520px;height:104px;border-radius:52px;display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:600;color:#fff;background:rgba(30,26,22,.45);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1.5px solid rgba(255,255,255,.35)}""")
    u = ust / 1.2
    h = f'''<div id="{P}g0" class="gls" style="left:25px;top:{u:.0f}px;width:310px;height:290px;padding:24px 28px"><div class="gs"><b class="gdot"></b>Claude</div><div class="gbig">{esc(buyuk)}</div><div class="gs2">{esc(etiket)}</div></div>
<div id="{P}g1" class="gls" style="left:25px;top:{u + 311:.0f}px;width:310px;height:330px;padding:18px"><div class="gmono">artifact · grafik.html</div><div class="gwin"><div class="gwd"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b></div><div class="gwt">{esc(e.get("grafik", "Bu hafta"))}</div><div class="gwv">{esc(e.get("grafik_deger", ""))}</div><div class="gch">{bars}</div></div></div>
<div id="{P}g2" class="gls" style="left:25px;top:{u + 661:.0f}px;width:310px;height:180px;padding:20px 26px"><div class="glab">{esc(e.get("kutu_etiket", "KAYDETME")).upper()}</div><div class="gmid">{esc(e.get("kutu", "12B"))}</div><div class="gred">{esc(e.get("kutu_alt", "en iyi Reels"))}</div></div>
<div id="{P}g3" class="gls" style="left:545px;top:{u:.0f}px;width:330px;height:170px;padding:22px 26px"><div class="gs"><b class="gdot" style="background:#ff4b3e"></b>Render ediliyor</div><div class="gbar"><div id="{P}gb" class="gbf"></div></div><div class="gs2">1080p · kayıpsız renk</div></div>
<div id="{P}g4" class="gls" style="left:545px;top:{u + 191:.0f}px;width:330px;height:150px;padding:22px 26px;display:flex;align-items:center"><div style="flex:1"><div class="gname">{esc(ad)}</div><div class="gs2">{esc(kul)}</div></div><img src="{c.kart(0)}" class="gav"></div>
<div id="{P}g5" class="gls" style="left:545px;top:{u + 361:.0f}px;width:330px;height:290px;padding:22px"><div style="display:flex;gap:16px;align-items:center"><div class="gico">{spark(54, "#fff")}</div><div><div class="glab" style="font-size:16px;letter-spacing:1.5px">ŞİMDİ DÜZENLENİYOR</div><div class="gname" style="font-size:30px">{esc(e.get("calan", "Arka plan sesi"))}</div><div class="gs2">{esc(e.get("calan_alt", "ses · 25 sn"))}</div></div></div><div class="gpb"><div id="{P}gp"></div></div><div class="gctl"><span>⏮</span><span style="font-size:52px">▶</span><span>⏭</span></div></div>
<div id="{P}g6" class="gls" style="left:605px;top:{u + 672:.0f}px;width:270px;height:270px;border-radius:50%;display:flex;align-items:center;justify-content:center"><div class="gring"><div>{esc(e.get("halka", "50"))}<br><span>{esc(e.get("halka_etiket", "fps"))}</span></div></div></div>'''
    h += c.kesik(a, b)
    h += f'<div id="{P}g7" class="gpill">Claude ile <b style="color:#FFB08A;margin-left:12px">düzenlendi</b></div>'
    for j in range(8):
        giris(c, f"#{P}g{j}", a, j, 0.07); c.yuzen(f"#{P}g{j}", a + 0.5 + j * 0.05, 8 + (j % 3) * 4, max(0.4, (b - a - 0.6) / 2))
    c.T(f"#{P}gb", "{width:'15%'}", "{width:'92%'}", a + 0.1, b - a - 0.2, "power1.inOut")
    c.T(f"#{P}gp", "{width:'10%'}", "{width:'70%'}", a + 0.1, b - a - 0.2, "none")
    return h


@efekt("belgesel", "Siyah-beyaz sen köşede, başının arkasında turuncu daire, sağ üstte satır satır başlık, isim bandı, Takip et → Takiptesin", kesik=True, takma=("red-collage", "documentary"))
def fx_belgesel(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    satir = parca(e.get("metin", "TEK KLİP.|25 EFEKT.|0 UYGULAMA."))
    renk = e.get("renk", TURUNCU); sk = 1.15
    # kişiyi sol alta kaydır: yüz (290, 1118) civarına gelir
    tx = 290 - (540 + (fx - 540) * sk); ty = 1118 - (960 + (fy - 960) * sk)
    nx, ny, nw = 290, 1118, fw * sk; r = 0.71 * nw
    g = f"filter:grayscale(1) contrast(1.12) brightness(.9);transform:translate({tx:.0f}px,{ty:.0f}px) scale({sk});transform-origin:540px 960px;"
    ts = "".join(f'<div id="{P}l{i}">{esc(" ".join(s.split()[:-1]))} <em>{esc(s.split()[-1])}</em></div>' if len(s.split()) > 1 else f'<div id="{P}l{i}"><em>{esc(s)}</em></div>' for i, s in enumerate(satir))
    c.css("belgesel", """.bbg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 30% 40%,#3a1a08 0%,#140904 55%,#050302 100%)}
.bbg:after{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,140,60,.07) 2px,transparent 2px),linear-gradient(90deg,rgba(255,140,60,.07) 2px,transparent 2px);background-size:90px 90px}
.btop{position:absolute;left:70px;top:150px;color:rgba(255,255,255,.75);font-size:26px;letter-spacing:6px;font-weight:600}
.btl{position:absolute;right:50px;top:300px;text-align:right;color:#fff;font:400 135px Bebas;line-height:.95;letter-spacing:2px}.btl em{font-style:normal}
.bln{display:inline-block;color:#fff;font:400 72px Bebas;padding:8px 22px 0;letter-spacing:3px}.blh{color:#fff;font-size:34px;margin-top:12px;opacity:.85}
.bfol{position:absolute;color:#fff;font-size:42px;font-weight:700;border-radius:18px;padding:18px 44px}""")
    h = f'''<div id="{P}bg" class="bbg"></div>
<div id="{P}dk" style="position:absolute;left:{nx - 0.05 * nw - r:.0f}px;top:{ny - 0.09 * nw - r:.0f}px;width:{2 * r:.0f}px;height:{2 * r:.0f}px;border-radius:50%;background:radial-gradient(circle,#FF8A3D 0%,{renk} 60%,#d4560f 100%);box-shadow:0 0 90px 30px {renk}8c,0 0 220px 80px {renk}40"></div>
<div id="{P}ut" class="btop">{esc(e.get("ust", "CLAUDE İLE KURGU")).upper()}</div>
<div class="btl">{ts.replace("<em>", '<em style="color:#FF8A3D">')}</div>'''
    h += c.kesik(a, b, g)
    h += f'''<div id="{P}bt" style="position:absolute;left:60px;top:1560px"><div class="bln" style="background:{renk}">{esc(e.get("ad", "ADIN SOYADIN").upper())}</div><div class="blh">{esc(e.get("kullanici", "@kullanici"))}</div></div>
<div id="{P}fo" class="bfol" style="right:60px;top:1575px;background:{renk}"><span id="{P}f1">Takip et</span><span id="{P}f2" style="display:none">Takiptesin</span></div>
<div id="{P}cu" style="position:absolute;left:880px;top:1620px;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5))">{IMLEC}</div>'''
    c.T(f"#{P}bg", "{opacity:0}", "{opacity:1}", a, 0.2, "none")
    c.T(f"#{P}dk", "{scale:0.6,opacity:0}", "{scale:1,opacity:1}", a + 0.05, 0.6)
    c.yuzen(f"#{P}dk", a + 0.7, 12, max(0.4, (b - a - 0.8) / 2))
    c.T(f"#{P}ut", "{opacity:0,y:-20}", "{opacity:1,y:0}", a + 0.6, 0.3)
    c.T(f"#{P}bt", "{x:-500}", "{x:0}", a + 0.6, 0.4)
    for i in range(len(satir)): c.T(f"#{P}l{i}", "{opacity:0,x:60}", "{opacity:1,x:0}", a + 0.8 + i * 0.17, 0.18)
    t = a + min(b - a - 0.3, 0.8 + len(satir) * 0.17 + 0.35)
    c.T(f"#{P}cu", "{x:260,y:300,opacity:0}", "{x:0,y:0,opacity:1}", t - 0.35, 0.3)
    c.S(f"#{P}f1", '{display:"none"}', t); c.S(f"#{P}f2", '{display:"inline"}', t)
    c.S(f"#{P}fo", '{backgroundColor:"#fff",color:"#111",scale:0.94}', t); c.T(f"#{P}fo", "{scale:0.94}", "{scale:1}", t + 0.04, 0.15)
    return h


@efekt("yorunge", "Reels kapakların başının etrafında döner: arkadan geçerken arkanda, önden geçerken önünde", kesik=True, takma=("orbit", "yörünge", "carousel-spin", "carousel"))
def fx_yorunge(c, e, P):
    a, b = e["bas"], e["bit"]; n = int(e.get("sayi", 8)); hiz = float(e.get("hiz", 150))
    olc = float(e.get("boyut", 1.0))
    def poz(i, t):
        fx, fy, fw = c.yuz(t)
        th = math.radians(i * 360 / n + hiz * (t - a)); co, si = math.cos(th), math.sin(th)
        x = fx + 1.3 * fw * co; y = fy + 0.4 * fw + 0.64 * fw * si - 0.23 * fw * co
        return x - 85, y - 151, (0.82 + 0.26 * si) * olc, si > 0, -co * 38
    c.css("orb", ".orb{position:absolute;left:0;top:0;width:170px;height:302px;border-radius:16px;object-fit:cover;box-shadow:0 14px 40px rgba(0,0,0,.55);border:3px solid rgba(255,255,255,.9);opacity:0}")
    arka = on = ""
    for i in range(n):
        for k in "bf":
            el = f'<img id="{P}o{i}{k}" class="orb" src="{c.kart(i)}">'
            if k == "b": arka += el
            else: on += el
    adim = 0.1; m = int((b - a) / adim) + 1
    for i in range(n):
        st = None
        for j in range(m):
            t = a + j * adim; x, y, s, f, ry = poz(i, t)
            v = f"x:{x:.1f},y:{y:.1f},scale:{s:.3f},rotationY:{ry:.1f}"
            for k in "bf":
                if j == 0: c.S(f"#{P}o{i}{k}", f"{{{v},transformPerspective:1200}}", t)
                else: c.J.append(f'tl.to("#{P}o{i}{k}", {{{v},duration:{adim},ease:"none"}}, {c.fr(t - adim):.4f});')
            if f != st:
                c.S(f"#{P}o{i}f", f"{{opacity:{1 if f else 0}}}", t); c.S(f"#{P}o{i}b", f"{{opacity:{0 if f else 1}}}", t); st = f
    c.T(f"#{P}dk", "{opacity:0}", "{opacity:1}", a, 0.25, "none")
    return f'<div id="{P}dk" style="position:absolute;inset:0;background:rgba(0,0,0,.25)"></div>' + arka + c.kesik(a, b) + on


@efekt("arka-kelime", "Dev bir kelime arkana düşer", kesik=True, takma=("backdrop-word", "backdrop", "kelime"))
def fx_arka_kelime(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    s = e.get("metin", "CLAUDE"); renk = e.get("renk", TURUNCU)
    boy = min(520, int(1900 / max(len(s), 1)))
    serif = e.get("font") == "serif"
    yaz = f'font:italic 500 {boy}px Playfair' if serif else f'font:400 {boy}px Bebas'
    h = f'<div id="{P}w" style="position:absolute;left:-40px;right:-40px;top:{fy - 1.0 * fw - boy * 0.78:.0f}px;text-align:center;{yaz};line-height:1;color:{renk};letter-spacing:4px;text-shadow:0 10px 40px rgba(0,0,0,.35)">{esc(s)}</div>'
    c.T(f"#{P}w", "{y:-900,opacity:1}", "{y:0,opacity:1}", a, 0.55, "bounce.out")
    c.T(f"#{P}w", "{scale:1}", "{scale:1.05}", a + 0.55, b - a - 0.55, "none")
    return h + c.kesik(a, b)


@efekt("spot", "Işıklar söner, sen aydınlık kalırsın; arkanda neon bir yazı yanar", kesik=True, takma=("spotlight", "neon"))
def fx_spot(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    s = e.get("metin", "Claude"); renk = e.get("renk", "#ff7a1f")
    boy = min(330, int(2200 / max(len(s), 1)))
    h = f'''<div id="{P}d" style="position:absolute;inset:0;background:radial-gradient(ellipse 60% 45% at {fx / W * 100:.0f}% {fy / H * 100:.0f}%,rgba(0,0,0,.25),rgba(0,0,0,.88) 80%)"></div>
<div id="{P}n" style="position:absolute;left:-40px;right:-40px;top:{fy - 1.05 * fw - boy * 0.5:.0f}px;text-align:center;font:italic 500 {boy}px Playfair;color:#fff1e3;text-shadow:0 0 8px #fff,0 0 22px {renk},0 0 48px {renk},0 0 90px {renk}">{esc(s)}</div>'''
    h += c.kesik(a, b, "filter:brightness(.9);")
    h += f'<div id="{P}v" style="position:absolute;inset:0;background:radial-gradient(ellipse 70% 55% at {fx / W * 100:.0f}% {fy / H * 100:.0f}%,transparent 55%,rgba(0,0,0,.6))"></div>'
    c.T(f"#{P}v", "{opacity:0}", "{opacity:1}", a, 0.25, "none")
    c.T(f"#{P}d", "{opacity:0}", "{opacity:1}", a, 0.25, "none")
    c.S(f"#{P}n", "{opacity:0}", a)
    for t, o in ((0.25, 1), (0.33, 0.2), (0.41, 1), (0.49, 0.4), (0.55, 1)): c.S(f"#{P}n", f"{{opacity:{o}}}", a + t)
    c.T(f"#{P}n", "{scale:0.9}", "{scale:1.04}", a + 0.25, b - a - 0.25, "power1.out")
    return h


@efekt("led-tabela", "Işıklar düşer, arkanda parlayan bir LED tabela kendini yazar", kesik=True, takma=("led-sign", "led"))
def fx_led(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    satir = parca(e.get("metin", "CLAUDE|İLE KURGU")); renk = e.get("renk", "#ffb340")
    boy = min(220, int(1700 / max(max(len(s) for s in satir), 1)))
    harfler = sum(len(s) for s in satir); hiz = min(0.07, (b - a - 0.6) / max(harfler, 1))
    c.css("led", f""".led{{font:400 {boy}px Bebas;letter-spacing:10px;line-height:1.05;color:transparent;background-image:radial-gradient(circle,{renk} 42%,transparent 46%);background-size:12px 12px;-webkit-background-clip:text;background-clip:text;filter:drop-shadow(0 0 10px {renk}) drop-shadow(0 0 28px {renk}aa)}}""")
    sp, k = "", 0
    for s in satir:
        sp += "<div>"
        for ch in s:
            sp += f'<span id="{P}c{k}" style="opacity:0">{esc(ch) if ch != " " else "&nbsp;"}</span>'; c.S(f"#{P}c{k}", "{opacity:1}", a + 0.35 + k * hiz); k += 1
        sp += "</div>"
    h = f'''<div id="{P}d" style="position:absolute;inset:0;background:rgba(0,0,0,.82)"></div>
<div class="led" style="position:absolute;left:0;right:0;top:{max(80, fy - 0.9 * fw - len(satir) * boy * 1.05):.0f}px;text-align:center">{sp}</div>'''
    c.T(f"#{P}d", "{opacity:0}", "{opacity:1}", a, 0.3, "none")
    return h + c.kesik(a, b, "filter:brightness(.85);")


@efekt("profil-duvari", "Reels ızgaran arkandaki duvarı doldurur, sayaç artar", kesik=True, takma=("profile-wall", "wall", "izgara"))
def fx_profil(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    hucre = "".join(f'<img id="{P}h{i}" src="{c.kart(i)}" style="width:100%;height:100%;object-fit:cover">' for i in range(12))
    bas_s, son_s = e.get("baslangic", "0"), e.get("son", "")
    etiket = e.get("etiket", "takipçi")
    h = f'''<div id="{P}p" style="position:absolute;left:90px;right:90px;top:110px;height:1180px;border-radius:34px;overflow:hidden;background:#000;box-shadow:0 20px 60px rgba(0,0,0,.5);display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:295px;gap:4px">{hucre}</div>'''
    h += c.kesik(a, b)
    if son_s:
        h += f'<div style="position:absolute;left:0;right:0;top:{min(1500, fy + 1.6 * fw):.0f}px;text-align:center;color:#fff;font-weight:800;font-size:110px;text-shadow:0 6px 30px rgba(0,0,0,.7)"><span id="{P}s">{esc(bas_s)}</span><div style="font-size:36px;font-weight:600;opacity:.9">{esc(etiket)}</div></div>'
        sayac(c, f"#{P}s", bas_s, son_s, a + 0.3, min(1.4, b - a - 0.5))
    c.T(f"#{P}p", "{y:80,opacity:0,rotation:-2}", "{y:0,opacity:1,rotation:0}", a, 0.55)
    for i in range(12): giris(c, f"#{P}h{i}", a + 0.15, i, 0.04)
    return h


def sayac(c, sel, bas_s, son_s, t, d):
    """'0' → '24,1B' gibi sayaç; birim ve ondalık son değerden alınır."""
    import re
    m = re.match(r"([\d.,]+)(.*)", str(son_s)); n0 = re.match(r"([\d.,]+)", str(bas_s))
    if not m: return
    v1 = float(m.group(1).replace(".", "").replace(",", ".")); v0 = float(n0.group(1).replace(".", "").replace(",", ".")) if n0 else 0
    ond = len(m.group(1).split(",")[1]) if "," in m.group(1) else 0
    c.J.append(f'(function(){{const o={{v:{v0}}};tl.to(o,{{v:{v1},duration:{d},ease:"power2.out",onUpdate:()=>{{document.querySelector("{sel}").textContent=o.v.toFixed({ond}).replace(".",",")+"{m.group(2)}";}}}},{c.fr(t):.4f});}})();')
    steps = 12
    for i in range(1, steps + 1):  # snapshot onUpdate çalıştırmaz: kare kare de yaz
        v = v0 + (v1 - v0) * (1 - (1 - i / steps) ** 2)
        c.J.append(f'tl.set("{sel}", {{textContent:"{v:.{ond}f}".replace(".",",")+"{m.group(2)}"}}, {c.fr(t + d * i / steps):.4f});')


@efekt("gurultu", "Reels kapakları başının arkasına üst üste yığılır", kesik=True, takma=("noise", "the-noise", "yigin"))
def fx_gurultu(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b); r = random.Random(7)
    n = int(e.get("sayi", min(14, int((b - a) / 0.22)))); h = ""
    for i in range(n):
        x = fx + r.uniform(-2.2, 2.2) * fw; y = fy - fw * r.uniform(0.2, 1.6)
        h += f'<img id="{P}n{i}" src="{c.kart(i)}" style="position:absolute;left:{x - 150:.0f}px;top:{y - 267:.0f}px;width:300px;height:534px;object-fit:cover;border-radius:20px;border:4px solid #fff;box-shadow:0 18px 50px rgba(0,0,0,.5);transform:rotate({r.uniform(-14, 14):.1f}deg);opacity:0">'
        c.T(f"#{P}n{i}", "{opacity:0,scale:1.6}", "{opacity:1,scale:1}", a + i * 0.22, 0.22, "power3.out")
    return h + c.kesik(a, b)


@efekt("tus-yagmuru", "Klavye tuşları arkana yağar", kesik=True, takma=("shortcut-rain", "rain", "yagmur"))
def fx_tus(c, e, P):
    a, b = e["bas"], e["bit"]; r = random.Random(3)
    tus = parca(e.get("metin", "⌘|C|V|Z|⇧|⌥|S|K|⏎|/")); n = int(e.get("sayi", 26)); h = ""
    for i in range(n):
        x = r.uniform(40, W - 180); t0 = a + r.uniform(0, max(0.1, b - a - 1.0)); d = r.uniform(0.9, 1.5)
        k = tus[i % len(tus)]
        h += f'<div id="{P}k{i}" style="position:absolute;left:{x:.0f}px;top:-200px;width:140px;height:140px;border-radius:26px;background:linear-gradient(#fafafa,#d9d9d9);box-shadow:0 8px 0 #9a9a9a,0 18px 30px rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;font-size:62px;font-weight:700;color:#222">{esc(k)}</div>'
        c.T(f"#{P}k{i}", f"{{y:0,rotation:{r.uniform(-40, 40):.0f}}}", f"{{y:{H + 260},rotation:{r.uniform(-200, 200):.0f}}}", t0, d, "power1.in")
    return h + c.kesik(a, b)


@efekt("yavas-yaklas", "Yavaş sinematik yaklaşma, oda bulanıklaşır, sen net kalırsın", kesik=True, takma=("slow-push", "push", "push-in"))
def fx_yavas(c, e, P):
    a, b = e["bas"], e["bit"]; z = min(2.0, float(e.get("zoom", 1.4))); bl = float(e.get("bulaniklik", 14))
    h = c.video(a, b, f"filter:blur({bl}px);opacity:0", a)
    vid = f"#v{c.videolar}"
    c.T(vid, "{opacity:0}", "{opacity:1}", a, 0.8, "none")
    kamera(c, a, b, z, b - a, gir="power1.inOut", cik=0.25)
    return h + c.kesik(a, b)


def kamera(c, a, b, z, gir_sure, gir="power3.out", cik=0.2, takip=False):
    """#kam'ı yüze doğru yakınlaştırır (transform-origin 0 0: ekran = s·p + t)."""
    adim = 0.1; n = max(1, int((b - a) / adim))
    for j in range(n + 1):
        t = a + j * adim
        fx, fy, fw = c.yuz(t) if takip else c.yuz_ort(a, b)
        k = min(1.0, (t - a) / max(gir_sure, 0.01)); k = 1 - (1 - k) ** 3 if gir == "power3.out" else (3 * k * k - 2 * k ** 3)
        s = 1 + (z - 1) * k
        tx = min(0, max(W - W * s, W / 2 - s * fx)); ty = min(0, max(H - H * s, H * 0.42 - s * fy))
        v = f"x:{tx:.1f},y:{ty:.1f},scale:{s:.4f}"
        if j == 0: c.S("#kam", f"{{{v},transformOrigin:'0 0'}}", t)
        else: c.J.append(f'tl.to("#kam", {{{v},duration:{adim},ease:"none"}}, {c.fr(t - adim):.4f});')
    c.J.append(f'tl.to("#kam", {{x:0,y:0,scale:1,duration:{cik},ease:"power2.inOut"}}, {c.fr(b - cik):.4f});')


@efekt("kilitlen", "Köşe parantezler yüzüne kilitlenir, kamera seni takip eder", ust=True, takma=("locked-on", "lock"))
def fx_kilit(c, e, P):
    a, b = e["bas"], e["bit"]; z = min(2.0, float(e.get("zoom", 1.35))); etiket = e.get("metin", "HEDEF")
    kamera(c, a, b, z, 0.35, takip=True)
    br = '<b style="position:absolute;width:70px;height:70px;border-color:#fff;border-style:solid;{}"></b>'
    kose = br.format("left:0;top:0;border-width:8px 0 0 8px") + br.format("right:0;top:0;border-width:8px 8px 0 0") + br.format("left:0;bottom:0;border-width:0 0 8px 8px") + br.format("right:0;bottom:0;border-width:0 8px 8px 0")
    h = f'<div id="{P}b" style="position:absolute;left:0;top:0;width:10px;height:10px;filter:drop-shadow(0 0 6px rgba(0,0,0,.6))">{kose}<span style="position:absolute;left:0;top:-58px;background:#ff3b30;color:#fff;font:700 30px Menlo,monospace;padding:4px 12px">{esc(etiket)}</span></div>'
    adim = 0.1; n = max(1, int((b - a) / adim))
    for j in range(n + 1):
        t = a + j * adim; fx, fy, fw = c.yuz(t)
        k = min(1.0, (t - a) / 0.35); s = 1 + (z - 1) * (1 - (1 - k) ** 3)
        tx = min(0, max(W - W * s, W / 2 - s * fx)); ty = min(0, max(H - H * s, H * 0.42 - s * fy))
        X, Y, Bw = s * fx + tx, s * fy + ty, s * fw * 1.25
        v = f"x:{X - Bw / 2:.1f},y:{Y - Bw * 0.62:.1f},width:{Bw:.1f},height:{Bw * 1.25:.1f}"
        if j == 0: c.S(f"#{P}b", f"{{{v}}}", t)
        else: c.J.append(f'tl.to("#{P}b", {{{v},duration:{adim},ease:"none"}}, {c.fr(t - adim):.4f});')
    c.T(f"#{P}b", "{scale:1.6,opacity:0}", "{scale:1,opacity:1}", a, 0.25)
    return h


@efekt("yaklas", "Tek kelimede hızlı yakınlaşma", ust=True, takma=("lean-in", "punch", "zoom"))
def fx_yaklas(c, e, P):
    a, b = e["bas"], e["bit"]; z = min(2.0, float(e.get("zoom", 1.4)))
    kamera(c, a, b, z, float(e.get("hiz", 0.12)), cik=0.15)
    return ""


@efekt("manset", "Yakınlaşma + iki satırlık manşet, ikinci satır beyaz kutuda", ust=True, takma=("headline-box", "headline"))
def fx_manset(c, e, P):
    a, b = e["bas"], e["bit"]; z = min(2.0, float(e.get("zoom", 1.2)))
    s = parca(e.get("metin", "BUNU|BİLMİYORDUM")) + [""]
    kamera(c, a, b, z, 0.3)
    h = f'''<div style="position:absolute;left:0;right:0;top:{e.get("y", 1330)}px;text-align:center">
<div id="{P}1" style="color:#fff;font-weight:900;font-size:84px;letter-spacing:-2px;text-shadow:0 6px 24px rgba(0,0,0,.6)">{esc(s[0])}</div>
<div id="{P}2" style="display:inline-block;margin-top:10px;background:#fff;color:#111;font-weight:900;font-size:84px;letter-spacing:-2px;padding:4px 26px">{esc(s[1])}</div></div>'''
    c.T(f"#{P}1", "{opacity:0,y:30}", "{opacity:1,y:0}", a + 0.1, 0.25)
    c.T(f"#{P}2", "{scaleX:0}", "{scaleX:1}", a + 0.3, 0.28)
    return h


@efekt("liste", "Claude'un görev listesi: her adım döner, sonra yeşil tik alır", ust=True, takma=("checklist", "todo", "to-do", "tasks", "gorevler"))
def fx_liste(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    ad = parca(e.get("metin", "Yüzün bulundu::her karede|Arka plandan ayrıldın::maske|Yazı arkana yerleşti::derinlik|Renkler korundu::renk|Render edildi::50 fps"))
    adim = [x.split("::") + [""] for x in ad]
    top = min(H - 140 - 86 * len(adim) - 110, fy + 0.95 * fw)
    rows = "".join(f'<div style="display:flex;align-items:center;gap:22px;height:86px;border-top:1px solid rgba(255,255,255,.08)"><span id="{P}c{j}" style="width:46px;height:46px;border-radius:50%;border:3px solid #555;color:transparent;font-size:28px;font-weight:900;display:flex;align-items:center;justify-content:center;flex:none">✓</span><span id="{P}t{j}" style="font-size:36px;color:#888;font-weight:600">{esc(x[0])}</span><span style="margin-left:auto;font:24px Menlo,monospace;color:#8f8d88">{esc(x[1])}</span></div>' for j, x in enumerate(adim))
    h = f'<div id="{P}k" style="position:absolute;left:50px;right:50px;top:{top:.0f}px;border-radius:32px;background:rgba(18,18,18,.74);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1.5px solid rgba(255,255,255,.14);padding:28px 34px;color:#fff"><div style="display:flex;align-items:center;gap:14px;font-size:34px;margin-bottom:16px">{spark(36)} <b>{esc(e.get("baslik", "Claude klibini düzenliyor"))}</b></div>{rows}</div>'
    c.T(f"#{P}k", "{y:300,opacity:0}", "{y:0,opacity:1}", a, 0.45, "back.out(1.3)")
    ara = (b - a - 0.7) / max(len(adim), 1)
    for j in range(len(adim)):
        t = a + 0.6 + j * ara
        c.S(f"#{P}c{j}", '{backgroundColor:"#2ecc71",borderColor:"#2ecc71",color:"#fff"}', t); c.S(f"#{P}t{j}", '{color:"#fff"}', t)
        c.T(f"#{P}c{j}", "{scale:0.6}", "{scale:1}", t, 0.2, "back.out(2)")
    return h


@efekt("yorum-kutusu", "Instagram yorum kutusuna bir kelime yazılır ve paylaşılır", ust=True, takma=("comment-box", "comment", "yorum"))
def fx_yorum(c, e, P):
    a, b = e["bas"], e["bit"]; s = e.get("metin", "ANİMASYON"); ad = e.get("kullanici", "@kullanici")
    hiz = min(0.12, (b - a - 1.2) / max(len(s), 1))
    harf = "".join(f'<span id="{P}h{i}" style="display:none">{esc(ch)}</span>' for i, ch in enumerate(s))
    h = f'''<div id="{P}p" style="position:absolute;left:40px;right:40px;top:1430px;opacity:0;display:flex;gap:18px;align-items:center;background:rgba(255,255,255,.96);border-radius:30px;padding:22px 26px;box-shadow:0 14px 40px rgba(0,0,0,.35)">
 <img src="{c.kart(0)}" style="width:72px;height:72px;border-radius:50%;object-fit:cover"><div><b style="font-size:28px;color:#111">{esc(ad)}</b><div style="font-size:40px;font-weight:700;color:#111">{esc(s)}</div></div><span style="margin-left:auto;font-size:44px;color:#ed4956">♥</span></div>
<div id="{P}b" style="position:absolute;left:30px;right:30px;top:1640px;height:120px;border-radius:60px;background:rgba(25,25,25,.9);display:flex;align-items:center;gap:20px;padding:0 20px 0 22px;color:#fff;font-size:40px">
 <img src="{c.kart(0)}" style="width:80px;height:80px;border-radius:50%;object-fit:cover"><span id="{P}y" style="color:#8e8e8e">Yorum ekle…</span><span>{harf}</span><b style="width:4px;height:48px;background:#3897f0"></b>
 <span id="{P}s" style="margin-left:auto;color:#3897f0;font-weight:700;opacity:.4">Paylaş</span></div>'''
    c.T(f"#{P}b", "{y:200,opacity:0}", "{y:0,opacity:1}", a, 0.35)
    c.S(f"#{P}y", '{display:"none"}', a + 0.45)
    for i in range(len(s)): c.S(f"#{P}h{i}", '{display:"inline"}', a + 0.45 + i * hiz)
    t = a + 0.55 + len(s) * hiz
    c.S(f"#{P}s", "{opacity:1}", t); c.T(f"#{P}s", "{scale:1}", "{scale:0.85,yoyo:true,repeat:1}", t + 0.25, 0.08, "none")
    c.T(f"#{P}b", "{opacity:1}", "{opacity:0}", t + 0.45, 0.2, "none")
    c.T(f"#{P}p", "{opacity:0,y:60}", "{opacity:1,y:0}", t + 0.45, 0.35, "back.out(1.5)")
    return h


@efekt("takip", "Takip et butonu çıkar ve Takiptesin'e döner", ust=True, takma=("tap", "follow", "the-tap"))
def fx_takip(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    an = float(e.get("an", a + (b - a) * 0.55)); renk = e.get("renk", "#0095f6")
    y = float(e.get("y", 0)) * H or min(1600, fy + 1.15 * fw)
    h = f'''<div id="{P}k" style="position:absolute;left:150px;right:150px;top:{y:.0f}px;height:150px;border-radius:34px;background:rgba(25,25,25,.85);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);display:flex;align-items:center;gap:24px;padding:0 30px;color:#fff;font-size:36px;line-height:1.2">
 <img src="{c.kart(0)}" style="width:96px;height:96px;border-radius:50%;object-fit:cover"><div><b>{esc(e.get("ad", "Adın Soyadın"))}</b><br><span style="font-size:28px;opacity:.75">{esc(e.get("kullanici", "@kullanici"))}</span></div>
 <div id="{P}f" style="margin-left:auto;background:{renk};color:#fff;font-weight:700;font-size:34px;border-radius:16px;padding:16px 30px"><span id="{P}1">Takip et</span><span id="{P}2" style="display:none">Takiptesin</span></div></div>
<div id="{P}c" style="position:absolute;left:{W - 290}px;top:{y + 95:.0f}px;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5))">{IMLEC}</div>'''
    c.T(f"#{P}k", "{y:120,opacity:0}", "{y:0,opacity:1}", a, 0.4, "back.out(1.5)")
    c.T(f"#{P}c", "{x:200,y:260,opacity:0}", "{x:0,y:0,opacity:1}", an - 0.4, 0.35)
    c.S(f"#{P}1", '{display:"none"}', an); c.S(f"#{P}2", '{display:"inline"}', an)
    c.S(f"#{P}f", '{backgroundColor:"#efefef",color:"#111"}', an); c.T(f"#{P}f", "{scale:0.9}", "{scale:1}", an, 0.18)
    return h


@efekt("damga", "Kocaman kırmızı bir damga ekrana iner", ust=True, takma=("reject-stamp", "stamp"))
def fx_damga(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    s = e.get("metin", "REDDEDİLDİ"); renk = e.get("renk", "#e0262b"); aci = float(e.get("aci", -12))
    y = float(e.get("y", 0)) * H or min(1500, fy + 1.0 * fw)
    boy = min(190, int(1500 / max(len(s), 1)))
    h = f'<div id="{P}d" style="position:absolute;left:0;right:0;top:{y:.0f}px;display:flex;justify-content:center"><div style="transform:rotate({aci}deg);border:14px solid {renk};border-radius:22px;padding:6px 34px 0;color:{renk};font:400 {boy}px Bebas;letter-spacing:6px;mix-blend-mode:normal;background:rgba(255,255,255,.08)">{esc(s)}</div></div>'
    c.T(f"#{P}d", "{scale:3,opacity:0}", "{scale:1,opacity:1}", a, 0.18, "power4.in")
    c.T("#kam", "{x:0}", "{x:14,yoyo:true,repeat:3}", a + 0.18, 0.04, "none")
    return h


@efekt("geri-sayim", "Başının üstünde 3, 2, 1 çevirmeli saat", ust=True, takma=("countdown-flip", "countdown"))
def fx_sayim(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b); n = int(e.get("kac", 3))
    y = max(80, fy - 1.25 * fw - 330); ara = (b - a) / n
    h = f'<div style="position:absolute;left:{fx - 150:.0f}px;top:{y:.0f}px;width:300px;height:330px;perspective:900px">'
    for i in range(n):
        d = n - i
        h += f'<div id="{P}{i}" style="position:absolute;inset:0;border-radius:30px;background:linear-gradient(#2a2a2a 50%,#1c1c1c 50%);box-shadow:0 20px 50px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;color:#fff;font:400 300px Bebas;opacity:0">{d}<i style="position:absolute;left:0;right:0;top:50%;height:4px;background:#000"></i></div>'
        c.S(f"#{P}{i}", "{opacity:1}", a + i * ara)
        c.T(f"#{P}{i}", "{rotationX:-90}", "{rotationX:0}", a + i * ara, 0.25)
        if i < n - 1: c.S(f"#{P}{i}", "{opacity:0}", a + (i + 1) * ara)
    return h + "</div>"


@efekt("mesajlar", "Mesaj bildirimleri birbiri ardına yumuşak bir parıltıyla düşer", ust=True, takma=("messages", "imessage", "bildirim"))
def fx_mesaj(c, e, P):
    a, b = e["bas"], e["bit"]; m = parca(e.get("metin", "Bunu nasıl yaptın?|Hangi uygulama bu?|Bana da gönder 🙏"))
    y0 = float(e.get("y", 0)) * H or 1250; ara = min(0.6, (b - a - 0.4) / max(len(m), 1)); h = ""
    for i, s in enumerate(m):
        h += f'''<div id="{P}{i}" style="position:absolute;left:50px;right:50px;top:{y0 + i * 170:.0f}px;height:150px;border-radius:36px;background:rgba(250,246,240,.78);backdrop-filter:blur(26px);-webkit-backdrop-filter:blur(26px);box-shadow:0 10px 40px rgba(255,230,200,.35);display:flex;align-items:center;gap:22px;padding:0 28px;opacity:0">
 <div style="width:86px;height:86px;border-radius:22px;background:linear-gradient(#5df07a,#24c043);display:flex;align-items:center;justify-content:center;font-size:52px;flex:none">💬</div>
 <div style="flex:1;min-width:0"><div style="display:flex;font-size:28px;color:#555"><b style="color:#111">{esc(e.get("baslik", "Mesajlar"))}</b><span style="margin-left:auto">şimdi</span></div><div style="font-size:36px;color:#111;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(s)}</div></div></div>'''
        c.T(f"#{P}{i}", "{opacity:0,y:-80,scale:0.9}", "{opacity:1,y:0,scale:1}", a + i * ara, 0.4, "back.out(1.6)")
    return h


@efekt("anahtarlar", "iPhone ayar kartındaki anahtarlar tek tek açılır", ust=True, takma=("apple-toggles", "toggles", "ayarlar"))
def fx_anahtar(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    m = parca(e.get("metin", "Kişiyi ayır|Yüzü takip et|Rengi koru|Render al")); renk = e.get("renk", "#34c759")
    top = min(H - 120 - 112 * len(m), fy + 1.0 * fw)
    rows = "".join(f'<div style="display:flex;align-items:center;height:112px;border-top:{"0" if i == 0 else "1px solid #e4e4e4"};font-size:40px;color:#111">{esc(s)}<div id="{P}t{i}" style="margin-left:auto;width:120px;height:72px;border-radius:36px;background:#e5e5ea;position:relative"><i id="{P}k{i}" style="position:absolute;left:4px;top:4px;width:64px;height:64px;border-radius:50%;background:#fff;box-shadow:0 3px 8px rgba(0,0,0,.25)"></i></div></div>' for i, s in enumerate(m))
    h = f'<div id="{P}c" style="position:absolute;left:60px;right:60px;top:{top:.0f}px;border-radius:36px;background:rgba(255,255,255,.95);padding:4px 36px;box-shadow:0 18px 50px rgba(0,0,0,.35)">{rows}</div>'
    c.T(f"#{P}c", "{y:200,opacity:0}", "{y:0,opacity:1}", a, 0.4, "back.out(1.3)")
    ara = (b - a - 0.6) / max(len(m), 1)
    for i in range(len(m)):
        t = a + 0.5 + i * ara
        c.J.append(f'tl.to("#{P}t{i}", {{backgroundColor:"{renk}",duration:0.2}}, {c.fr(t):.4f});')
        c.J.append(f'tl.to("#{P}k{i}", {{x:48,duration:0.2,ease:"power2.out"}}, {c.fr(t):.4f});')
    return h


@efekt("siralama", "Tier list düşer, Claude S'ye uçar", ust=True, takma=("tier-list", "tier", "tiers"))
def fx_siralama(c, e, P):
    a, b = e["bas"], e["bit"]
    diger = parca(e.get("digerleri", "ChatGPT|Perplexity|Gemini|DeepSeek")); oge = e.get("oge", "Claude")
    renk = [("S", "#ff7f7f"), ("A", "#ffbf7f"), ("B", "#ffdf7f"), ("C", "#bfff7f"), ("D", "#7fbfff"), ("E", "#9f7fff"), ("F", "#d77fff")]
    rows = "".join(f'<div id="{P}r{i}" style="height:92px;border-bottom:2px solid #2c2c2c;display:flex;align-items:center"><div style="width:96px;height:100%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:46px;color:#111;background:{c_}">{t}</div>' + (f'<span style="margin-left:20px;background:#2a2a2a;color:#fff;font-weight:700;font-size:32px;border-radius:12px;padding:10px 20px">{esc(diger[i - 1])}</span>' if 1 <= i <= len(diger) else "") + "</div>" for i, (t, c_) in enumerate(renk))
    h = f'''<div style="position:absolute;left:0;right:0;top:120px;text-align:center;font:400 120px Bebas;line-height:.95;color:#F2B33D;text-shadow:0 6px 24px rgba(0,0,0,.6)">{"<br>".join(esc(x) for x in parca(e.get("baslik", "YAPAY ZEKA|SIRALAMASI")))}</div>
<div style="position:absolute;left:110px;right:110px;top:1230px;border-radius:12px;overflow:hidden;background:#141414;border:3px solid #333">{rows}</div>
<div id="{P}o" style="position:absolute;left:228px;top:1235px;background:{TURUNCU};color:#fff;font-weight:800;font-size:40px;border-radius:16px;padding:16px 26px;display:flex;align-items:center;gap:12px;box-shadow:0 10px 30px rgba(0,0,0,.5)">{spark(40, "#fff")}{esc(oge)}</div>'''
    c.J.append(f'tl.fromTo("#{P} [id^={P}r]", {{x:-700,opacity:0}}, {{x:0,opacity:1,duration:0.3,ease:"power3.out",stagger:0.04}}, {c.fr(a):.4f});')
    c.T(f"#{P}o", "{y:-1300,rotation:-10}", "{y:0,rotation:-2}", a + min(0.7, (b - a) * 0.35), 0.55, "bounce.out")
    return h


@efekt("grafik", "Üstte gerçek izlenme grafiği, altta pencerede sen; başın pencereden taşar", kesik=True, takma=("chart", "kallaway", "liquid-glass-graph"))
def fx_grafik(c, e, P):
    a, b = e["bas"], e["bit"]
    deg = [float(x.replace(",", ".")) for x in parca(e.get("degerler", "9|7|5|3|2|1|1"))]
    et = parca(e.get("etiketler", "")) or [f"#{i + 1}" for i in range(len(deg))]
    yaz = parca(e.get("yazilar", "")) or [f"{v:g}".replace(".", ",") for v in deg]
    bas = parca(e.get("baslik", "En çok izlenen|Reels'lerim")) + [""]
    mx = max(deg) * 1.08; Y0, HH = 820, 470; n = len(deg); bw = min(110, 800 / n - 24); st = 860 / n
    bars = "".join(f'<div id="{P}b{j}" style="position:absolute;left:{170 + j * st:.0f}px;top:{Y0 - max(6, v / mx * HH):.0f}px;width:{bw:.0f}px;height:{max(6, v / mx * HH):.0f}px;border-radius:12px 12px 0 0;transform-origin:50% 100%;background:{"#F2C063" if j == 0 else "#D9583D"}"><b style="position:absolute;left:-40px;right:-40px;top:-60px;text-align:center;font:400 50px Bebas;color:{MUREKKEP}">{esc(yaz[j] if j < len(yaz) else "")}</b></div><div style="position:absolute;left:{170 + j * st - 15:.0f}px;top:{Y0 + 14}px;width:{bw + 30:.0f}px;text-align:center;font-size:22px;color:#4d473e;font-weight:700">{esc(et[j] if j < len(et) else "")}</div>' for j, v in enumerate(deg))
    ort = sum(deg) / n
    vst, kst = pencere_yuz(c, e, 36, 965, W - 72, H - 965)
    h = f'''<div style="position:absolute;inset:0;background:{KREM};background-image:linear-gradient(rgba(150,140,120,.13) 1.5px,transparent 1.5px),linear-gradient(90deg,rgba(150,140,120,.13) 1.5px,transparent 1.5px);background-size:44px 44px">
<div id="{P}tl" style="position:absolute;left:60px;top:80px;font-weight:800;font-size:68px;color:{MUREKKEP};letter-spacing:-1.5px;line-height:1.12">{esc(bas[0])}<br><span style="border-bottom:5px solid #C9452E"><em style="font-family:Playfair;font-weight:600;color:#C9452E">{esc(bas[1])}</em></span></div>
<div id="{P}av" style="position:absolute;left:150px;right:40px;top:{Y0 - ort / mx * HH:.0f}px;border-top:3px dashed #D9583D;transform-origin:0 50%"><span style="position:absolute;right:0;top:-38px;font:26px Menlo,monospace;color:#D9583D">ort. {esc(e.get("ortalama", f"{ort:.3g}".replace(".", ",")))}</span></div>{bars}
<div id="{P}w" style="position:absolute;left:36px;right:36px;top:965px;bottom:0;border-radius:56px 56px 0 0;overflow:hidden;box-shadow:0 -6px 30px rgba(0,0,0,.12)">{c.video(a, b, vst)}</div>
<div id="{P}kk" style="position:absolute;inset:0">{c.kesik(a, b, kst)}</div></div>'''
    for j in range(n): c.T(f"#{P}b{j}", "{scaleY:0}", "{scaleY:1}", a + 0.25 + j * 0.08, 0.45)
    c.T(f"#{P}av", "{scaleX:0}", "{scaleX:1}", a + 0.7, 0.4, "power2.out")
    c.T(f"#{P}tl", "{y:-30,opacity:0}", "{y:0,opacity:1}", a + 0.05, 0.35)
    c.T(f"#{P}w", "{y:300}", "{y:0}", a, 0.45); c.T(f"#{P}kk", "{y:300}", "{y:0}", a, 0.45)
    return h


@efekt("bolunmus-manset", "Manşet kartı yukarıdan iner, seni alt yarıya iter; başın pencereden taşar", kesik=True, takma=("split-headline", "split", "bolunmus"))
def fx_bolunmus(c, e, P):
    a, b = e["bas"], e["bit"]; s = parca(e.get("metin", "Bunu|Claude yaptı")); vurgu = e.get("vurgu", s[-1] if s else "")
    vst, kst = pencere_yuz(c, e, 40, 960, 1000, 900)
    ttl = "<br>".join(esc(x).replace(esc(vurgu), f'<i style="font-family:Playfair;color:#C96442">{esc(vurgu)}</i>') if vurgu else esc(x) for x in s)
    h = f'''<div style="position:absolute;inset:0;background:{KREM};background-image:radial-gradient(#d9d2c4 2px,transparent 2.5px);background-size:34px 34px"></div>
<div id="{P}t" style="position:absolute;left:0;right:0;top:150px;text-align:center">{f'<div style="display:inline-flex;align-items:center;gap:10px;background:#D97757;color:#fff;font-size:34px;font-weight:700;border-radius:14px;padding:8px 22px">{spark(30, "#fff")} {esc(e["etiket"])}</div>' if e.get("etiket") else ""}
<div style="margin-top:30px;font:400 104px Georgia,serif;color:{MUREKKEP};letter-spacing:-2px;line-height:1.08">{ttl}</div></div>
<div id="{P}w" style="position:absolute;left:40px;top:960px;width:1000px;height:900px;border-radius:48px;overflow:hidden;box-shadow:0 20px 60px rgba(60,40,20,.25)">{c.video(a, b, vst)}</div>
<div id="{P}kk" style="position:absolute;inset:0">{c.kesik(a, b, kst)}</div>'''
    c.T(f"#{P}t", "{y:-500}", "{y:0}", a, 0.45); c.T(f"#{P}w", "{y:400}", "{y:0}", a, 0.45); c.T(f"#{P}kk", "{y:400}", "{y:0}", a, 0.45)
    return h


@efekt("zaman-cizelgesi", "Üstte kurgu programı, oynatma çizgisi ilerler; altta pencerede sen", kesik=False, takma=("timeline", "auto-edit"))
def fx_zaman(c, e, P):
    a, b = e["bas"], e["bit"]
    rows = [x.split("::") + [""] for x in parca(e.get("metin", "kesim::duraklar silindi ✓|renk::doğal ton ✓|efektler::eklendi ✓|ses::seviye ayarlandı ✓"))]
    rr = "".join(f'<div style="display:flex;justify-content:space-between;align-items:center;height:70px;margin:0 30px;border-bottom:1px solid rgba(255,255,255,.07);font-size:30px"><span style="color:#b9a9d6">{esc(x)}</span><b style="font-weight:600;font-size:28px">{esc(y)}</b></div>' for x, y, *_ in rows)
    film = "".join(f'<img src="{c.kart(i)}" style="height:96px;width:64px;object-fit:cover">' for i in range(14))
    wav = "".join(f'<i style="flex:1;background:#e7865f;border-radius:3px;height:{8 + 38 * abs(math.sin(j * 0.7) * math.cos(j * 0.23)):.0f}px"></i>' for j in range(70))
    bas = parca(e.get("baslik", "Claude|render ediyor")) + [""]
    fx, fy, fw = c.yuz_ort(a, b); s = 1.05
    h = f'''<div style="position:absolute;inset:0;background:{KREM};background-image:radial-gradient(#d9d2c4 2px,transparent 2.5px);background-size:34px 34px"></div>
<div style="position:absolute;left:0;right:0;top:70px;text-align:center;font-weight:800;font-size:80px;color:{MUREKKEP};letter-spacing:-2px">{esc(bas[0])} <em style="font-family:Playfair;font-weight:600;color:#C96442">{esc(bas[1])}</em></div>
<div id="{P}z" style="position:absolute;left:60px;right:60px;top:200px;height:760px;border-radius:26px;background:#261d36;box-shadow:0 20px 50px rgba(40,20,60,.35);overflow:hidden;color:#fff">
 <div style="height:66px;background:#1d1529;display:flex;align-items:center;gap:12px;padding:0 24px;font-size:22px;color:#b9a9d6;letter-spacing:2px"><b style="width:18px;height:18px;border-radius:50%;background:#ff5f57"></b><b style="width:18px;height:18px;border-radius:50%;background:#febc2e"></b><b style="width:18px;height:18px;border-radius:50%;background:#28c840"></b><span>KURGU · RENDER</span></div>
 {rr}<div style="margin:24px 30px 0;height:96px;border-radius:10px;overflow:hidden;display:flex">{film}</div><div style="margin:14px 30px 0;height:60px;display:flex;align-items:center;gap:4px">{wav}</div>
 <div id="{P}ph" style="position:absolute;left:30px;top:{66 + 70 * len(rows) + 10}px;width:4px;height:200px;background:#ff5f57;box-shadow:0 0 10px #ff5f57"></div>
 <div style="position:absolute;left:30px;right:150px;bottom:40px;height:20px;border-radius:10px;background:rgba(255,255,255,.12);overflow:hidden"><div id="{P}pf" style="height:100%;width:65%;background:linear-gradient(90deg,#e7865f,#D97757)"></div></div></div>
<div id="{P}v" style="position:absolute;left:60px;right:60px;top:1000px;bottom:60px;border-radius:40px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)">{c.video(a, b, f"left:{480 - fx * s:.0f}px;top:{-(fy - 0.95 * fw) * s + 90:.0f}px;width:{W * s:.0f}px;height:{H * s:.0f}px;")}</div>'''
    c.T(f"#{P}ph", "{x:0}", "{x:780}", a, b - a, "none"); c.T(f"#{P}pf", "{width:'10%'}", "{width:'95%'}", a, b - a, "power1.inOut")
    c.T(f"#{P}z", "{y:-60,opacity:0}", "{y:0,opacity:1}", a, 0.4); c.T(f"#{P}v", "{y:150}", "{y:0}", a, 0.45)
    return h


@efekt("hikaye-kartlari", "Süre, görsel ve yorum kartları yukarıdan düşer, başlık başının üstünde durur", ust=True, takma=("story", "hikaye", "kartlar"))
def fx_hikaye(c, e, P):
    a, b = e["bas"], e["bit"]; fx, fy, fw = c.yuz_ort(a, b)
    yor = parca(e.get("yorumlar", "ANİMASYON|nasıl yaptın?|ANİMASYON|devamı 👀"))
    renk = ["#e74c3c", "#3498db", "#f1c40f", "#2ecc71"]
    bas = parca(e.get("baslik", "")); kt = parca(e.get("kart", "1 KLİP|0 UYGULAMA")) + [""]
    sure = e.get("sure", "0:45")
    h = f'''<div style="position:absolute;left:0;right:0;top:0;height:1000px;background:linear-gradient(rgba(0,0,0,.45),transparent)"></div>
<div id="{P}a" style="position:absolute;left:50px;top:150px;width:250px;height:290px;border-radius:26px;background:#fff;text-align:center;padding-top:22px;box-shadow:0 10px 30px rgba(0,0,0,.4);transform:rotate(-3deg)"><div style="font-size:22px;font-weight:700;color:#888;letter-spacing:2px">GEÇEN SÜRE</div>
 <div style="width:150px;height:150px;margin:14px auto 0;border-radius:50%;background:conic-gradient(#e2683c 290deg,#eee 0);display:flex;align-items:center;justify-content:center"><div style="width:118px;height:118px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:800;color:#222">{esc(sure)}</div></div></div>
<div id="{P}b" style="position:absolute;left:350px;top:120px;width:330px;height:380px;border-radius:22px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.5)"><img src="{c.kart(1)}" style="width:100%;height:100%;object-fit:cover"><div style="position:absolute;left:0;right:0;bottom:30px;text-align:center;color:#fff;font:400 56px Bebas;line-height:1;text-shadow:0 3px 12px #000">{esc(kt[0])}<br><span style="color:#FFE04A">{esc(kt[1])}</span></div></div>
<div id="{P}c" style="position:absolute;right:50px;top:150px;width:290px;border-radius:26px;background:#fff;padding:22px 24px;box-shadow:0 10px 30px rgba(0,0,0,.4);transform:rotate(3deg);font-size:28px;color:#111"><b>Yorumlar</b>{"".join(f'<div style="display:flex;align-items:center;gap:12px;margin-top:12px;font-weight:600"><i style="width:22px;height:22px;border-radius:50%;background:{renk[i % 4]}"></i>{esc(y)}</div>' for i, y in enumerate(yor))}</div>'''
    if bas:
        h += f'<div id="{P}t" style="position:absolute;left:0;right:0;top:520px;text-align:center;color:#fff;font-weight:800;font-size:50px;line-height:1.15;text-shadow:0 4px 24px rgba(0,0,0,.85)">{"<br>".join(esc(x) for x in bas)}</div>'
        c.T(f"#{P}t", "{y:30,opacity:0}", "{y:0,opacity:1}", a + 0.35, 0.35)
    for j, k in enumerate("abc"):
        c.T(f"#{P}{k}", "{y:-500,opacity:0}", "{y:0,opacity:1}", a + j * 0.1, 0.45, "back.out(1.6)"); c.yuzen(f"#{P}{k}", a + 0.6 + j * 0.05, 10, max(0.3, (b - a - 0.8) / 2))
    return h


# ================================================================ HAZIRLIK
def yuz_izi(klip, dur, fps, cache):
    if os.path.exists(cache): return json.load(open(cache))
    import cv2
    det = cv2.FaceDetectorYN.create(os.path.join(KOK, "models", "yunet.onnx"), "", (540, 960), 0.6, 0.3, 5000)
    cap = cv2.VideoCapture(klip); out = []; t = 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, fr = cap.read()
        if not ok: break
        sx, sy = W / fr.shape[1], H / fr.shape[0]
        k = cv2.resize(fr, (540, 960)); det.setInputSize((540, 960)); _, f = det.detect(k)
        if f is not None and len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])[:4]
            out.append([round(t, 2), float((x + w / 2) * 2 * sx), float((y + h / 2) * 2 * sy), float(w * 2 * sx)])
        t += 0.1
    if not out: out = [[0, W / 2, H * 0.42, 300]]
    # yumuşat
    for i in range(1, 4):
        out = [[p[0]] + [sum(q[j] for q in out[max(0, k - 1):k + 2]) / len(out[max(0, k - 1):k + 2]) for j in (1, 2, 3)] for k, p in enumerate(out)]
    json.dump(out, open(cache + ".tmp", "w")); os.replace(cache + ".tmp", cache); return out


def model_var(ad):
    return any(os.path.exists(os.path.join(d, ad)) for d in (os.path.join(KOK, "models"), os.path.expanduser("~/.u2net")))


def maske_motoru(kaliteli):
    import onnxruntime as ort
    adlar = ["birefnet-portrait.onnx"] if kaliteli else ["u2net_human_seg.onnx"]
    for d in (os.path.join(KOK, "models"), os.path.expanduser("~/.u2net")):
        for a in adlar:
            if os.path.exists(os.path.join(d, a)):
                s = ort.InferenceSession(os.path.join(d, a), providers=["CPUExecutionProvider"]); boy = 1024 if kaliteli else 320
                M = np.array([0.485, 0.456, 0.406], np.float32); SD = np.array([0.229, 0.224, 0.225], np.float32)
                def mas(im):
                    x = np.asarray(im.resize((boy, boy), Image.BILINEAR)).astype(np.float32) / 255
                    o = s.run(None, {s.get_inputs()[0].name: ((x - M) / SD).transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
                    o = 1 / (1 + np.exp(-o)) if kaliteli else (o - o.min()) / max(o.max() - o.min(), 1e-6)
                    return Image.fromarray((o * 255).astype(np.uint8)).resize(im.size, Image.BILINEAR)
                return mas
    sys.exit("Maske modeli yok. Önce: bash scripts/kurulum.sh" + (" (kaliteli mod için BiRefNet gerekir)" if kaliteli else ""))


def kesikleri_yap(c, is_kl, kaliteli, fps, kareler=None):
    """kareler verilirse (kontrol modu) sadece o anlara maske çıkarılır, diğer kareler en yakınınkini kullanır."""
    mas = None; mk = os.path.join(is_kl, "work", "mk" + ("_k" if kaliteli else "_h")); os.makedirs(mk, exist_ok=True)
    for i, (a, b) in enumerate(c.kesikler):
        n = int(math.ceil((b - a + 0.05) * fps)) + 1; ilk = int(round(a * fps))
        rgb = os.path.join(is_kl, "work", "rgb"); shutil.rmtree(rgb, ignore_errors=True); os.makedirs(rgb)
        sh("ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", os.path.join(is_kl, "assets", "klip.mov"), "-frames:v", str(n), "-start_number", "0", os.path.join(rgb, "%05d.png"))
        kk = os.path.join(is_kl, "work", f"kesik{i}"); shutil.rmtree(kk, ignore_errors=True); os.makedirs(kk)
        dosyalar = sorted(glob.glob(os.path.join(rgb, "*.png")))
        hedef = None
        if kareler:
            ic = [int(round(t * fps)) - ilk for t in kareler if a - 0.1 <= t <= b + 0.1]
            hedef = [min(max(x, 0), len(dosyalar) - 1) for x in ic] or [len(dosyalar) // 2]
        for j, f in enumerate(dosyalar):
            jj = min(hedef, key=lambda x: abs(x - j)) if hedef else j
            m = os.path.join(mk, f"{ilk + jj:06d}.png")
            if jj != j:
                if not os.path.exists(m): mas = mas or maske_motoru(kaliteli); mas(Image.open(dosyalar[jj]).convert("RGB")).save(m)
                im = Image.open(f).convert("RGB"); im.putalpha(Image.open(m).convert("L")); im.save(os.path.join(kk, f"{j:05d}.png")); continue
            im = Image.open(f).convert("RGB")
            if not os.path.exists(m):
                mas = mas or maske_motoru(kaliteli); mas(im).save(m)
                print(f"  maske {i + 1}/{len(c.kesikler)}: {j + 1}/{len(dosyalar)}", flush=True)
            im.putalpha(Image.open(m).convert("L")); im.save(os.path.join(kk, f"{j:05d}.png"))
        sh("ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(kk, "%05d.png"), "-c:v", "png", "-pix_fmt", "rgba", os.path.join(is_kl, "assets", f"kesik{i}.mov"))


def kartlari_hazirla(is_kl, klasor, dur):
    A = os.path.join(is_kl, "assets"); out = []
    if klasor and os.path.isdir(klasor):
        for i, f in enumerate(sorted(x for x in os.listdir(klasor) if x.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))):
            im = Image.open(os.path.join(klasor, f)).convert("RGB"); im.thumbnail((540, 960)); p = f"assets/kart{i}.jpg"; im.save(os.path.join(is_kl, p), quality=90); out.append(p)
    if not out:  # videonun kendi karelerinden
        for i in range(9):
            t = dur * (i + 0.5) / 9; p = f"assets/kart{i}.jpg"
            sh("ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", os.path.join(A, "klip.mov"), "-frames:v", "1", "-vf", "scale=360:-1", "-q:v", "3", os.path.join(is_kl, p)); out.append(p)
    return out


def main():
    p = argparse.ArgumentParser(description="25 kurgu efekti")
    p.add_argument("args", nargs="*"); p.add_argument("--plan"); p.add_argument("--bas", type=float); p.add_argument("--bit", type=float)
    p.add_argument("--opt", action="append", default=[]); p.add_argument("--kare", help="kontrol kareleri: 4.5,9.2")
    p.add_argument("--hizli", action="store_true", help="U2Net maske (hızlı ama saç kenarı kaba)"); p.add_argument("--kaliteli", action="store_true", help=argparse.SUPPRESS); p.add_argument("--kartlar", help="Reels kapakları klasörü")
    p.add_argument("--liste", action="store_true")
    a = p.parse_args()
    if a.liste:
        for i, (k, v) in enumerate(EFEKTLER.items(), 1): print(f"{i:2}. {k:18} {v['aciklama']}")
        return
    if a.plan:
        plan = json.load(open(a.plan)); video, cikti = a.args[0], a.args[1]; liste = plan.get("efektler", plan.get("effects", []))
        a.kartlar = a.kartlar or plan.get("kartlar")
    else:
        ad, video, cikti = a.args
        e = {"fx": ad, "bas": a.bas, "bit": a.bit}
        for o in a.opt: k, v = o.split("=", 1); e[k] = v
        liste = [e]
    video, cikti = os.path.abspath(video), os.path.abspath(cikti)
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height:format=duration", "-of", "json", video], capture_output=True, text=True).stdout)
    n_, d_ = pr["streams"][0]["r_frame_rate"].split("/"); fps = round(int(n_) / int(d_)); dur = float(pr["format"]["duration"])
    for e in liste:
        e["fx"] = TAKMA.get(e.get("fx", e.get("efekt")), e.get("fx", e.get("efekt")))
        if e["fx"] not in EFEKTLER: sys.exit(f"Bilinmeyen efekt: {e['fx']}. Liste: --liste")
        e["bas"] = float(e.get("bas", e.get("start", 0)) or 0); e["bit"] = min(dur, float(e.get("bit", e.get("end", dur)) or dur))
    # çalışma klasörü (video başına önbellek)
    kimlik = hashlib.md5(f"{video}{os.path.getmtime(video)}".encode()).hexdigest()[:8]
    is_kl = os.path.join(os.path.dirname(cikti), f".kurgu-{os.path.splitext(os.path.basename(video))[0]}-{kimlik}")
    A = os.path.join(is_kl, "assets"); os.makedirs(os.path.join(A, "fonts"), exist_ok=True); os.makedirs(os.path.join(is_kl, "work"), exist_ok=True)
    for f in os.listdir(FONTLAR): shutil.copy(os.path.join(FONTLAR, f), os.path.join(A, "fonts", f))
    open(os.path.join(is_kl, "package.json"), "w").write('{"name":"kurgu","private":true}\n')
    if not os.path.exists(os.path.join(A, "klip.mov")):
        print("klip hazırlanıyor…", flush=True)
        sh("ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}," + DEC, "-c:v", "png", "-an", os.path.join(A, "klip.mov"))
    print("yüz takibi…", flush=True)
    yuz = yuz_izi(os.path.join(A, "klip.mov"), dur, fps, os.path.join(is_kl, "work", "yuz.json"))
    c = Baglam(fps, dur, yuz, kartlari_hazirla(is_kl, a.kartlar, dur))
    kam, ust = "", ""
    for i, e in enumerate(liste):
        P = f"f{i}"; d = EFEKTLER[e["fx"]]
        body = d["fn"](c, e, P)
        blok = f'<div id="{P}" class="fx" style="opacity:0">{body}</div>'
        c.S(f"#{P}", "{opacity:1}", e["bas"]); c.T(f"#{P}", "{opacity:1}", "{opacity:0}", e["bit"] - 0.15, 0.15, "none")
        if d["ust"]: ust += blok
        else: kam += blok
    css = "\n".join(c.CSS.values())
    html = f'''<!doctype html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>
@font-face{{font-family:"Playfair";src:url("assets/fonts/PlayfairDisplay-Italic-Variable.ttf");font-style:italic}}
@font-face{{font-family:"Bebas";src:url("assets/fonts/BebasNeue-Regular.ttf")}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;background:#000;overflow:hidden;font-family:-apple-system,"SF Pro Text","Helvetica Neue",sans-serif}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#000}}.fx{{position:absolute;inset:0}}
{css}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="{W}" data-height="{H}">
 <div class="clip" id="kam" data-start="0" data-duration="{dur:.3f}" data-track-index="2" style="position:absolute;inset:0;transform-origin:0 0">
  <video id="taban" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="1" data-media-start="0" src="assets/klip.mov" muted playsinline style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover"></video>
  {kam}
 </div>
 <div class="clip" id="ust" data-start="0" data-duration="{dur:.3f}" data-track-index="3" style="position:absolute;inset:0">{ust}</div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(c.J)}
tl.set({{}}, {{}}, {dur - 0.01:.3f});
window.__timelines["main"] = tl;
</script></body></html>'''
    if c.kesikler:
        kal = not a.hizli and model_var("birefnet-portrait.onnx")
        if not a.hizli and not kal: print("UYARI: BiRefNet yok, hızlı maskeye geçildi (saç kenarı kaba olabilir). Kurmak için: bash scripts/kurulum.sh", flush=True)
        print(f"kişi ayrılıyor ({'kaliteli' if kal else 'hızlı'})…", flush=True); kesikleri_yap(c, is_kl, kal, fps, [float(x) for x in a.kare.split(",")] if a.kare else None)
    open(os.path.join(is_kl, "index.html"), "w", encoding="utf8").write(html)
    if a.kare:
        r = subprocess.run(["npx", "--yes", "hyperframes@0.6.16", "snapshot", "--at", a.kare, "."], cwd=is_kl, capture_output=True, text=True)
        snaps = sorted(glob.glob(os.path.join(is_kl, "snapshots", "*.png")), key=os.path.getmtime)[-len(a.kare.split(",")):]
        if not snaps: sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
        snaps.sort(key=lambda f: float(f.rsplit("-at-", 1)[1][:-5]))
        ins = sum([["-i", f] for f in snaps], [])
        sh("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", f"hstack={len(snaps)}," + f"scale={min(len(snaps) * 540, 4000)}:-1" if len(snaps) > 1 else "scale=540:-1", "-q:v", "3", cikti)
        print("KARE", cikti); return
    png = os.path.join(is_kl, "renders", "png"); shutil.rmtree(png, ignore_errors=True)
    print("render…", flush=True)
    sh("npx", "--yes", "hyperframes@0.6.16", "render", "-w", "1", "--fps", str(fps), "--format", "png-sequence", "--output", "renders/png", ".", cwd=is_kl)
    ses = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    harita = ["-map", "0:v"] + (["-map", "1:a", "-c:a", "copy"] if ses else [])
    sh("ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(png, "frame_%06d.png"), "-i", video, *harita,
       "-vf", ENC, "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
       "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0", "-shortest", "-movflags", "+faststart", cikti)
    print("BITTI", cikti)


if __name__ == "__main__":
    main()
