#!/usr/bin/env python3
"""make_video.py - bir video spec'inden (JSON) sessiz, altyazılı MP4 üretir.

    python3 make_video.py spec.json out_dir

Her sahne bir görsel (title, scores, bignum, timeline, table) ve seslendirme cümlelerinden oluşur.
Her cümle altyazı olarak ekrana gelir; süresi kelime sayısından hesaplanır (dakikada 150 kelime).
Çıktı: video.mp4 (sessiz), seslendirme.txt (TTS'e yapıştırılacak metin), kareler/ (PNG'ler).
"""
import json, os, subprocess, sys, textwrap
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

def subtitle(d, text, W, H):
    f = font(46)
    lines = textwrap.wrap(text, width=48 if W > H else 24)
    lh = 62
    top = H - 40 - lh * len(lines) - 30
    if H > W:  # Shorts: alt kısmı YouTube arayüzü kapatıyor
        top = int(H * 0.58)
    d.rectangle((0, top - 10, W, top + lh * len(lines) + 30), fill=(0, 0, 0))
    for i, line in enumerate(lines):
        center(d, top + 10 + i * lh, line, f)

def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    frames = os.path.join(out, "kareler")
    os.makedirs(frames, exist_ok=True)
    W, H = spec.get("size", [1920, 1080])
    ses = os.path.join(out, "ses")
    dpath = os.path.join(ses, "durations.json")
    voiced = os.path.exists(dpath)  # seslendir.py çalıştıysa süreler sesten gelir
    durations = json.load(open(dpath)) if voiced else None
    concat, narration, n, total = [], [], 0, 0.0
    for scene in spec["scenes"]:
        narration.append(f'[{scene["name"]}]\n' + " ".join(scene["say"]) + "\n")
        for sentence in scene["say"]:
            img = Image.new("RGB", (W, H), BG)
            d = ImageDraw.Draw(img)
            DRAW[scene["visual"]["type"]](d, scene["visual"], W, H)
            subtitle(d, sentence, W, H)
            path = os.path.join(frames, f"{n:03d}.png")
            img.save(path)
            dur = durations[n] if voiced else max(1.8, len(sentence.split()) / WPS)
            concat.append(f"file '{os.path.abspath(path)}'\nduration {dur:.2f}")
            n += 1; total += dur
    concat.append(f"file '{os.path.abspath(path)}'")  # ffmpeg concat: son kare tekrar
    lst = os.path.join(out, "concat.txt")
    open(lst, "w").write("\n".join(concat) + "\n")
    open(os.path.join(out, "seslendirme.txt"), "w").write("\n".join(narration))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if voiced:
        alst = os.path.join(out, "concat-ses.txt")
        open(alst, "w").write("".join(f"file '{os.path.abspath(os.path.join(ses, f'{i:03d}.wav'))}'\n"
                                      for i in range(n)))
        cmd += ["-f", "concat", "-safe", "0", "-i", alst, "-af", "loudnorm=I=-16:TP=-1.5",
                "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            os.path.join(out, "video.mp4")]
    subprocess.run(cmd, check=True)
    print(f"{n} kare, {total:.0f} sn, {'sesli' if voiced else 'sessiz'} -> {os.path.join(out, 'video.mp4')}")

if __name__ == "__main__":
    main()
