"""6 kurgu stili: Claude arayüzünde /komut yazılır, sonuç kartı tam ekrana açılır.
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
B = 3.3                      # her yetenek bloğu
E0 = 6 * B                   # kapanış
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
    ("arkandaki-grafik", "Arkanda grafikler, temiz kesim", 0.8, "/ar"),
    ("bölünmüş-ekran", "Üstte görsel, altta sen, ortada altyazı", 0.95, "/bö"),
    ("anlatıcı", "Sen altta kartta, görseller üstte anlatır", 0.9, "/an"),
    ("deneme-reels", "Deneme reels için 3 farklı versiyon", 0.0, "/de"),
    ("hikaye", "Üç görsel, bir başlık, küçük altyazı", 1.5, "/hi"),
    ("sıralama", "S'den F'ye liste, kartlar yerine düşer", 2.0, "/sı"),
]
POST = {0: "p_1.8", 1: "p_3.0", 2: "p_1.2", 3: "p_1.2", 4: "p_2.4", 5: "p_3.5"}

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
def sahne(k, pref, mode):
    B0 = k * B; m = SK[k][2]; vid = f"{pref}v{k}"
    if k == 0:   # arkandaki grafik
        h = media(mode, vid, k, B0 + 0.8, m - 0.7)
        h += f'<div id="{pref}pn0" class="pn0"><img src="assets/ig_grid.png"></div>'
        if mode == "v":
            VID.append((f"{pref}cut", B0 + 0.8, m - 0.7))
            h += f'<video id="{pref}cut" class="clip" data-start="{B0 + 0.8:.4f}" data-duration="{B - 0.8 + 0.1:.3f}" data-track-index="{60 + len(VID)}" data-media-start="{max(m - 0.7 - MK0, 0):.3f}" src="assets/kesik.mov" muted playsinline style="position:absolute;left:0;top:0;width:1080px;height:1920px;"></video>'
        else:
            h += '<img src="assets/kesik_poster.png" style="position:absolute;left:0;top:0;width:1080px;height:1920px;">'
        vals = ["0", "6,2B", "12,8B", "19,3B", "24,1B"]
        h += f'<div class="cnt">' + "".join(f'<span id="{pref}n{i}" style="display:{"inline" if (mode=="i" and i==4) else "none"}">{v}</span>' for i, v in enumerate(vals)) + '</div>'
        h += f'<div class="chip0"><img class="cav" src="assets/ig_avatar.png"><div><b>{AD}</b><br><span>{TAKIPCI} takipçi</span></div><div class="fbtn">Takip et</div></div>'
        h += caps(pref, k, m, B0, "cap0", mode)
        if mode == "v":
            for i in range(5): S(f"#{pref}n{i}", '{display:"inline"}', B0 + 1.5 + i * 0.22); S(f"#{pref}n{i}", '{display:"none"}', B0 + 1.5 + (i + 1) * 0.22) if i < 4 else None
            pass
    elif k == 1:  # bölünmüş ekran
        h = '<div class="cream" style="position:absolute;inset:0"></div>'
        h += f'<div class="w1">{media(mode, vid, k, B0 + 0.8, m - 0.7, "top:-642px;left:-110px;width:1166px;height:2074px;")}</div>'
        kst = f"position:absolute;left:-70px;top:318px;width:1166px;height:2074px;clip-path:inset(0 56px 531px 110px);"
        if mode == "v":
            VID.append((f"{pref}cut1", B0 + 1.4, 0))
            h += f'<video id="{pref}cut1" class="clip" data-start="{B0 + 1.4:.4f}" data-duration="{B - 1.4 + 0.1:.3f}" data-track-index="{60 + len(VID)}" data-media-start="{max(m - 0.1 - MK0, 0):.3f}" src="assets/kesik.mov" muted playsinline style="{kst}"></video>'
        else:
            h += f'<img src="assets/kesik_poster.png" style="{kst}">'
        h += f'''<div class="top1"><div class="pill">{spark(30,"#fff")} Adım 1</div>
          <div class="ttl">Ne <i>görüyorsun?</i></div>
          <div class="win"><div class="wbar"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b><span>chatgpt.com</span></div>
            <img class="wph" src="assets/foto.jpg"><div class="wtx"><div class="ln" style="width:300px"></div><div class="ln" style="width:240px"></div><div class="ln" style="width:270px"></div></div>
            <div id="{pref}wbt" class="wbt">Fotoğraf ekle +</div><div id="{pref}cur" class="cur">➤</div></div></div>'''
        h += caps(pref, k, m, B0, "cap1", mode, gri_ikinci)
        if mode == "v":
            T(f"#{pref}cur", "{x:-260,y:120}", "{x:0,y:0}", B0 + 1.6, 0.7, "power3.inOut")
            T(f"#{pref}wbt", "{scale:1}", "{scale:0.92,yoyo:true,repeat:1}", B0 + 2.3, 0.1, "none")
    elif k == 2:  # anlatıcı
        h = f'''<div class="cream" style="position:absolute;inset:0"></div>
          <div class="ttl2">Asıl mesele <i>yorum</i></div>
          <div class="lb" style="left:110px">FİNCAN</div><div class="lb" style="left:670px">YORUM</div>
          <img class="c2a" src="assets/foto.jpg">
          <div class="c2b"><div id="{pref}q" class="q">?</div><div id="{pref}ans" class="ans"><b>Yorum</b><div class="ln"></div><div class="ln" style="width:70%"></div><div class="ln" style="width:85%"></div><div class="ln" style="width:55%"></div></div></div>
          <svg class="arr" viewBox="0 0 300 120"><path id="{pref}ap" d="M10 100 C 90 0, 210 0, 285 70" fill="none" stroke="#c96442" stroke-width="7" stroke-linecap="round" stroke-dasharray="360" stroke-dashoffset="0"/><path d="M262 66 L287 72 L278 47" fill="none" stroke="#c96442" stroke-width="7" stroke-linecap="round"/></svg>
          <div class="vc2">{media(mode, vid, k, B0 + 0.8, m - 0.7, "top:-330px;left:-115px;")}</div>'''
        h += caps(pref, k, m, B0, "cap2", mode, gradyan_kelime)
        if mode == "v":
            T(f"#{pref}ap", "{strokeDashoffset:360}", "{strokeDashoffset:0}", B0 + 1.7, 0.5)
            S(f"#{pref}q", '{opacity:1}', B0); S(f"#{pref}ans", '{opacity:0}', B0)
            S(f"#{pref}q", '{opacity:0}', B0 + 2.25); T(f"#{pref}ans", "{opacity:0,y:20}", "{opacity:1,y:0}", B0 + 2.25, 0.3)
        else:
            h = h.replace(f'id="{pref}q" class="q"', f'id="{pref}q" class="q" style="opacity:0"')
    elif k == 3:  # deneme reels — tam ekrana açılmaz, 3 kart
        hooks = ["FİNCANDA NE <y>GÖRÜYORSUN?</y>", "ASIL ÖNEMLİ OLAN <y>YORUM</y>", "SEN NE <y>GÖRDÜN?</y>"]
        ms = [0.0, 0.6, 1.2]; TC3 = ["fincanda", "yorum", "sen ne gördün?"]
        h = ""
        for i in range(3):
            if mode == "v":
                VID.append((f"{pref}v3_{i}", B0 + 0.8, ms[i]))
                mv = f'<video id="{pref}v3_{i}" class="clip" data-start="{B0 + 0.8:.4f}" data-duration="{B - 0.8 + 0.1:.3f}" data-track-index="{60 + len(VID)}" data-media-start="{ms[i]:.3f}" src="{KLIP}" muted playsinline style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;"></video>'
            else:
                mv = f'<img src="assets/{["p_0.6","p_1.8","p_3.0"][i]}.jpg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;">'
            if i == 0: deco = f'<div class="th">{hooks[0]}</div><div class="tcap">{TC3[0]}</div>'
            elif i == 1: deco = f'<div class="ttw"><div class="ttwh"><img src="assets/ig_avatar.png"><div><b>{AD}</b><br>{KULLANICI}</div></div>Fincanda ne görüyorsun? Asıl mesele yorum.</div><div class="tcap2">{TC3[1].upper()}</div>'
            else:
                deco = f'<div class="t3big">1 FİNCAN</div><div class="t3s">{TC3[2]}</div>'
                mv = f'<div class="t3f">{mv}</div>'
            h += f'<div id="{pref}t{i}" class="tc{" t3" if i == 2 else ""}" style="left:{23 + i * 352}px">{mv}{deco}</div>'
            if mode == "v": T(f"#{pref}t{i}", "{scale:0.86,opacity:0}", "{scale:1,opacity:1}", B0 + 1.5 + i * 0.12, 0.3, "back.out(1.6)")
    elif k == 4:  # hikaye
        h = media(mode, vid, k, B0 + 0.8, m - 0.7, "left:-194px;width:1404px;height:2496px;")
        h += '<div class="shade4"></div>'
        tv = ["0:41", "0:42", "0:43", "0:44", "0:45", "0:46"]
        h += f'''<div class="k4a"><div class="k4s">GEÇEN SÜRE</div><div id="{pref}ring" class="ring"><div class="rin">''' + "".join(
            f'<span id="{pref}tm{i}" style="display:{"inline" if (mode=="i" and i==5) else "none"}">{v}</span>' for i, v in enumerate(tv)) + '''</div></div><div class="k4s" style="margin-top:6px">saniye</div></div>'''
        h += f'<div class="k4b"><img src="assets/foto.jpg"><div class="k4bt">FİNCANDA<br><y>NE VAR?</y></div></div>'
        h += '<div class="k4c"><b>Yorumlar</b>' + "".join(f'<div class="cm"><i style="background:{c}"></i>{t}</div>' for c, t in [("#e74c3c", "ANİMASYON"), ("#3498db", "ne gördün?"), ("#f1c40f", "ANİMASYON"), ("#2ecc71", "devamı 👀")]) + '</div>'
        h += '<div class="t4">Fincanda ne gördüğün değil,<br>yorumda ne gördüğün önemli<div class="sub4"><span>asıl mesele bu</span></div></div>'
        h += caps(pref, k, m, B0, "cap0 c4", mode)
        if mode == "v":
            for i in range(6):
                S(f"#{pref}tm{i}", '{display:"inline"}', B0 + 1.5 + i * 0.3)
                if i < 5: S(f"#{pref}tm{i}", '{display:"none"}', B0 + 1.5 + (i + 1) * 0.3)
            T(f"#{pref}ring", '{"--p":200}', '{"--p":290}', B0 + 1.5, 1.8, "none")
    else:  # sıralama
        h = media(mode, vid, k, B0 + 0.8, m - 0.7)
        h += '<div class="shade6"></div><div class="t6">YAPAY ZEKA<br>SIRALAMASI</div>'
        tiers = [("S", "#ff7f7f"), ("A", "#ffbf7f"), ("B", "#ffdf7f"), ("C", "#bfff7f"), ("D", "#7fbfff"), ("E", "#9f7fff"), ("F", "#d77fff")]
        IC = {"A": "chatgpt", "B": "perplexity", "C": "gemini", "D": "deepseek"}
        h += '<div class="tier">' + "".join(f'<div class="tr"><div class="tl" style="background:{c}">{t}</div>' + (f'<img class="tlg" src="assets/logo_{IC[t]}.png">' if t in IC else '') + '</div>' for t, c in tiers) + '</div>'
        h += f'<div id="{pref}card6" class="card6"><img src="assets/logo_claude.png"></div>'
        h += caps(pref, k, m, B0, "cap0 c6", mode)
        if mode == "v":
            T(f"#{pref}card6", "{y:-1300,rotation:-10}", "{y:0,rotation:-2}", B0 + 2.2, 0.55, "bounce.out")
            sx("impact1", B0 + 2.45, 0.35)
    return h


def fl(sel, t, amp=14, d=0.9):
    J.append(f'  tl.fromTo("{sel}", {{y:0}}, {{y:{-amp}, duration:{d}, ease:"sine.inOut", yoyo:true, repeat:1}}, {fr(t):.4f});')
def hareket(k, rid, B0):
    T(f"#z{k}", "{scale:1}", "{scale:1.06}", B0 + 1.5, B - 1.5, "none")
    if k == 0:
        T(f"#{rid} .pn0", "{y:60,rotation:-2}", "{y:0,rotation:0}", B0 + 1.5, 0.7, "power3.out"); fl(f"#{rid} .pn0 img", B0 + 2.2, 10, 0.55)
        T(f"#{rid} .chip0", "{y:160,opacity:0}", "{y:0,opacity:1}", B0 + 2.0, 0.45, "back.out(1.5)"); sx("whoosh_kisa2", B0 + 2.0, 0.25)
    elif k == 1:
        T(f"#{rid} .win", "{y:50,opacity:0}", "{y:0,opacity:1}", B0 + 1.95, 0.4, "power3.out"); fl(f"#{rid} .win", B0 + 2.35, 8, 0.45)
        T(f"#{rid} .ttl", "{y:-30,opacity:0}", "{y:0,opacity:1}", B0 + 1.9, 0.35, "power3.out")
    elif k == 2:
        T(f"#{rid} .c2a", "{x:-80,rotation:-8,opacity:0}", "{x:0,rotation:0,opacity:1}", B0 + 1.9, 0.4, "back.out(1.4)")
        T(f"#{rid} .c2b", "{x:80,rotation:8,opacity:0}", "{x:0,rotation:0,opacity:1}", B0 + 2.0, 0.4, "back.out(1.4)")
        fl(f"#{rid} .c2a", B0 + 2.35, 10, 0.45)
    elif k == 4:
        for j, c in enumerate(("k4a", "k4b", "k4c")):
            T(f"#{rid} .{c}", "{y:-120,opacity:0}", "{y:0,opacity:1}", B0 + 1.95 + j * 0.1, 0.45, "back.out(1.6)"); sx("pop", B0 + 1.95 + j * 0.1, 0.15)
            fl(f"#{rid} .{c}", B0 + 2.45 + j * 0.05, 10, 0.4)
        T(f"#{rid} .t4", "{y:30,opacity:0}", "{y:0,opacity:1}", B0 + 2.2, 0.35, "power3.out")
    elif k == 5:
        T(f"#{rid} .t6", "{scale:1.3,opacity:0}", "{scale:1,opacity:1}", B0 + 1.9, 0.35, "back.out(1.6)")
        J.append(f'  tl.fromTo("#{rid} .tr", {{x:-700,opacity:0}}, {{x:0,opacity:1,duration:0.3,ease:"power3.out",stagger:0.04}}, {fr(B0 + 1.85):.4f});')

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
    # noktalar
    S("#dp", "{opacity:1}", B0 + 0.85); S("#dP", f'{{opacity:0,attr:{{src:"assets/dotP{k}.png"}}}}', B0)
    for j in range(9):
        t = B0 + 0.85 + j * 0.08
        S("#dA", f"{{opacity:{1 if j % 2 == 0 else 0}}}", t); S("#dB", f"{{opacity:{0 if j % 2 == 0 else 1}}}", t)
    T("#dP", "{opacity:0}", "{opacity:1}", B0 + 1.1, 0.35, "none")
    T("#dA", "{opacity:1}", "{opacity:0}", B0 + 1.25, 0.2, "none"); S("#dB", "{opacity:0}", B0 + 1.25)
    S("#dp", "{opacity:0}", B0 + 1.62)
    # sonuç
    rid = f"r{k}"
    if k == 3:
        scenes += f'<div id="{rid}" class="res3" style="opacity:0">{sahne(k, "", "v")}</div>'
        S(f"#{rid}", "{opacity:1}", B0 + 1.5); S(f"#{rid}", "{opacity:0}", B0 + B)
        sx("kagit_kisa", B0 + 1.5, 0.3)
    else:
        scenes += f'<div id="{rid}" class="res" style="opacity:0"><div id="z{k}" class="zin">{sahne(k, "", "v")}</div></div>'
        hareket(k, rid, B0)
        S(f"#{rid}", "{opacity:1,x:43,y:455,scale:0.639,borderRadius:34}", B0 + 1.5)
        J.append(f'  tl.to("#{rid}", {{x:0,y:0,scale:1,borderRadius:0,duration:0.32,ease:"power3.inOut"}}, {fr(B0 + 1.85):.4f});')
        S(f"#{rid}", "{opacity:0}", B0 + B)
        sx("whoosh_kisa1", B0 + 1.8, 0.4)

# ---------- kapanış ----------
tg = blok_arayuz(6, E0, "animasyon", "", "animasyon", son=True)
S("#rsp", '{display:"flex"}', tg + 0.35); T("#rsp", "{opacity:0}", "{opacity:1}", tg + 0.35, 0.2)
grid = ""
for k in range(6):
    col, row = k % 3, k // 3
    x, y = 60 + col * 330, 350 + row * 640
    inner = sahne(k, "g_", "i")
    bg = "#222120" if k == 3 else "#000"
    grid += f'<div class="gc" style="left:{x}px;top:{y}px;background:{bg}"><div style="position:absolute;left:0;top:0;width:1080px;height:1920px;transform:scale({300/1080:.5f});transform-origin:0 0;">{inner}</div></div><div class="gl" style="left:{x}px;top:{y + 545}px">/{SK[k][0]}</div>'
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
/* sahne 0 */
.pn0{position:absolute;left:110px;right:110px;top:130px;height:1111px;border-radius:34px;background:#000;box-shadow:0 20px 60px rgba(0,0,0,.5);overflow:hidden;}
.pnh{height:110px;border-bottom:2px solid #eee;font:600 44px -apple-system;color:#111;padding:30px 40px;}
.pnu{position:absolute;right:50px;top:150px;width:420px;height:420px;border-radius:30px;overflow:hidden;} .pnu img{width:100%;height:100%;object-fit:cover;}
.pnbar{position:absolute;right:50px;top:600px;width:420px;height:16px;border-radius:8px;background:#e8e8e8;overflow:hidden;} .pnf{height:100%;width:100%;background:#10a37f;}
.pnt{position:absolute;right:50px;top:640px;font-size:30px;color:#777;}
.cnt{position:absolute;left:0;right:0;top:1395px;text-align:center;color:#fff;font-weight:800;font-size:120px;text-shadow:0 6px 30px rgba(0,0,0,.7);}
.chip0{position:absolute;left:150px;right:150px;top:1560px;height:130px;border-radius:30px;background:rgba(25,25,25,.85);display:flex;align-items:center;gap:24px;padding:0 28px;color:#fff;font-size:36px;line-height:1.2;}
.chip0 span{font-size:28px;color:#bbb;font-weight:500;} .cav{width:84px;height:84px;border-radius:50%;flex:none;} .pn0 img{width:100%;display:block;}
.fbtn{margin-left:auto;background:#3897f0;border-radius:30px;padding:12px 26px;font-size:30px;font-weight:700;}
.cap0{position:absolute;left:0;right:0;top:1250px;text-align:center;color:#fff;font-weight:800;font-size:82px;text-shadow:0 4px 22px rgba(0,0,0,.75),0 0 3px rgba(0,0,0,.6);letter-spacing:-1px;}
.c4{top:1560px;} .c6{top:1000px;}
/* sahne 1 */
.cream{background:#f4f0e8;background-image:radial-gradient(#d9d2c4 2px,transparent 2.5px);background-size:34px 34px;}
.top1{position:absolute;left:0;top:0;width:1080px;height:960px;}
.w1{position:absolute;left:40px;top:960px;width:1000px;height:900px;border-radius:48px;overflow:hidden;box-shadow:0 20px 60px rgba(60,40,20,.25);}
.pill{position:absolute;left:50%;transform:translateX(-50%);top:120px;background:#D97757;color:#fff;font-size:36px;font-weight:600;border-radius:14px;padding:8px 24px;display:flex;align-items:center;gap:10px;}
.ttl{position:absolute;left:0;right:0;top:150px;text-align:center;font:400 100px Georgia,serif;color:#1d1d1b;letter-spacing:-2px;}
.ttl i,.ttl2 i{font-family:"Playfair";color:#C96442;font-weight:500;}
.win{position:absolute;left:100px;right:100px;top:320px;height:480px;background:#fff;border-radius:26px;box-shadow:0 18px 50px rgba(60,40,20,.18);overflow:hidden;}
.wbar{height:70px;background:#f5f4f2;display:flex;align-items:center;gap:12px;padding:0 24px;} .wbar b{width:20px;height:20px;border-radius:50%;}
.wbar span{margin-left:20px;background:#fff;border-radius:20px;padding:6px 30px;font-size:26px;color:#888;flex:1;}
.wph{position:absolute;left:40px;top:110px;width:330px;height:330px;border-radius:20px;object-fit:cover;}
.wtx{position:absolute;left:410px;top:130px;} .ln{height:22px;border-radius:11px;background:#ececec;margin-bottom:22px;width:100%;}
.wbt{position:absolute;left:410px;top:330px;background:#111;color:#fff;border-radius:30px;padding:18px 34px;font-size:32px;font-weight:700;}
.cur{position:absolute;left:640px;top:370px;font-size:56px;color:#fff;text-shadow:0 0 0 #000,0 2px 6px rgba(0,0,0,.6);transform-origin:0 0;-webkit-text-stroke:3px #111;}
.cap1{position:absolute;left:50%;transform:translateX(-50%);top:915px;background:#141414;border-radius:16px;padding:10px 30px 4px;color:#fff;font:400 92px "Bebas";letter-spacing:2px;white-space:nowrap;z-index:3;}
/* sahne 2 */
.ttl2{position:absolute;left:0;right:0;top:110px;text-align:center;color:#1d1d1b;font-weight:800;font-size:96px;letter-spacing:-2px;}
.ttl2 i{font-size:104px;}
.lb{position:absolute;top:262px;width:300px;text-align:center;font-size:26px;font-weight:700;color:#8c8578;letter-spacing:2px;}
.c2a{position:absolute;left:110px;top:310px;width:300px;height:380px;object-fit:cover;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.18);}
.c2b{position:absolute;left:670px;top:310px;width:300px;height:380px;border-radius:16px;border:4px dashed #cfc6b6;background:#fbf9f4;}
.q{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:120px;color:#cfc6b6;}
.ans{position:absolute;inset:26px;opacity:1;} .ans b{display:block;font-size:40px;color:#C96442;margin-bottom:24px;} .ans .ln{background:#e3ddd1;}
.arr{position:absolute;left:400px;top:270px;width:300px;height:120px;}
.vc2{position:absolute;left:90px;right:90px;top:760px;height:1080px;border-radius:44px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.cap2{position:absolute;left:0;right:0;top:1560px;text-align:center;color:#fff;font-weight:800;font-size:76px;text-shadow:0 4px 22px rgba(0,0,0,.75);letter-spacing:-1px;z-index:3;}
.cap2 i{font-family:"Playfair";font-weight:600;font-size:84px;}
/* sahne 3 */
.tc{position:absolute;top:470px;width:330px;height:587px;border-radius:22px;overflow:hidden;background:#000;}
.tcap{position:absolute;left:0;right:0;top:330px;text-align:center;color:#fff;font-weight:700;font-size:24px;text-shadow:0 2px 8px rgba(0,0,0,.9);}
.tcap2{position:absolute;left:0;right:0;top:360px;text-align:center;color:#FFE04A;font:400 46px "Bebas";text-shadow:0 3px 10px rgba(0,0,0,.9);}
.ttw{position:absolute;left:16px;right:16px;top:60px;background:#fff;border-radius:12px;padding:10px 12px;color:#111;font-size:19px;font-weight:600;line-height:1.25;box-shadow:0 4px 14px rgba(0,0,0,.4);}
.ttwh{display:flex;gap:8px;align-items:center;font-size:12px;font-weight:500;color:#555;margin-bottom:6px;line-height:1.15;} .ttwh b{color:#111;font-size:13px;} .ttwh img{width:28px;height:28px;border-radius:50%;}
.t3{background:#151515;background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);background-size:22px 22px;}
.t3big{position:absolute;left:0;right:0;top:34px;text-align:center;color:#F07A3A;font:400 74px "Bebas";line-height:1;}
.t3s{position:absolute;left:0;right:0;top:110px;text-align:center;color:#fff;font-size:20px;font-weight:600;}
.t3f{position:absolute;left:34px;right:34px;top:150px;bottom:24px;border-radius:16px;overflow:hidden;border:2px solid rgba(240,122,58,.7);}
.th{position:absolute;left:14px;right:14px;top:44px;text-align:center;color:#fff;font:400 50px "Bebas";line-height:1;text-shadow:0 3px 10px rgba(0,0,0,.9);}
.th y,.k4bt y{color:#FFD43B;}
.tcap{position:absolute;left:0;right:0;top:400px;text-align:center;color:#fff;font-weight:800;font-size:34px;text-shadow:0 2px 10px rgba(0,0,0,.9);}
/* sahne 4 */
.shade4{position:absolute;left:0;right:0;top:0;height:1000px;background:linear-gradient(rgba(0,0,0,.45),transparent);}
.k4a{position:absolute;left:50px;top:150px;width:250px;height:290px;border-radius:26px;background:#fff;text-align:center;padding-top:22px;box-shadow:0 10px 30px rgba(0,0,0,.4);transform:rotate(-3deg);}
.k4s{font-size:22px;font-weight:700;color:#666;letter-spacing:1px;}
.ring{--p:290;width:170px;height:170px;border-radius:50%;margin:12px auto 0;background:conic-gradient(#D97757 calc(var(--p)*1deg),#eee 0);display:flex;align-items:center;justify-content:center;}
.rin{width:130px;height:130px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:44px;font-weight:800;color:#111;}
.k4b{position:absolute;left:350px;top:120px;width:330px;height:380px;border-radius:22px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.5);}
.k4b img{width:100%;height:100%;object-fit:cover;} .k4bt{position:absolute;left:0;right:0;bottom:24px;text-align:center;color:#fff;font:400 64px "Bebas";line-height:.95;text-shadow:0 3px 12px rgba(0,0,0,.9);}
.k4c{position:absolute;right:50px;top:150px;width:290px;height:300px;border-radius:26px;background:#fff;padding:22px 24px;box-shadow:0 10px 30px rgba(0,0,0,.4);transform:rotate(3deg);font-size:30px;color:#111;}
.cm{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:700;margin-top:16px;color:#333;} .cm i{width:26px;height:26px;border-radius:50%;flex:none;}
.t4{position:absolute;left:0;right:0;top:500px;text-align:center;color:#fff;font-weight:800;font-size:50px;line-height:1.12;letter-spacing:-1px;text-shadow:0 4px 24px rgba(0,0,0,.85);}
.sub4{margin-top:14px;} .sub4 span{display:inline-block;background:#fff;color:#111;font-size:36px;font-weight:700;border-radius:10px;padding:6px 20px;letter-spacing:0;text-shadow:none;}
/* sahne 5 */
.shade6{position:absolute;left:0;right:0;top:0;height:700px;background:linear-gradient(rgba(0,0,0,.55),transparent);}
.t6{position:absolute;left:0;right:0;top:120px;text-align:center;font-weight:900;font-style:italic;font-size:94px;line-height:.98;letter-spacing:-2px;color:#FFB23E;text-shadow:0 0 30px rgba(255,140,30,.55),0 6px 20px rgba(0,0,0,.6);}
.tier{position:absolute;left:110px;right:110px;top:1230px;border-radius:12px;overflow:hidden;background:#141414;border:3px solid #333;}
.tr{height:92px;border-bottom:2px solid #2c2c2c;display:flex;align-items:center;} .ti{width:44px;height:74px;object-fit:cover;margin-left:14px;border-radius:4px;} .tlg{width:76px;height:76px;object-fit:contain;margin-left:20px;} .tv{margin-left:18px;color:#fff;font-weight:800;font-size:40px;} .tl{width:96px;height:100%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:46px;color:#111;}
.card6{position:absolute;left:228px;top:1150px;width:170px;height:170px;filter:drop-shadow(0 16px 30px rgba(0,0,0,.6));transform:rotate(-2deg);} .card6 img{width:170px!important;height:170px!important;object-fit:contain;}
.c6l{width:190px;height:190px;border-radius:24px;background:#F4F0E8;display:flex;align-items:center;justify-content:center;flex:none;} .card6 img{width:130px;height:226px;border-radius:12px;object-fit:cover;} .card6 div{color:#fff;font:400 84px "Bebas";line-height:.95;}
'''

home = f'''<div id="home"><div class="sp">{spark(90)}</div><div class="grt">İyi akşamlar, {AD.split()[0]}</div></div>
<div id="ibox"><div class="th0"><img src="assets/p_0.6.jpg"><i>×</i></div>
  <div class="ibi" style="left:40px">+</div><div class="ibi" style="left:110px;font-size:40px;bottom:38px">⚙︎</div><div class="ibi" style="right:150px;font-size:40px;bottom:40px">🎙︎</div><div id="send">↑</div></div>'''
hdr = '<div class="hdr"><div class="ic" style="left:40px">☰</div><div class="tog"><span>Sohbet</span><b>Kod</b></div><div class="ic" style="right:40px">✎</div></div>'
endh = f'''<div id="end"><div id="eh1" class="eh">6 kurgu yeteneği<small>Claude ile yapıldı</small></div>
<div id="eh2" class="eh" style="opacity:0;font-size:66px;top:120px">Yorumlara “ANİMASYON” yaz<br><span class="pl">6'sını da göndereyim</span></div>{grid}</div>'''
rsp = f'<div id="rsp" style="opacity:0">{spark(40)} <span>Yorumlara “ANİMASYON” yaz, 6’sını da göndereyim</span></div>'

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
