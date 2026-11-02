---
name: efekt
description: Konuşan kafa videosuna 25 kurgu efektinden birini ya da birkaçını ekler. Efektler arasında yörünge, spot, cam paneller, belgesel, grafik, kilitlen, yorum kutusu, tier list, LED tabela ve mesajlar var. Efektler yüzü takip eder ve kişinin arkasına geçebilir. Ayrıca Claude arayüzlü iki hazır Reels şablonu (7-efekt, 6-stil) içerir. Kullanıcı /efekt yazdığında, bu efektlerden birini andığında ya da videosuna efekt, yakınlaşma, animasyon veya "Claude ile düzenlendi" kurgusu istediğinde kullan.
---

# Efekt: 25 kurgu efekti (@ugur.saricam)

Kullanıcı çoğunlukla teknik biri değil. Kısa ve sıcak cevap ver, işi sen yap, ondan komut çalıştırmasını isteme.

Aşağıdaki yollar bu skill'in klasörüne göredir. Komutlarda mutlak yolu kullan. Python olarak `.venv/bin/python` kullan.

## 1. İlk kurulum (bir kez)
`bash scripts/kurulum.sh` çalıştır. Bitince `HAZIR` yazar.
- `EKSIK_FFMPEG` çıkarsa: `brew install ffmpeg`.
- `EKSIK_NODE` çıkarsa: `brew install node`.
- `EKSIK_PYTHON` çıkarsa: `brew install python@3.12`, sonra kurulumu tekrar çalıştır.
- Kurulum, saç tellerini net ayıran BiRefNet modelini indirir (~970 MB). İnternet ya da yer sorunu varsa `--hizli` ile sadece küçük U2Net modeli iner.

## 2. Videoyu ve efekti al
- **Video:** Kullanıcı sohbete sürükler ya da yolunu verir. Dikey telefon videosu en iyisidir.
- **Efekt:** `/efekt <ad>` ile ya da kullanıcının anlattığından gelir. Sözlerini aşağıdaki tabloyla eşleştir. Emin değilsen listeyi göster.

## 3. Zamanlamayı bul
- "X kelimesinde" ya da "… dediğimde" derse kelime zamanlarını çıkar. Bunun için kullanıcının bilgisayarındaki whisper araçlarını kullan.
- Zamanlama vermezse tek kısa bir soru sor ya da efekti uygun 2-4 saniyeye yerleştir.
- Kısa pencereler daha iyi görünür: efekt başına 1,5-4 saniye.

## 4. Taslak, kontrol, render
1. Planı videonun yanına `<video-adı>_efekt.json` olarak yaz:
   ```json
   {"efektler": [
     {"fx": "yorunge", "bas": 3.2, "bit": 6.0},
     {"fx": "arka-kelime", "bas": 14.0, "bit": 16.3, "metin": "CLAUDE"}
   ], "kartlar": "/kullanıcının/reels/kapakları"}
   ```
2. Önce kontrol karelerine bak (her efektin ortası):
   ```
   .venv/bin/python scripts/efekt.py --plan <plan.json> <video> <klasör>/kontrol.jpg --kare 4.5,15.2
   ```
   Kareye kendin bak. Yazı yüze biniyorsa, kenardan taşıyorsa ya da okunmuyorsa metni, zamanı veya seçenekleri düzelt. İlk seferde yüz takibi ve kişi ayırma da yapılır; bunlar önbelleğe alınır.
3. Render:
   ```
   .venv/bin/python scripts/efekt.py --plan <plan.json> <video> <video-adı>_efekt.mp4
   ```
   - Çıktı kaynağın fps'ini, rengini (bt709) ve sesini aynen korur.
   - Kişi ayırma varsayılan olarak kaliteli moddadır (BiRefNet): saç kenarı net ama yavaş, kare başına birkaç saniye sürer. Kullanıcı hız isterse `--hizli` ekle; saç kenarı kabalaşır, bunu ona söyle.
4. Dosyanın nerede olduğunu söyle. Tek satırla paylaşmadan önce izlemesini hatırlat: Claude taslak çıkarır, onay ondadır.

Tek efekt için plana gerek yok:
```
.venv/bin/python scripts/efekt.py yorunge <video> <cikti.mp4> --bas 3 --bit 6 --opt metin=CLAUDE
```
Listeyi görmek için: `--liste`.

## 25 efekt
| # | `fx` adı | Ne yapar | Seçenekler (hepsi isteğe bağlı) |
|---|---|---|---|
| 1 | `cam-paneller` | Buzlu cam paneller başın arkasında süzülür, altta "Claude ile düzenlendi" | `metin` (büyük sayı), `etiket`, `ad`, `kullanici`, `degerler` (grafik, `\|` ile), `grafik` (başlık), `halka`, `halka_etiket` |
| 2 | `belgesel` | Siyah-beyaz kişi, başın arkasında renkli daire, satır satır başlık, isim bandı, takip tıklaması | `metin` (satırlar `\|` ile; son kelime renkli), `renk`, `ad`, `kullanici` |
| 3 | `yorunge` | Reels'ler başın etrafında döner; tepede arkada, önde önde | `sayi`, `hiz` (derece/sn), `boyut` |
| 4 | `grafik` | Üstte grafik, altta pencerede kişi, baş pencereden taşar | `degerler`, `yazilar`, `etiketler` (hepsi `\|`), `baslik` (2 satır `\|`), `ortalama` |
| 5 | `spot` | Işıklar söner, kişi aydınlık, arkada neon yazı | `metin`, `renk` |
| 6 | `zaman-cizelgesi` | Üstte kurgu ekranı ve oynatma çizgisi, altta kişi | `baslik` (2 parça `\|`), `metin` (`satır::değer\|…`) |
| 7 | `gurultu` | Reels'ler başın arkasına yığılır | `sayi` |
| 8 | `arka-kelime` | Dev kelime arkaya düşer | `metin`, `renk`, `font` (`serif`) |
| 9 | `led-tabela` | Karartma + arkada kendini yazan LED tabela | `metin` (satırlar `\|`), `renk` |
| 10 | `profil-duvari` | Reels ızgarası arkadaki duvarı doldurur, sayaç artar | `baslangic`, `son` (ör. `24,1B`), `etiket` |
| 11 | `hikaye-kartlari` | Süre, görsel ve yorum kartları düşer, başlık başın üstünde | `sure`, `kart` (2 satır `\|`), `yorumlar` (`\|`), `baslik` (`\|`) |
| 12 | `liste` | Görev listesi, adımlar yeşil tik alır | `metin` (`adım::etiket\|…`), `baslik` |
| 13 | `siralama` | Tier list, Claude S'ye uçar | `baslik` (`\|`), `oge`, `digerleri` (`\|`) |
| 14 | `bolunmus-manset` | Manşet kartı iner, kişi alt pencerede, baş taşar | `metin` (satırlar `\|`), `vurgu`, `etiket` |
| 15 | `tus-yagmuru` | Klavye tuşları arkaya yağar | `metin` (tuşlar `\|`), `sayi` |
| 16 | `kilitlen` | Parantezler yüze kilitlenir, kamera takip eder | `zoom` (vars. 1.35), `metin` (etiket) |
| 17 | `manset` | Yakınlaşma + iki satır manşet, ikincisi beyaz kutuda | `metin` (2 satır `\|`), `zoom`, `y` (px) |
| 18 | `yorum-kutusu` | Yorum kutusuna kelime yazılır, paylaşılır | `metin`, `kullanici` |
| 19 | `mesajlar` | Mesaj bildirimleri sırayla düşer | `metin` (mesajlar `\|`), `baslik`, `y` (0-1) |
| 20 | `anahtarlar` | iPhone anahtarları tek tek açılır | `metin` (satırlar `\|`), `renk` |
| 21 | `takip` | Takip et → Takiptesin | `an` (saniye), `ad`, `kullanici`, `renk`, `y` (0-1) |
| 22 | `damga` | Kırmızı damga ekrana iner | `metin`, `renk`, `aci`, `y` (0-1) |
| 23 | `geri-sayim` | Başın üstünde 3-2-1 çevirmeli saat | `kac` |
| 24 | `yavas-yaklas` | Yavaş yakınlaşma, arka plan bulanık, kişi net | `zoom` (vars. 1.4, en çok 2), `bulaniklik` |
| 25 | `yaklas` | Tek kelimede hızlı yakınlaşma | `zoom` (vars. 1.4), `hiz` |

İngilizce adlar da çalışır: `orbit`, `spotlight`, `glass-widgets`, `locked-on`, `lean-in`, `backdrop-word`, `comment-box`, `tap`, `reject-stamp`, `countdown-flip`, `messages`, `apple-toggles`, `tier-list`, `timeline`, `split-headline`, `checklist`, `led-sign`, `slow-push`, `noise`, `shortcut-rain`, `profile-wall`, `headline-box`.

## Bonus: Claude arayüzlü Reels şablonları
`sablonlar/7-efekt` ve `sablonlar/6-stil` hazır bir Reels'tir. Telefonda Claude uygulamasına `/komut` yazılır, nokta animasyonu oynar, sonuç tam ekrana açılır, kapanışta "Yorumlara “KELİME” yaz" çıkar. Kullanıcı bunu isterse adımlar şöyle:
1. `scripts/yeni.py <şablon> <video> <proje>` ile proje klasörünü aç.
2. `build.py`'nin üstündeki AYARLAR bloğunu doldur, metinleri kullanıcının kendi sözleriyle değiştir.
3. Kesik sahneleri için `scripts/maskele.py` ile maske çıkar.
4. `HAZIRLA=1 scripts/teslim.py` ile önizleme hazırla, `npx hyperframes@0.6.16 snapshot --at …` ile kare al ve onay iste.
5. `scripts/teslim.py` ile render al.

Yüz konumu satırlarını (yörünge merkezi, belgesel kaydırması, pencere ofsetleri) kullanıcının yüzüne göre ayarla. Bu satırlar `build.py` içinde `translate(`, `top:-`, `x = 565` aranarak bulunur.

## Kurallar
- **Yüzü asla kapatma.** Kesik efektlerinde her şey kişinin arkasına geçer. Kart efektleri yüzün altına ya da üstüne yerleşir. Kontrol karesinde hâlâ yüze binen yazı varsa `y`'yi değiştir ya da metni kısalt.
- **Uydurma yok.** Ekrandaki metinler kullanıcının kendi sözlerinden, sayılar gerçek verisinden gelir. Bilmediğin sayıyı sor.
- **Kaynağa dokunma.** Keskinlik, filtre ya da renk ayarı yapma. Çıktı kaynağın rengini ve sesini korur.
- **Zoom 2x'i geçmez**, böylece görüntü net kalır.
- Efektler plandaki sırayla uygulanır. Kamera efektlerini (`kilitlen`, `yaklas`, `yavas-yaklas`, `manset`) aynı anda üst üste koyma.
- Bunlar başlangıç sürümleri. Kullanıcı bir Reels'le karşılaştırırsa bunu açıkça söyle.
