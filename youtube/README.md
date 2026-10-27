# YouTube kanalı: çalışma akışı (yüzsüz kanal)

Kamera yok. Görüntüyü Şerif (Claude) üretir, ses telefonda eklenir.

## Her gün

1. **Şerif:** Dünün sonuçlarını doğrular, `/yt-script` ile senaryoyu, `/yt-package` ile başlık ve
   kapağı yazar, `youtube/tools/make_video.py` ile videoyu üretir.
   Çıktı: `youtube/<tarih>/<n>-video/video.mp4` (sessiz, altyazılı) ve `seslendirme.txt`.
2. **Sen (CapCut, telefonda, ~10 dk):**
   - `video.mp4`'ü CapCut'a aç.
   - Ses: `seslendirme.txt`'yi **Metin → Metinden sese** ile Türkçe bir sese okut,
     ya da kendi sesini kaydet (yüz gerekmez, sadece ses).
   - Sesi videonun uzunluğuna göre hızlandır/yavaşlat (ya da kareleri sese göre uzat).
   - Telifsiz bir müzik ekle (CapCut'un kendi kütüphanesinden), sesi kısık.
3. **Yükle:** Başlık, açıklama ve etiketleri `<n>-*.md` dosyasından kopyala.

## Video üretmek

    python3 youtube/tools/make_video.py youtube/<tarih>/<n>-spec.json youtube/<tarih>/<n>-video

Spec'te her sahnenin bir görseli (`title`, `scores`, `bignum`, `timeline`, `table`) ve seslendirme
cümleleri (`say`) var. Boyut: uzun video için `[1920, 1080]`, Shorts için `[1080, 1920]`.

## Ses profili

Skill'ler `~/.claude/youtube/voice.md` dosyasını okur. Yeni oturumda:

    mkdir -p ~/.claude/youtube && cp youtube/voice.md ~/.claude/youtube/voice.md
