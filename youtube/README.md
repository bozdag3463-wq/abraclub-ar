# YouTube kanalı: çalışma akışı (yüzsüz kanal)

Kamera yok, mikrofon da şart değil. Görüntüyü ve sesi Şerif (Claude) üretir; video yüklemeye hazır çıkar.

## Her gün

1. **Şerif:** Dünün sonuçlarını doğrular, `/yt-script` ile senaryoyu, `/yt-package` ile başlık ve
   kapağı yazar, `youtube/tools/make_video.py` ile videoyu üretir.
   `youtube/tools/seslendir.py` ile Türkçe seslendirir.
   Çıktı: `youtube/<tarih>/<n>-video/video.mp4` (sesli, altyazılı) ve `seslendirme.txt`.
2. **İstersen (CapCut):** Telifsiz müzik ekle ya da sesi kendi sesinle değiştir:
   - `video.mp4`'ü CapCut'a aç.
   - Ses: `seslendirme.txt`'yi **Metin → Metinden sese** ile Türkçe bir sese okut,
     ya da kendi sesini kaydet (yüz gerekmez, sadece ses).
   - Sesi videonun uzunluğuna göre hızlandır/yavaşlat (ya da kareleri sese göre uzat).
   - Telifsiz bir müzik ekle (CapCut'un kendi kütüphanesinden), sesi kısık.
3. **Yükle:** Başlık, açıklama ve etiketleri `<n>-*.md` dosyasından kopyala.

## Video üretmek

Seslendirme (çevrimdışı, sherpa-onnx 1.13.x ve Türkçe piper modeli "fahrettin"):

    python -m venv tts && tts/bin/pip install "sherpa-onnx==1.13.8" soundfile
    curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-tr_TR-fahrettin-medium.tar.bz2
    tar xjf vits-piper-tr_TR-fahrettin-medium.tar.bz2
    tts/bin/python youtube/tools/seslendir.py youtube/<tarih>/<n>-spec.json youtube/<tarih>/<n>-video vits-piper-tr_TR-fahrettin-medium

Sonra video (ses varsa kare süreleri sese göre ayarlanır ve ses videoya eklenir):

    python3 youtube/tools/make_video.py youtube/<tarih>/<n>-spec.json youtube/<tarih>/<n>-video

Spec'te her sahnenin bir görseli (`title`, `scores`, `bignum`, `timeline`, `table`) ve seslendirme
cümleleri (`say`) var. Boyut: uzun video için `[1920, 1080]`, Shorts için `[1080, 1920]`.

## Ses profili

Skill'ler `~/.claude/youtube/voice.md` dosyasını okur. Yeni oturumda:

    mkdir -p ~/.claude/youtube && cp youtube/voice.md ~/.claude/youtube/voice.md

## Yapay zekâ sesi

Her açıklamada "Seslendirme yapay zekâ ile yapılmıştır." satırı olsun. YouTube'da yüklerken
"Değiştirilmiş veya sentetik içerik" sorusuna, ses gerçek bir kişiyi taklit etmediği için genelde
"Hayır" yeterli; emin değilsen "Evet" de.
