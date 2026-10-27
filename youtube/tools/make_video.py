#!/usr/bin/env python3
"""make_video.py - bir video spec'inden (JSON) hareketli, altyazılı MP4 üretir.

    python3 make_video.py spec.json out_dir

Her sahne bir görsel (title, scores, bignum, timeline, table) ve seslendirme cümlelerinden oluşur.
Görsel aşağıdan kayarak gelir ve yavaşça yakınlaşır; arka plan kayar; altyazı kelime kelime
vurgulanır. Süreler seslendir.py'nin çıktısından, yoksa kelime sayısından (dakikada 150) gelir.
Çıktı: video.mp4, sesliyse video-sessiz.mp4 (CapCut için) ve seslendirme.txt.
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BG, FG, MUTED, ACCENT = (15, 17, 21), (245, 245, 245), (150, 155, 165), (255, 196, 0)
WPS = 2.5  # 150 kelime / dakika

def font(size, bold=True): return ImageFont.truetype(FONT if bold else FONT_REG, size)

def center(d, y, text, f, fill=FG, w=None):
    w = w or d.im.size[0]
    while d.textlength(text, font=f) > w - 80 and f.size > 20:  # dikey videoda taşmasın
        f = f.font_variant(size=f.size - 4)
    tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, y), text, font=f, fill=fill)

def draw_title(d, v, W, H):
    y = H * 0.28
    for i, line in enumerate(v["lines"]):
        f = font(v.get("size", 110) if i == 0 else 60)
        center(d, y, line, f, ACCENT if i == 0 else FG)
        y += f.size * 1.35

def draw_scores(d, v, W, H):
    center(d, H * 0.09, v["header"], font(64), ACCENT)
    rows = v["rows"]
    rh = min(150, (H * 0.6) / max(1, len(rows)))
    f, fs = font(int(rh * 0.48)), font(int(rh * 0.3), False)
    y = H * 0.22
    for r in rows:
        if r.get("muted"):
            center(d, y + rh * 0.2, r["text"], fs, MUTED)
        else:
            mid = W / 2
            d.text((mid - 140 - d.textlength(r["home"], font=f), y), r["home"], font=f, fill=FG)
            score = f'{r["hs"]} - {r["as"]}'
            d.text((mid - d.textlength(score, font=f) / 2, y), score, font=f, fill=ACCENT)
            d.text((mid + 140, y), r["away"], font=f, fill=FG)
            if r.get("league"):
                d.text((60, y + rh * 0.12), r["league"], font=fs, fill=MUTED)
        y += rh

def draw_bignum(d, v, W, H):
    center(d, H * 0.05, v["num"], font(300), ACCENT)
    y = H * 0.38
    for i, line in enumerate(v["lines"]):
        f = font(72 if i == 0 else 48, i == 0)
        center(d, y, line, f, FG if i == 0 else MUTED)
        y += f.size * 1.4

def draw_timeline(d, v, W, H):
    center(d, H * 0.05, v["header"], font(60), ACCENT)
    ev = v["events"]
    x0, x1, y = 140, W - 140, H * 0.36
    d.line((x0, y, x1, y), fill=MUTED, width=6)
    f, fs = font(44), font(34, False)
    for i, (minute, score, who) in enumerate(ev):
        x = x0 + (x1 - x0) * i / max(1, len(ev) - 1)
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=ACCENT)
        d.text((x - d.textlength(minute, font=fs) / 2, y - 80), minute, font=fs, fill=MUTED)
        d.text((x - d.textlength(score, font=f) / 2, y + 34), score, font=f, fill=FG)
        d.text((x - d.textlength(who, font=fs) / 2, y + 96), who, font=fs, fill=MUTED)
    if v.get("note"):
        center(d, H * 0.56, v["note"], font(54), ACCENT)

def draw_table(d, v, W, H):
    center(d, H * 0.05, v["header"], font(60), ACCENT)
    f = font(58)
    y = H * 0.16
    xp, xt, xs = (0.28, 0.34, 0.66) if W > H else (0.08, 0.17, 0.82)
    for pos, team, pts, hl in v["rows"]:
        fill = ACCENT if hl else FG
        d.text((W * xp, y), f"{pos}.", font=f, fill=MUTED)
        d.text((W * xt, y), team, font=f, fill=fill)
        d.text((W * xs, y), str(pts), font=f, fill=fill)
        y += 92

DRAW = {"title": draw_title, "scores": draw_scores, "bignum": draw_bignum,
        "timeline": draw_timeline, "table": draw_table}

FPS = 30
PAUSE = 0.35  # seslendir.py'deki cümle sonu sessizliği

def stripes(W, H):
    """Arka plan: yavaşça kayan çapraz çizgiler (döngü için 2x genişlik)."""
    img = Image.new("RGB", (W * 2, H), BG)
    d = ImageDraw.Draw(img)
    for x in range(-H, W * 2 + H, 160):
        d.polygon([(x, 0), (x + 60, 0), (x + 60 - H, H), (x - H, H)], fill=(22, 25, 31))
    return img

def chunks(words, size):
    return [words[i:i + size] for i in range(0, len(words), size)]

def karaoke(d, words, idx, W, H):
    """Konuşulan kelime grubunu büyük yazar, o anki kelimeyi sarıyla vurgular."""
    f = font(70 if W > H else 78)
    gap = d.textlength(" ", font=f)
    widths = [d.textlength(w, font=f) for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    while total > W - 120 and f.size > 30:
        f = f.font_variant(size=f.size - 4)
        gap = d.textlength(" ", font=f)
        widths = [d.textlength(w, font=f) for w in words]
        total = sum(widths) + gap * (len(words) - 1)
    y = H - 210 if W > H else int(H * 0.6)
    x = (W - total) / 2
    for i, (w, ww) in enumerate(zip(words, widths)):
        d.text((x, y), w, font=f, fill=ACCENT if i == idx else FG, stroke_width=6, stroke_fill=(0, 0, 0))
        x += ww + gap

def word_times(sentence, dur, voiced):
    """Her kelimenin başlangıç zamanı; süre harf sayısına göre paylaştırılır."""
    words = sentence.split()
    speak = max(0.5, dur - (PAUSE if voiced else 0))
    weights = [len(w) + 2 for w in words]
    t, out = 0.0, []
    for w in weights:
        out.append(t); t += speak * w / sum(weights)
    return words, out

def ease(x): return 1 - (1 - min(1.0, max(0.0, x))) ** 3

def render(spec, durations, voiced, W, H, sink):
    bg = stripes(W, H)
    total = sum(durations)
    group = 4 if W > H else 3
    frame = 0
    for scene in spec["scenes"]:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        DRAW[scene["visual"]["type"]](ImageDraw.Draw(layer), scene["visual"], W, H)
        n0 = sum(len(s["say"]) for s in spec["scenes"][:spec["scenes"].index(scene)])
        sdur = sum(durations[n0:n0 + len(scene["say"])])
        # cümle -> (kelimeler, başlangıçlar) ve sahne içi başlangıç zamanı
        timeline, t0 = [], 0.0
        for k, sentence in enumerate(scene["say"]):
            words, starts = word_times(sentence, durations[n0 + k], voiced)
            timeline.append((t0, words, starts)); t0 += durations[n0 + k]
        scaled, last_z = layer, None
        for fi in range(int(round(sdur * FPS))):
            t = fi / FPS
            img = bg.crop(((frame * 2) % W, 0, (frame * 2) % W + W, H))
            z = round(1.0 + 0.05 * t / max(sdur, 0.1), 3)  # yavaş yakınlaşma
            if z != last_z:
                big = layer.resize((int(W * z), int(H * z)))
                ox, oy = (big.width - W) // 2, (big.height - H) // 2
                scaled, last_z = big.crop((ox, oy, ox + W, oy + H)), z
            a = ease(t / 0.35)  # giriş: aşağıdan kayarak belirme
            lay = scaled
            if a < 1:
                lay = scaled.copy()
                lay.putalpha(scaled.getchannel("A").point(lambda v: int(v * a)))
            img.paste(lay, (0, int(40 * (1 - a))), lay)
            d = ImageDraw.Draw(img)
            for st, words, starts in reversed(timeline):
                if t >= st:
                    rel = t - st
                    wi = max(i for i, s0 in enumerate(starts) if rel >= s0)
                    ci = wi // group
                    karaoke(d, chunks(words, group)[ci], wi - ci * group, W, H)
                    break
            d.rectangle((0, H - 8, int(W * (frame / FPS) / total), H), fill=ACCENT)  # ilerleme çubuğu
            sink.write(img.tobytes())
            frame += 1
    return frame

def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    W, H = spec.get("size", [1920, 1080])
    ses = os.path.join(out, "ses")
    dpath = os.path.join(ses, "durations.json")
    voiced = os.path.exists(dpath)  # seslendir.py çalıştıysa süreler sesten gelir
    sentences = [x for sc in spec["scenes"] for x in sc["say"]]
    durations = json.load(open(dpath)) if voiced else [max(1.8, len(x.split()) / WPS) for x in sentences]
    narration = [f'[{sc["name"]}]\n' + " ".join(sc["say"]) + "\n" for sc in spec["scenes"]]
    open(os.path.join(out, "seslendirme.txt"), "w").write("\n".join(narration))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if voiced:
        alst = os.path.join(out, "concat-ses.txt")
        open(alst, "w").write("".join(f"file '{os.path.abspath(os.path.join(ses, f'{i:03d}.wav'))}'\n"
                                      for i in range(len(sentences))))
        cmd += ["-f", "concat", "-safe", "0", "-i", alst, "-af", "loudnorm=I=-16:TP=-1.5",
                "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            os.path.join(out, "video.mp4")]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = render(spec, durations, voiced, W, H, p.stdin)
    p.stdin.close()
    if p.wait(): sys.exit("ffmpeg hata verdi")
    if voiced:  # CapCut'ta başka ses eklemek için sessiz kopya
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "video.mp4"),
                        "-an", "-c:v", "copy", os.path.join(out, "video-sessiz.mp4")], check=True)
    print(f"{frames} kare, {frames / FPS:.0f} sn, {'sesli' if voiced else 'sessiz'} -> {os.path.join(out, 'video.mp4')}")

if __name__ == "__main__":
    main()
