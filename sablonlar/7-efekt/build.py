"""7 kurgu efekti: cam paneller, belgesel, yörünge, grafik, spot, liste, zaman çizelgesi.
python3 build.py → index.html + assets/sfx.wav. Önce scripts/teslim.py klip.mov ve kesik.mov hazırlar."""
import json, math, os, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw

# ================= AYARLAR (her video için değiştir) =================
AD = "Uğur Sarıçam"           # isim kartlarında görünen ad
KULLANICI = "@ugur.saricam"   # kullanıcı adı
TAKIPCI = "24,1B"             # profil kartındaki takipçi sayısı (gerçek sayı)
MK0 = 0.1                     # maskelemenin başladığı saniye (scripts/maskele.py --bas)
SES = os.environ.get("KURGU_SES", "sesler/")  # ses efekti klasörü (ad.wav); yoksa sessiz
# =====================================================================

KLIP = "assets/klip.mov"
B = 3.0                      # her yetenek bloğu
E0 = 7 * B                   # kapanış
DUR = round(E0 + 4.6, 2)

# ---------- kelimeler ----------
d = json.load(open("work/kelimeler.json")) if os.path.exists("work/kelimeler.json") else {"transcription": []}
W = []
for s in d["transcription"]:
    t = s["text"].strip()
    if not t: continue
    a, b = s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000
    if W and W[-1][2].lower() == "chat": W[-1] = (W[-1][0], b, "ChatGPT'ye"); continue
    W.append((a, b, t.rstrip(".")))

def fr(t):
    if t <= 0.001: return 0.0
    n = math.ceil(t * 50 - 1e-6)
    while math.floor(n * 0.6 + 1e-9) == math.floor((n - 1) * 0.6 + 1e-9): n += 1
    return math.floor(n * 0.6 + 1e-9) / 30 - 0.0005

J = []
def S(sel, props, t): J.append(f'  tl.set("{sel}", {props}, {fr(t):.4f});')
def T(sel, a, b, t, dur, ease="power2.out"):
    J.append(f'  tl.fromTo("{sel}", {a}, {{...{b}, duration:{dur}, ease:"{ease}"}}, {fr(t):.4f});')
SFX = []
def sx(name, t, g=0.5): SFX.append((name, t, g))

# ---------- yetenekler ----------
SK = [
    ("efekt cam-paneller", "Etrafında buzlu cam paneller", 1.2, "/ef"),
    ("efekt belgesel", "Siyah-beyaz, arkanda ışık, isim bandı", 1.2, "/ef"),
    ("efekt yörünge", "Videoların başının etrafında döner", 1.2, "/ef"),
    ("efekt grafik", "Üstte grafik, altta sen", 1.2, "/ef"),
    ("efekt spot", "Karanlık sahne, arkanda neon yazı", 1.2, "/ef"),
    ("efekt liste", "Claude adım adım düzenler", 1.0, "/ef"),
    ("efekt zaman-çizelgesi", "Üstte kurgu ekranı, altta sen", 1.6, "/ef"),
]
NE = len(SK)
POST = {0: "p_2.4", 1: "p_1.8", 2: "p_1.8", 3: "p_1.8", 4: "p_1.8", 5: "p_1.8", 6: "p_2.4"}

# ---------- nokta görselleri ----------
DW, DH, CS = 690, 1227, 17
def nokta_rastgele(seed, path):
    r = random.Random(seed); im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    for y in range(CS // 2, DH, CS):
        for x in range(CS // 2, DW, CS):
            v = r.random()
            if v < 0.55: continue
            rr = 2 + 4.5 * r.random(); a = int(90 + 165 * r.random())
            g.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(214, 120, 88, a))
    im.save(path)
def nokta_portre(src, path):
    p = Image.open(src).convert("L").resize((1080, 1920)).resize((DW, DH))
    a = np.asarray(p).astype(np.float32) / 255
    im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    for y in range(CS // 2, DH, CS):
        for x in range(CS // 2, DW, CS):
            v = a[y - 4:y + 4, x - 4:x + 4].mean()
            rr = 1.2 + 6.8 * v ** 1.2
            g.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(226, 132, 96, int(110 + 145 * v)))
    im.save(path)
nokta_rastgele(1, "assets/dotA.png"); nokta_rastgele(2, "assets/dotB.png")
for k, p in POST.items(): nokta_portre(f"assets/{p}.jpg", f"assets/dotP{k}.png")

# ---------- yardımcı html ----------
def spark(sz, col="#D97757"):
    rays = []
    for i in range(12):
        ang = i * 30 + 8; L = 0.48 if i % 2 else 0.36
        x2 = 50 + L * 100 * math.cos(math.radians(ang)); y2 = 50 + L * 100 * math.sin(math.radians(ang))
        rays.append(f'<line x1="50" y1="50" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    return (f'<svg width="{sz}" height="{sz}" viewBox="0 0 100 100"><g stroke="{col}" stroke-width="11" stroke-linecap="round">'
            + "".join(rays) + "</g></svg>")

VID = []   # (id, start, mediastart, dur)
def media(mode, vid, k, start=None, m=None, style=""):
    """mode v: video; i: poster görseli (kapanış ızgarası)."""
    if mode == "i":
        return f'<img src="assets/{POST[k]}.jpg" style="position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;{style}">'
    VID.append((vid, start, m))
    return f'<video id="{vid}" class="clip" data-start="{start:.4f}" data-duration="{B - 0.8 + 0.1:.3f}" data-track-index="{60 + len(VID)}" data-media-start="{m:.3f}" src="{KLIP}" muted playsinline style="position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;{style}"></video>'

def kelimeler(m, L=1.8):
    out = []
    for a, b, w in W:
        if b <= m + 0.08 or a >= m + L: continue
        out.append((max(a, m), b, w))
    ch = [out[i:i + 2] for i in range(0, len(out), 2)]
    return [(c[0][0], " ".join(x[2] for x in c)) for c in ch]

def caps(pref, k, m, B0, cls, mode, style_fn=None):
    return ''
    ch = kelimeler(m)
    if mode == "i": ch = ch[:1]
    h = ""
    for i, (a, txt) in enumerate(ch):
        cid = f"{pref}c{k}_{i}"
        inner = style_fn(txt) if style_fn else txt
        disp = "block" if mode == "i" else "none"
        h += f'<div id="{cid}" class="{cls}" style="display:{disp}">{inner}</div>'
        if mode == "v":
            t0 = B0 + 1.5 + (a - m); t1 = B0 + B if i == len(ch) - 1 else B0 + 1.5 + (ch[i + 1][0] - m)
            S(f"#{cid}", '{display:"block"}', max(t0, B0 + 1.5)); S(f"#{cid}", '{display:"none"}', t1)
    return h

def gradyan_kelime(txt):  # anlatıcı: son kelime italik serif
    p = txt.split(" ")
    return " ".join(p[:-1]) + (" " if len(p) > 1 else "") + f'<i>{p[-1]}</i>'
def gri_ikinci(txt):
    p = txt.upper().split(" ")
    return p[0] + ("" if len(p) == 1 else f' <span style="color:#9a9a9a">{" ".join(p[1:])}</span>')

# ---------- sahneler (pref "" canlı, "g_" ızgara kopyası) ----------
ORB = ["insan", "claude", "gizli", "fincan", "komut", "sonuc", "diyet", "kopya"]
def orb_pos(i, tt):
    th = math.radians(i * 45 + 150 * tt)
    c, sn = math.cos(th), math.sin(th)
    x = 565 + 500 * c; y = 1040 + 250 * sn - 90 * c
    sc = 0.82 + 0.26 * sn
    return x - 85, y - 151, sc, sn > 0, -c * 38
def orb_tf(x, y, sc, ry):
    return f"transform:perspective(1200px) translate({x:.0f}px,{y:.0f}px) rotateY({ry:.1f}deg) scale({sc:.3f})"

def kesik(pref, mode, B0, m, filt=""):
    if mode == "v":
        VID.append((f"{pref}cut", 0, 0)); kk = int(round(B0 / B))
        return f'<video id="{pref}cut{kk}" class="clip" data-start="{B0 + 0.8:.4f}" data-duration="{B - 0.8 + 0.1:.3f}" data-track-index="{60 + len(VID)}" data-media-start="{max(m - 0.7 - MK0, 0):.3f}" src="assets/kesik.mov" muted playsinline style="position:absolute;left:0;top:0;width:1080px;height:1920px;{filt}"></video>'
    return f'<img src="assets/kesik_poster.png" style="position:absolute;left:0;top:0;width:1080px;height:1920px;{filt}">'

def sahne(k, pref, mode):
    B0 = k * B; m = SK[k][2]; vid = f"{pref}v{k}"; P = pref
    if k == 0:   # cam paneller
        h = media(mode, vid, k, B0 + 0.8, m - 0.7)
        D = [651, 624, 158, 71.7, 43.1, 16.9, 10.9]
        ch = "".join(f'<i style="height:{max(5, v / 651 * 100):.0f}px;background:{"#F2B33D" if j == 0 else "#D9583D"}"></i>' for j, v in enumerate(D))
        h += f'''<div id="{P}g0" class="gls" style="zoom:1.2;left:25px;top:67px;width:310px;height:290px;padding:24px 28px;">
             <div class="gs"><b class="gdot"></b>Claude</div><div class="gbig">7</div><div class="gs2">efekt<br>tek klip</div></div>
          <div id="{P}g1" class="gls" style="zoom:1.2;left:25px;top:378px;width:310px;height:330px;padding:18px;">
             <div class="gmono">artifact · izlenme.html</div>
             <div class="gwin"><div class="gwd"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b></div>
               <div class="gwt">En çok izlenen</div><div class="gwv">651B</div><div class="gch">{ch}</div></div></div>
          <div id="{P}g2" class="gls" style="zoom:1.2;left:25px;top:728px;width:310px;height:180px;padding:20px 26px;">
             <div class="glab" style="color:#fff;opacity:.85">KAYDETME</div><div class="gmid">108B</div><div class="gred">ChatGPT kodları</div></div>
          <div id="{P}g3" class="gls" style="zoom:1.2;left:545px;top:67px;width:330px;height:170px;padding:22px 26px;">
             <div class="gs"><b class="gdot" style="background:#ff4b3e"></b>Render ediliyor</div><div class="gbar"><div id="{P}gb" class="gbf"></div></div><div class="gs2">1080p render · %71</div></div>
          <div id="{P}g4" class="gls" style="zoom:1.2;left:545px;top:258px;width:330px;height:150px;padding:22px 26px;display:flex;align-items:center;">
             <div style="flex:1"><div class="gname">{AD}</div><div class="gs2">{KULLANICI}</div></div><img src="assets/ig_avatar.png" class="gav"></div>
          <div id="{P}g5" class="gls" style="zoom:1.2;left:545px;top:428px;width:330px;height:290px;padding:22px 22px;">
             <div style="display:flex;gap:16px;align-items:center"><div class="gico">{spark(54, "#fff")}</div><div><div class="glab" style="color:rgba(255,255,255,.8);font-size:16px;letter-spacing:1.5px">ŞİMDİ DÜZENLENİYOR</div><div class="gname" style="font-size:30px">UI pop sesleri</div><div class="gs2">sfx · 25,6 sn</div></div></div>
             <div class="gpb"><div id="{P}gpf"></div></div><div class="gctl"><span>⏮</span><span style="font-size:52px">▶</span><span>⏭</span></div></div>
          <div id="{P}g6" class="gls" style="zoom:1.2;left:605px;top:739px;width:270px;height:270px;border-radius:50%;display:flex;align-items:center;justify-content:center;">
             <div class="gring"><div>50<br><span>fps</span></div></div></div>
'''
        h += kesik(P, mode, B0, m)
        h += f'<div id="{P}g7" class="gls gpill">Claude ile <b style="color:#FFB08A;margin-left:12px">düzenlendi</b></div>'
        if mode == "v":
            for j in range(8): T(f"#{P}g{j}", "{opacity:0,scale:0.85}", "{opacity:1,scale:1}", B0 + 1.5 + j * 0.07, 0.35, "back.out(1.6)"); sx("pop", B0 + 1.52 + j * 0.07, 0.14)
            T(f"#{P}gb", "{width:'20%'}", "{width:'71%'}", B0 + 1.6, 1.2, "power1.inOut")
            T(f"#{P}gpf", "{width:'10%'}", "{width:'60%'}", B0 + 1.6, 1.4, "none")
    elif k == 1:  # belgesel
        g = "filter:grayscale(1) contrast(1.12) brightness(.9);"
        tr = "transform:translate(-300px,210px) scale(1.15);transform-origin:540px 960px;"
        h = media(mode, vid, k, B0 + 0.8, m - 0.7, g + tr)
        on = "1" if mode == "i" else "0"
        h += f'''<div id="{P}bbg" class="bbg" style="opacity:{on}"></div>
          <div class="bdisk"></div>
          <div class="btop">YAPAY ZEKA OKURYAZARLIĞI</div>
          <div class="btl"><div id="{P}bl1">TEK <em>KLİP.</em></div><div id="{P}bl2">7 <em>EFEKT.</em></div><div id="{P}bl3">0 <em>UYGULAMA.</em></div></div>'''
        h += kesik(P, mode, B0, m, g + tr)
        h += f'''<div class="blt"><div class="bln">{AD.upper()}</div><div class="blh">{KULLANICI}</div></div>
          <div id="{P}bfo" class="bfol"{' style="background:#fff;color:#111"' if mode == "i" else ''}>{'Takiptesin' if mode == "i" else '<span id="' + P + 'bf1">Takip et</span><span id="' + P + 'bf2" style="display:none">Takiptesin</span>'}</div>'''
        if mode == "v":
            h += f'<div id="{P}bcur" class="bcur"><svg width="64" height="80" viewBox="0 0 16 20"><path d="M1 1 L1 16 L5 12.5 L8 19 L10.5 18 L7.6 11.6 L13 11.6 Z" fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg></div>'
            T(f"#{P}bbg", "{opacity:0}", "{opacity:1}", B0 + 1.15, 0.25, "none")
            for j, t in enumerate((1.95, 2.12, 2.29)):
                T(f"#{P}bl{j + 1}", "{opacity:0,x:60}", "{opacity:1,x:0}", B0 + t, 0.18, "power3.out"); sx("impact2" if j == 2 else "impact1", B0 + t, 0.22)
            T(f"#{P}bcur", "{x:260,y:300,opacity:0}", "{x:0,y:0,opacity:1}", B0 + 2.3, 0.3, "power3.out")
            S(f"#{P}bf1", '{display:"none"}', B0 + 2.65); S(f"#{P}bf2", '{display:"inline"}', B0 + 2.65)
            S(f"#{P}bfo", '{backgroundColor:"#F06A1F",color:"#fff"}', B0); S(f"#{P}bfo", '{backgroundColor:"#fff",color:"#111",scale:0.94}', B0 + 2.62); T(f"#{P}bfo", "{scale:0.94}", "{scale:1}", B0 + 2.66, 0.15)
            sx("deklansor1", B0 + 1.85, 0.3); sx("tik2", B0 + 2.62, 0.5)
    elif k == 2:  # yörünge
        h = media(mode, vid, k, B0 + 0.8, m - 0.7)
        h += '<div class="odark"></div>'
        back = front = ""
        t0 = 0.55 if mode == "i" else 0.0
        for i, n in enumerate(ORB):
            x, y, sc, fr_, ry = orb_pos(i, t0)
            for lay in ("b", "f"):
                vis = (fr_ if lay == "f" else not fr_)
                st = orb_tf(x, y, sc, ry) + ";" if mode == "i" else ""
                el = f'<img id="{P}o{i}{lay}" class="orb" src="assets/r_{n}.jpg" style="{st}opacity:{1 if (vis and mode == "i") else 0}">'
                if lay == "b": back += el
                else: front += el
        h += back + kesik(P, mode, B0, m) + front
        if mode == "v":
            sx("whoosh_uzun", B0 + 1.5, 0.35)
            for i in range(len(ORB)):
                st = None
                for j in range(17):
                    tt = j * 0.1; t = B0 + 1.45 + tt
                    x, y, sc, f_, ry = orb_pos(i, tt)
                    for lay in ("b", "f"):
                        v = f"x:{x:.1f},y:{y:.1f},scale:{sc:.3f},rotationY:{ry:.1f}"
                        if j == 0: S(f"#{P}o{i}{lay}", f"{{{v},transformPerspective:1200}}", t)
                        else: J.append(f'  tl.to("#{P}o{i}{lay}", {{{v},duration:0.1,ease:"none"}}, {fr(t - 0.1):.4f});')
                    if f_ != st:
                        S(f"#{P}o{i}f", f"{{opacity:{1 if f_ else 0}}}", t); S(f"#{P}o{i}b", f"{{opacity:{0 if f_ else 1}}}", t); st = f_
    elif k == 3:  # grafik
        D = [(651, "651B", "Sonuç 37"), (624, "624B", "Fincan"), (158, "158B", "İnsan gibi"), (71.7, "71,7B", "Gizli kod"), (43.1, "43,1B", "Diyet"), (16.9, "16,9B", "Claude"), (10.9, "10,9B", "5 komut")]
        Y0, H = 820, 470  # taban ve 700B yüksekliği
        bars = ""
        for j, (v, lab, nm) in enumerate(D):
            hh = max(6, v / 700 * H); x = 175 + j * 124
            col = "#F2C063" if j == 0 else "#D9583D"
            bars += f'<div id="{P}br{j}" class="bar" style="left:{x}px;top:{Y0 - hh:.0f}px;height:{hh:.0f}px;background:{col}"><b>{lab}</b></div><div class="bn" style="left:{x - 12}px;top:{Y0 + 14}px">{nm}</div>'
        grid = "".join(f'<div class="gy" style="top:{Y0 - v / 700 * H:.0f}px"><span>{v}B</span></div>' for v in (0, 200, 400, 600))
        av = sum(d[0] for d in D) / 7
        h = f'''<div class="gpap" style="position:absolute;inset:0">
          <div class="gtl">En çok izlenen<br><span>7 <em>Reels'im</em></span></div>
          {grid}<div class="gavg" style="top:{Y0 - av / 700 * H:.0f}px"><span>ort. 225B</span></div>{bars}
          <div class="gwn">{media(mode, vid, k, B0 + 0.8, m - 0.7, "top:-590px;left:-65px;")}</div>{kesik(P, mode, B0, m, "left:-29px;top:375px;clip-path:inset(0 7px 0 65px);")}</div>'''
        if mode == "v":
            for j in range(7): T(f"#{P}br{j}", "{scaleY:0}", "{scaleY:1}", B0 + 1.6 + j * 0.08, 0.45, "power3.out"); sx("tik1", B0 + 1.6 + j * 0.08, 0.15)
    elif k == 4:  # spot
        h = media(mode, vid, k, B0 + 0.8, m - 0.7, "filter:brightness(.8);")
        h += '<div class="sdark"></div>'
        h += f'<div id="{P}neon" class="neon">Claude</div>'
        h += kesik(P, mode, B0, m, "filter:brightness(.8);")
        h += '<div class="sdark2"></div>'
        if mode == "v":
            S(f"#{P}neon", "{opacity:0}", B0)
            for t, o in ((1.6, 1), (1.68, 0.2), (1.76, 1), (1.84, 0.4), (1.9, 1)): S(f"#{P}neon", f"{{opacity:{o}}}", B0 + t)
            sx("tik3", B0 + 1.6, 0.3)
    elif k == 5:  # liste
        h = media(mode, vid, k, B0 + 0.8, m - 0.7)
        h += '<div class="ldark"></div>'
        IT = [("Yüzün bulundu", "her karede"), ("Arka plandan ayrıldın", "maske"), ("Yazı arkana yerleşti", "derinlik"), ("Renkler korundu", "renk"), ("Render edildi", "50 fps")]
        rows = ""
        for j, (a, b) in enumerate(IT):
            on = mode == "i"
            rows += f'<div class="lr"><span id="{P}lc{j}" class="lck{" on" if on else ""}">✓</span><span id="{P}lt{j}" class="ltx{" on" if on else ""}">{a}</span><span class="ltg">{b}</span></div>'
        cnt = "".join(f'<span id="{P}ln{j}" style="display:{"inline" if (mode=="i" and j==5) or (mode=="v" and j==0) else "none"}">{j}/5</span>' for j in range(6))
        h += f'<div class="lcard"><div class="lh">{spark(36)} <b>Claude klibini düzenliyor</b><span class="lcn">{cnt}</span></div>{rows}</div>'
        if mode == "v":
            for j in range(5):
                t = B0 + 1.7 + j * 0.25
                S(f"#{P}lc{j}", '{attr:{class:"lck on"}}', t); S(f"#{P}lt{j}", '{attr:{class:"ltx on"}}', t)
                S(f"#{P}ln{j}", '{display:"none"}', t); S(f"#{P}ln{j + 1}", '{display:"inline"}', t)
                sx("tik2", t, 0.3)
    else:  # zaman çizelgesi
        h = f'<div class="cream" style="position:absolute;inset:0"></div>'
        rows = [("kesim", "duraklar silindi ✓"), ("renk", "doğal ton ✓"), ("efektler", "7 efekt ✓"), ("ses", "seviye ayarlandı ✓")]
        rr = "".join(f'<div class="zr"><span>{a}</span><b>{b}</b></div>' for a, b in rows)
        wav = "".join(f'<i style="height:{8 + 38 * abs(math.sin(j * 0.7) * math.cos(j * 0.23)):.0f}px"></i>' for j in range(70))
        pc = "".join(f'<span id="{P}zp{j}" style="display:{"inline" if (mode=="i" and j==3) or (mode=="v" and j==0) else "none"}">%{v}</span>' for j, v in enumerate([12, 31, 48, 65]))
        h += f'''<div class="ztl">Claude <em>render ediyor</em></div>
          <div class="zed"><div class="zbar"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b><span>KURGU · RENDER</span><span style="margin-left:auto">1080p · 50 fps</span></div>
            {rr}<div class="ztr"><img src="assets/strip.jpg"></div><div class="zwv">{wav}</div>
            <div id="{P}zph" class="zph"></div><div class="zpr"><div id="{P}zpf" class="zpf"></div></div><div class="zpc">{pc}</div></div>
          <div class="zvc">{media(mode, vid, k, B0 + 0.8, m - 0.7, "top:-430px;left:-85px;")}</div>'''
        if mode == "v":
            T(f"#{P}zph", "{x:0}", "{x:780}", B0 + 1.5, 1.5, "none")
            T(f"#{P}zpf", "{width:'12%'}", "{width:'65%'}", B0 + 1.6, 1.2, "power1.inOut")
            for j in range(1, 4): S(f"#{P}zp{j - 1}", '{display:"none"}', B0 + 1.6 + j * 0.4); S(f"#{P}zp{j}", '{display:"inline"}', B0 + 1.6 + j * 0.4)
    return h


def fl(sel, t, amp=14, d=0.9):
    J.append(f'  tl.fromTo("{sel}", {{y:0}}, {{y:{-amp}, duration:{d}, ease:"sine.inOut", yoyo:true, repeat:1}}, {fr(t):.4f});')
def hareket(k, rid, B0):
    T(f"#z{k}", "{scale:1}", "{scale:1.06}", B0 + 1.5, B - 1.5, "none")
    if k == 0:
        for j in range(7): fl(f"#{rid} #g{j}", B0 + 1.95 + j * 0.06, 9 + (j % 3) * 4, 0.5)
    elif k == 1:
        T(f"#{rid} .bdisk", "{scale:0.6,opacity:0}", "{scale:1,opacity:1}", B0 + 1.2, 0.6, "power3.out"); fl(f"#{rid} .bdisk", B0 + 1.9, 12, 0.55)
        T(f"#{rid} .blt", "{x:-500}", "{x:0}", B0 + 1.9, 0.4, "power3.out"); T(f"#{rid} .btop", "{opacity:0,y:-20}", "{opacity:1,y:0}", B0 + 1.9, 0.3)
    elif k == 3:
        T(f"#{rid} .gwn", "{y:300}", "{y:0}", B0 + 1.85, 0.45, "power3.out")
        T(f"#cut{k}", "{y:300}", "{y:0}", B0 + 1.85, 0.45, "power3.out")
        T(f"#{rid} .gavg", "{scaleX:0,transformOrigin:'0% 50%'}", "{scaleX:1}", B0 + 2.3, 0.4, "power2.out")
        T(f"#{rid} .gtl", "{y:-30,opacity:0}", "{y:0,opacity:1}", B0 + 1.9, 0.35, "power3.out")
    elif k == 4:
        T(f"#{rid} .neon", "{scale:0.85}", "{scale:1.04}", B0 + 1.6, 1.4, "power1.out")
    elif k == 5:
        T(f"#{rid} .lcard", "{y:400,opacity:0}", "{y:0,opacity:1}", B0 + 1.6, 0.45, "back.out(1.3)"); sx("whoosh_kisa2", B0 + 1.6, 0.25)
    elif k == 6:
        T(f"#{rid} .zed", "{y:-60,opacity:0}", "{y:0,opacity:1}", B0 + 1.9, 0.4, "power3.out"); T(f"#{rid} .zvc", "{y:120}", "{y:0}", B0 + 1.9, 0.45, "power3.out")
        sx("klavye", B0 + 2.0, 0.2)

# ---------- arayüz ----------
R1, R2, R3 = "qwertyuıopğü", "asdfghjklşi", "zxcvbnmöç"
KEY = {}
def klavye():
    h = '<div id="kb" class="kb"><div class="kbs"><i style="left:360px"></i><i style="left:720px"></i></div>'
    for row, y, x0 in ((R1, 1405, 4), (R2, 1545, 49), (R3, 1685, 139)):
        for i, c in enumerate(row):
            x = x0 + i * 90; KEY[c] = (x + 41, y)
            h += f'<div class="key" style="left:{x}px;top:{y - 1290}px">{c}</div>'
    h += '<div class="key kf" style="left:4px;top:395px;width:118px">⇧</div><div class="key kf" style="left:958px;top:395px;width:118px">⌫</div>'
    h += '<div class="key kf" style="left:4px;top:535px;width:200px">123</div><div class="key" style="left:214px;top:535px;width:652px;font-size:34px">boşluk</div><div class="key kf" style="left:876px;top:535px;width:200px;font-size:34px">git</div>'
    return h + "</div>"

def pop(c, t, pid):
    if c not in KEY: return ""
    x, y = KEY[c]
    S(f"#{pid}", '{display:"block"}', t); S(f"#{pid}", '{display:"none"}', t + 0.12)
    return f'<div id="{pid}" class="kpop" style="left:{x - 58}px;top:{y - 112}px">{c}</div>'

ui_extra = ""
def blok_arayuz(k, B0, cmd, desc, part, son=False):
    """Ev ekranı → yazma → gönderme. son=True: kapanış (cmd düz metin)."""
    global ui_extra
    full = cmd if son else "/" + cmd
    chars = part
    pid = f"in{k}"
    spans = "".join(f'<span id="{pid}_{i}" style="display:none">{c}</span>' for i, c in enumerate(chars))
    ui_extra += f'<div id="{pid}" class="intx" style="display:none">{spans}<span id="{pid}_f" style="display:none">{chars}{full[len(chars):]}</span><b class="cur2"></b></div>'
    if not son:
        ui_extra += f'<div id="dd{k}" class="dd" style="display:none"><div class="ddc">/{cmd}</div><div class="ddd">{desc}</div></div>'
    ui_extra += f'<div id="ch{k}" class="chip" style="display:none">{full}</div>'
    ui_extra += f'<div id="ed{k}" class="edl" style="display:none">{spark(34)} <span>Claude ile düzenleniyor: {full}…</span></div>'
    # ev durumu
    S("#home", "{opacity:1}", B0); S("#ibox", "{opacity:1}", B0); S("#kb", "{y:0}", B0)
    S("#rbar", "{opacity:0}", B0); S("#tth", "{opacity:0}", B0)
    S(f"#{pid}", '{display:"block"}', B0)
    for i, c in enumerate(chars):
        t = B0 + 0.04 + i * (0.07 if son else 0.13)
        S(f"#{pid}_{i}", '{display:"inline"}', t)
        ui_extra += pop(c, t, f"kp{k}_{i}")
        sx("tik2", t, 0.22)
        if i == 0 and not son: S(f"#dd{k}", '{display:"block"}', t)
    ta = B0 + 0.04 + len(chars) * (0.07 if son else 0.13) + 0.05
    if son:
        for i in range(len(chars), len(full)):
            pass
    for i in range(len(chars)): S(f"#{pid}_{i}", '{display:"none"}', ta)
    S(f"#{pid}_f", '{display:"inline"}', ta)
    if not son: S(f"#dd{k}", '{display:"none"}', ta + 0.1)
    tg = ta + 0.2
    T("#send", "{scale:1}", "{scale:0.88,yoyo:true,repeat:1}", tg, 0.07, "none"); sx("pop", tg, 0.35)
    # gönderildi
    S(f"#{pid}", '{display:"none"}', tg + 0.12)
    T("#home", "{opacity:1}", "{opacity:0}", tg + 0.05, 0.2)
    T("#ibox", "{opacity:1}", "{opacity:0}", tg + 0.05, 0.15)
    T("#kb", "{y:0}", "{y:700}", tg + 0.05, 0.3, "power2.in")
    T("#rbar", "{opacity:0}", "{opacity:1}", tg + 0.25, 0.2)
    T("#tth", "{opacity:0,y:30}", "{opacity:1,y:0}", tg + 0.08, 0.25)
    S(f"#ch{k}", '{display:"block"}', tg + 0.08); S(f"#ch{k}", '{display:"none"}', B0 + B if not son else DUR)
    S(f"#ed{k}", '{display:"flex"}', tg + 0.2); S(f"#ed{k}", '{display:"none"}', B0 + B if not son else tg + 0.35)
    return tg

scenes = ""
for k, (cmd, desc, m, part) in enumerate(SK):
    B0 = k * B
    tg = blok_arayuz(k, B0, cmd, desc, part)
    S("#dp", "{opacity:1}", B0 + 0.85); S("#dP", f'{{opacity:0,attr:{{src:"assets/dotP{k}.png"}}}}', B0)
    for j in range(9):
        t = B0 + 0.85 + j * 0.08
        S("#dA", f"{{opacity:{1 if j % 2 == 0 else 0}}}", t); S("#dB", f"{{opacity:{0 if j % 2 == 0 else 1}}}", t)
    T("#dP", "{opacity:0}", "{opacity:1}", B0 + 1.1, 0.35, "none")
    T("#dA", "{opacity:1}", "{opacity:0}", B0 + 1.25, 0.2, "none"); S("#dB", "{opacity:0}", B0 + 1.25)
    S("#dp", "{opacity:0}", B0 + 1.62)
    rid = f"r{k}"
    scenes += f'<div id="{rid}" class="res" style="opacity:0"><div id="z{k}" class="zin">{sahne(k, "", "v")}</div></div>'
    hareket(k, rid, B0)
    S(f"#{rid}", "{opacity:1,x:43,y:455,scale:0.639,borderRadius:34}", B0 + 1.5)
    J.append(f'  tl.to("#{rid}", {{x:0,y:0,scale:1,borderRadius:0,duration:0.32,ease:"power3.inOut"}}, {fr(B0 + 1.85):.4f});')
    S(f"#{rid}", "{opacity:0}", B0 + B)
    sx("whoosh_kisa1", B0 + 1.8, 0.4)

# ---------- kapanış ----------
tg = blok_arayuz(NE, E0, "animasyon", "", "animasyon", son=True)
S("#rsp", '{display:"flex"}', tg + 0.35); T("#rsp", "{opacity:0}", "{opacity:1}", tg + 0.35, 0.2)
grid = ""
CWD, CHT = 230, 409
for k in range(NE + 1):
    col, row = k % 4, k // 4
    x, y = 40 + col * 255, 360 + row * 500
    if k < NE:
        inner = sahne(k, f"g{k}_", "i")
        grid += f'<div class="gc" style="left:{x}px;top:{y}px;width:{CWD}px;height:{CHT}px;background:#000"><div style="position:absolute;left:0;top:0;width:1080px;height:1920px;transform:scale({CWD/1080:.5f});transform-origin:0 0;">{inner}</div></div><div class="gl" style="left:{x}px;top:{y + CHT + 10}px;width:{CWD}px;font-size:22px">/{SK[k][0].split(" ")[1]}</div>'
    else:
        grid += f'<div class="gc" style="left:{x}px;top:{y}px;width:{CWD}px;height:{CHT}px;background:#D97757;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;text-align:center;gap:14px">{spark(90,"#fff")}<div style="font:400 54px Bebas;line-height:1">“ANİMASYON”<br>YAZ</div></div>'
tE = tg + 0.55
S("#end", "{opacity:1,x:43,y:455,scale:0.639,borderRadius:34}", tE); sx("pop", tE, 0.3)
J.append(f'  tl.to("#end", {{x:0,y:0,scale:1,borderRadius:0,duration:0.35,ease:"power3.inOut"}}, {fr(tE + 0.3):.4f});'); sx("whoosh_kisa2", tE + 0.28, 0.4)
S("#eh1", "{opacity:0}", tE + 1.45); T("#eh2", "{opacity:0,y:30}", "{opacity:1,y:0}", tE + 1.45, 0.3, "back.out(1.7)"); sx("tik3", tE + 1.45, 0.4)

# ---------- css + html ----------
CSS = '''
@font-face{font-family:"Playfair";src:url("assets/fonts/PlayfairDisplay-Italic-Variable.ttf");font-style:italic;}
@font-face{font-family:"Bebas";src:url("assets/fonts/BebasNeue-Regular.ttf");}
*{margin:0;padding:0;box-sizing:border-box;}
body{width:1080px;height:1920px;background:#222120;overflow:hidden;font-family:-apple-system,"SF Pro Text","Helvetica Neue",sans-serif;}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;background:#222120;}
.hdr{position:absolute;left:0;right:0;top:0;height:180px;z-index:2;}
.ic{position:absolute;top:42px;width:88px;height:88px;border-radius:50%;background:#2f2e2c;color:#c8c6c0;font-size:40px;display:flex;align-items:center;justify-content:center;}
.tog{position:absolute;left:370px;top:42px;width:340px;height:88px;border-radius:44px;background:#2f2e2c;display:flex;align-items:center;justify-content:space-around;font-size:36px;color:#9a9893;padding:0 8px;}
.tog b{font-weight:500;background:#45443f;color:#fff;border-radius:36px;padding:12px 34px;}
#home{position:absolute;inset:0;}
.grt{position:absolute;left:0;right:0;top:420px;text-align:center;font-size:62px;color:#ece9e2;font-weight:400;}
.sp{position:absolute;left:495px;top:285px;}
#ibox{position:absolute;left:22px;right:22px;top:820px;height:455px;border-radius:40px;background:#302f2d;border:2px solid #3b3a37;}
.th0{position:absolute;left:36px;top:30px;width:200px;height:230px;border-radius:20px;overflow:hidden;}
.th0 img{width:100%;height:100%;object-fit:cover;} .th0 i{position:absolute;right:8px;top:8px;width:36px;height:36px;border-radius:50%;background:#111;color:#fff;font:600 24px sans-serif;text-align:center;line-height:36px;font-style:normal;}
.ibi{position:absolute;bottom:32px;color:#c8c6c0;font-size:46px;}
#send{position:absolute;right:30px;bottom:30px;width:88px;height:88px;border-radius:24px;background:#D97757;color:#fff;font-size:50px;display:flex;align-items:center;justify-content:center;}
.intx{position:absolute;left:60px;top:1110px;font-size:48px;color:#ece9e2;z-index:3;white-space:nowrap;}
.cur2{display:inline-block;width:3px;height:52px;background:#D97757;vertical-align:-10px;margin-left:2px;}
.dd{position:absolute;left:32px;right:32px;top:675px;height:128px;border-radius:24px;background:#2b2a28;border:2px solid #383734;padding:20px 30px;z-index:3;}
.ddc{font-size:40px;color:#ece9e2;} .ddd{font-size:27px;color:#8f8d88;margin-top:6px;}
.kb{position:absolute;left:0;right:0;top:1290px;height:630px;background:#1e1e1d;z-index:2;}
.kbs{position:absolute;left:0;right:0;top:0;height:100px;} .kbs i{position:absolute;top:30px;width:2px;height:40px;background:#3a3a38;}
.key{position:absolute;width:82px;height:122px;border-radius:14px;background:#3d3d3b;color:#fff;font-size:50px;display:flex;align-items:center;justify-content:center;}
.kf{background:#2c2c2b;font-size:40px;}
.kpop{position:absolute;display:none;width:116px;height:220px;border-radius:22px;background:#5c5c5a;color:#fff;font-size:72px;text-align:center;padding-top:20px;z-index:4;}
#rbar{position:absolute;left:22px;right:22px;top:1760px;height:116px;border-radius:40px;background:#302f2d;border:2px solid #3b3a37;color:#8f8d88;font-size:38px;display:flex;align-items:center;padding:0 30px;gap:26px;z-index:2;}
#rbar .up{margin-left:auto;width:76px;height:76px;border-radius:20px;background:#45443f;color:#ddd;display:flex;align-items:center;justify-content:center;}
#tth{position:absolute;right:122px;top:20px;width:200px;height:230px;border-radius:22px;overflow:hidden;z-index:3;} #tth img{width:100%;height:100%;object-fit:cover;}
.chip{position:absolute;right:36px;top:268px;background:#4a2e24;color:#ec9a78;font-size:42px;padding:14px 30px;border-radius:40px;z-index:3;}
.edl{position:absolute;left:40px;top:372px;align-items:center;gap:14px;font-size:30px;color:#8f8d88;z-index:3;}
#dp{position:absolute;left:43px;top:455px;width:690px;height:1227px;border-radius:22px;overflow:hidden;background:#1b1a19;z-index:5;opacity:0;}
#dp img{position:absolute;left:0;top:0;}
.zin{position:absolute;inset:0;transform-origin:50% 45%;}
.res{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:hidden;transform-origin:0 0;z-index:8;background:#000;}
.res3{position:absolute;inset:0;z-index:8;}
#rsp{position:absolute;left:40px;top:372px;display:none;align-items:center;gap:16px;font-size:34px;color:#ece9e2;z-index:3;}
#end{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:hidden;transform-origin:0 0;z-index:9;background:#1e1d1c;opacity:0;}
.eh{position:absolute;left:0;right:0;top:110px;text-align:center;color:#fff;font-weight:800;font-size:92px;letter-spacing:-1px;}
.eh small{display:block;font-size:40px;font-weight:600;color:#E0805C;margin-top:10px;letter-spacing:0;}
.eh .pl{display:inline-block;margin-top:16px;font-size:42px;font-weight:700;background:#D97757;color:#fff;border-radius:14px;padding:8px 26px;letter-spacing:0;}
.gc{position:absolute;width:300px;height:533px;border-radius:20px;overflow:hidden;}
.gl{position:absolute;width:300px;text-align:center;font-size:26px;color:#9a9893;}
.cream{background:#f4f0e8;background-image:radial-gradient(#d9d2c4 2px,transparent 2.5px);background-size:34px 34px;}
.gls{position:absolute;border-radius:34px;background:rgba(255,248,240,.2);backdrop-filter:blur(24px) saturate(1.2);-webkit-backdrop-filter:blur(24px) saturate(1.2);border:1.5px solid rgba(255,255,255,.4);box-shadow:0 14px 40px rgba(0,0,0,.18);color:#fff;}
.gs{font-size:30px;font-weight:600;display:flex;align-items:center;gap:12px;} .gs2{font-size:26px;font-weight:500;opacity:.85;line-height:1.3;}
.gdot{width:16px;height:16px;border-radius:50%;background:#e8644a;display:inline-block;}
.gbig{font-size:130px;font-weight:800;line-height:1;margin:4px 0 6px;}
.gmono{font:20px Menlo,monospace;white-space:nowrap;opacity:.8;margin:0 0 12px 6px;}
.gwin{background:#fbf8f3;border-radius:18px;padding:12px 16px;height:250px;position:relative;color:#1d1d1b;}
.gwd{display:flex;gap:7px;} .gwd b{width:12px;height:12px;border-radius:50%;}
.gwt{font-size:28px;font-weight:800;margin-top:8px;} .gwv{font:400 54px "Bebas";color:#C9452E;line-height:1;}
.gch{position:absolute;left:16px;right:16px;bottom:14px;height:100px;display:flex;align-items:flex-end;gap:10px;} .gch i{flex:1;}
.glab{font-size:20px;font-weight:700;letter-spacing:2px;color:#ff8a6a;} .gmid{font-size:70px;font-weight:800;line-height:1;margin:4px 0 10px;}
.gred{display:inline-block;background:#E0563B;border-radius:12px;padding:6px 16px;font-size:24px;font-weight:600;}
.gbar{height:16px;border-radius:8px;background:rgba(255,255,255,.3);margin:18px 0 14px;overflow:hidden;} .gbf{height:100%;width:71%;background:#fff;border-radius:8px;}
.gname{font-size:34px;font-weight:800;white-space:nowrap;} .gav{width:84px;height:84px;border-radius:50%;border:3px solid rgba(255,255,255,.8);object-fit:cover;}
.gico{width:76px;height:76px;border-radius:18px;background:#E0563B;display:flex;align-items:center;justify-content:center;flex:none;}
.gpb{height:8px;border-radius:4px;background:rgba(255,255,255,.3);margin:22px 0 10px;overflow:hidden;} .gpb div{height:100%;width:60%;background:#fff;}
.gctl{display:flex;justify-content:center;align-items:center;gap:56px;font-size:36px;}
.gring{width:210px;height:210px;border-radius:50%;background:conic-gradient(#3ddc84 300deg,rgba(255,255,255,.3) 0);display:flex;align-items:center;justify-content:center;}
.gring div{width:166px;height:166px;border-radius:50%;background:rgba(40,36,32,.5);display:flex;align-items:center;justify-content:center;text-align:center;font-size:62px;font-weight:800;line-height:.9;} .gring span{font-size:26px;font-weight:600;}
.gpill{left:50%;margin-left:-260px;top:1660px;width:520px;height:104px;border-radius:52px;display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:600;}
.bbg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 30% 40%,#3a1a08 0%,#140904 55%,#050302 100%);}
.bbg:after{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,140,60,.07) 2px,transparent 2px),linear-gradient(90deg,rgba(255,140,60,.07) 2px,transparent 2px);background-size:90px 90px;}
.bdisk{position:absolute;left:-51px;top:758px;width:640px;height:640px;border-radius:50%;background:radial-gradient(circle,#FF8A3D 0%,#F06A1F 60%,#d4560f 100%);box-shadow:0 0 90px 30px rgba(240,106,31,.55),0 0 220px 80px rgba(240,106,31,.25);}
.bbig{position:absolute;left:0;right:0;text-align:center;top:1330px;font:400 250px "Bebas";line-height:1;color:transparent;-webkit-text-stroke:3px rgba(255,138,61,.32);letter-spacing:6px;}
.btop{position:absolute;left:70px;top:150px;color:rgba(255,255,255,.75);font-size:26px;letter-spacing:6px;font-weight:600;}
.btl{position:absolute;right:50px;top:300px;text-align:right;color:#fff;font:400 135px "Bebas";line-height:.95;letter-spacing:2px;}
.btl em{font-style:normal;color:#FF8A3D;}
.blt{position:absolute;left:60px;top:1560px;} .bln{display:inline-block;background:#F06A1F;color:#fff;font:400 72px "Bebas";padding:8px 22px 0;letter-spacing:3px;} .blh{color:#fff;font-size:34px;margin-top:12px;opacity:.85;}
.bfol{position:absolute;right:60px;top:1575px;background:#F06A1F;color:#fff;font-size:42px;font-weight:700;border-radius:18px;padding:18px 44px;}
.bcur{position:absolute;left:880px;top:1620px;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5));}
.odark{position:absolute;inset:0;background:rgba(0,0,0,.25);}
.orb{position:absolute;left:0;top:0;width:170px;height:302px;border-radius:16px;object-fit:cover;box-shadow:0 14px 40px rgba(0,0,0,.55);border:3px solid rgba(255,255,255,.9);transform-origin:50% 50%;}
.gpap{background:#f3efe6;background-image:linear-gradient(rgba(150,140,120,.13) 1.5px,transparent 1.5px),linear-gradient(90deg,rgba(150,140,120,.13) 1.5px,transparent 1.5px);background-size:44px 44px;}
.gtl{position:absolute;left:60px;top:80px;font-weight:800;font-size:68px;color:#1d1d1b;letter-spacing:-1.5px;line-height:1.12;}
.gtl span{border-bottom:5px solid #C9452E;padding-bottom:2px;} .gtl em{font-family:"Playfair";font-weight:600;color:#C9452E;}
.gy{position:absolute;left:150px;right:40px;height:0;border-top:2px solid rgba(120,110,95,.18);} .gy span{position:absolute;left:-112px;top:-16px;width:96px;text-align:right;font:24px Menlo,monospace;color:#8c8578;}
.gavg{position:absolute;left:150px;right:40px;height:0;border-top:3px dashed #D9583D;z-index:2;} .gavg span{position:absolute;right:0;top:-38px;font:26px Menlo,monospace;color:#D9583D;}
.bar{position:absolute;width:96px;border-radius:12px 12px 0 0;transform-origin:50% 100%;} .bar b{position:absolute;left:-30px;right:-30px;top:-60px;text-align:center;font:400 50px "Bebas";color:#1d1d1b;}
.bn{position:absolute;width:120px;text-align:center;font-size:22px;color:#4d473e;font-weight:700;}
.gwn{position:absolute;left:36px;right:36px;top:965px;bottom:0;border-radius:56px 56px 0 0;overflow:hidden;box-shadow:0 -6px 30px rgba(0,0,0,.12);}
.sdark{position:absolute;inset:0;background:radial-gradient(ellipse 60% 45% at 55% 42%,rgba(0,0,0,.15),rgba(0,0,0,.82) 80%);}
.sdark2{position:absolute;inset:0;background:radial-gradient(ellipse 70% 55% at 55% 45%,transparent 55%,rgba(0,0,0,.6));}
.neon{position:absolute;left:-40px;right:-40px;top:330px;text-align:center;font-family:"Playfair";font-style:italic;font-weight:500;font-size:330px;color:#fff1e3;text-shadow:0 0 8px #fff,0 0 22px #ff9a4d,0 0 48px #ff7a1f,0 0 90px #ff7a1f;}
.ldark{position:absolute;left:0;right:0;bottom:0;height:900px;background:linear-gradient(transparent,rgba(0,0,0,.6));}
.lcard{position:absolute;left:50px;right:50px;top:1230px;border-radius:32px;background:rgba(18,18,18,.72);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1.5px solid rgba(255,255,255,.14);padding:28px 34px;color:#fff;}
.lh{display:flex;align-items:center;gap:14px;font-size:34px;margin-bottom:16px;} .lcn{margin-left:auto;font-size:28px;color:#999;font-family:Menlo,monospace;}
.lr{display:flex;align-items:center;gap:22px;height:86px;border-top:1px solid rgba(255,255,255,.08);}
.lck{width:46px;height:46px;border-radius:50%;border:3px solid #555;color:transparent;font-size:28px;font-weight:900;display:flex;align-items:center;justify-content:center;flex:none;}
.lck.on{background:#2ecc71;border-color:#2ecc71;color:#fff;}
.ltx{font-size:36px;color:#888;font-weight:600;} .ltx.on{color:#fff;}
.ltg{margin-left:auto;font-size:24px;color:#8f8d88;font-family:Menlo,monospace;}
.ztl{position:absolute;left:0;right:0;top:70px;text-align:center;font-weight:800;font-size:80px;color:#1d1d1b;letter-spacing:-2px;}
.ztl em{font-family:"Playfair";font-weight:600;color:#C96442;}
.zed{position:absolute;left:60px;right:60px;top:200px;height:760px;border-radius:26px;background:#261d36;box-shadow:0 20px 50px rgba(40,20,60,.35);overflow:hidden;color:#fff;}
.zbar{height:66px;background:#1d1529;display:flex;align-items:center;gap:12px;padding:0 24px;font-size:22px;color:#b9a9d6;letter-spacing:2px;} .zbar b{width:18px;height:18px;border-radius:50%;}
.zr{display:flex;justify-content:space-between;align-items:center;height:70px;margin:0 30px;border-bottom:1px solid rgba(255,255,255,.07);font-size:30px;} .zr span{color:#b9a9d6;} .zr b{font-weight:600;color:#fff;font-size:28px;}
.ztr{margin:24px 30px 0;height:96px;border-radius:10px;overflow:hidden;} .ztr img{height:96px;width:100%;object-fit:cover;}
.zwv{margin:14px 30px 0;height:60px;display:flex;align-items:center;gap:4px;} .zwv i{flex:1;background:#e7865f;border-radius:3px;}
.zph{position:absolute;left:30px;top:350px;width:4px;height:240px;background:#ff5f57;box-shadow:0 0 10px #ff5f57;}
.zpr{position:absolute;left:30px;right:150px;bottom:40px;height:20px;border-radius:10px;background:rgba(255,255,255,.12);overflow:hidden;} .zpf{height:100%;width:65%;background:linear-gradient(90deg,#e7865f,#D97757);}
.zpc{position:absolute;right:30px;bottom:28px;font-size:38px;font-weight:800;color:#e7865f;}
.zvc{position:absolute;left:60px;right:60px;top:1000px;bottom:60px;border-radius:40px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3);}
'''

home = f'''<div id="home"><div class="sp">{spark(90)}</div><div class="grt">İyi akşamlar, {AD.split()[0]}</div></div>
<div id="ibox"><div class="th0"><img src="assets/p_0.6.jpg"><i>×</i></div>
  <div class="ibi" style="left:40px">+</div><div class="ibi" style="left:110px;font-size:40px;bottom:38px">⚙︎</div><div class="ibi" style="right:150px;font-size:40px;bottom:40px">🎙︎</div><div id="send">↑</div></div>'''
hdr = '<div class="hdr"><div class="ic" style="left:40px">☰</div><div class="tog"><span>Sohbet</span><b>Kod</b></div><div class="ic" style="right:40px">✎</div></div>'
endh = f'''<div id="end"><div id="eh1" class="eh">7 kurgu efekti<small>Claude ile yapıldı</small></div>
<div id="eh2" class="eh" style="opacity:0;font-size:66px;top:120px">Yorumlara “ANİMASYON” yaz<br><span class="pl">7 efektin hepsini göndereyim</span></div>{grid}</div>'''
rsp = f'<div id="rsp" style="opacity:0">{spark(40)} <span>Yorumlara “ANİMASYON” yaz, 7 efektin hepsini göndereyim</span></div>'

html = f'''<!doctype html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
 <div class="clip" id="ui" data-start="0" data-duration="{DUR}" data-track-index="10" style="position:absolute;inset:0;">
  {hdr}{home}{klavye()}
  <div id="rbar"><span style="font-size:46px;color:#c8c6c0">+</span>Claude'a yanıt ver…<span class="up">↑</span></div>
  <div id="tth" style="opacity:0"><img src="assets/p_0.6.jpg"></div>
  {ui_extra}{rsp}
  <div id="dp"><img id="dA" src="assets/dotA.png"><img id="dB" src="assets/dotB.png" style="opacity:0"><img id="dP" src="assets/dotP0.png" style="opacity:0"></div>
  {scenes}{endh}
 </div>
 <audio class="clip" id="sfx" data-start="0" data-duration="{DUR}" data-track-index="3" data-volume="1" src="assets/sfx.wav"></audio>
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
{chr(10).join(J)}
  tl.set({{}}, {{}}, {DUR - 0.01});
  window.__timelines["main"] = tl;
</script></body></html>'''
open("index.html", "w", encoding="utf8").write(html)

# ---------- efektler ----------
SR = 44100; N = int(SR * DUR); L = np.zeros((N, 2))
K = SES.rstrip("/") + "/"; C = {}
for name, t, g in SFX:
    if not os.path.exists(K + name + ".wav"): continue
    if name not in C:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", K + name + ".wav", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        C[name] = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    x = C[name]; i = int(t * SR); n = min(len(x), N - i)
    if n > 0: L[i:i + n] += x[:n] * g
pk = np.abs(L).max(); L = L / max(pk, 1.0) * 0.9
with wave.open("assets/sfx.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((L * 32767).astype(np.int16).tobytes())
print("ok", DUR, "sn,", len(W), "kelime,", len(VID), "video")
