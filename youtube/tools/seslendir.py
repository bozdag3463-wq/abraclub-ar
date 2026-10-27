#!/usr/bin/env python3
"""seslendir.py - bir video spec'indeki her cümleyi Türkçe sese çevirir (çevrimdışı, sherpa-onnx).

    python seslendir.py spec.json out_dir model_dir

model_dir: sherpa-onnx piper modeli, ör. vits-piper-tr_TR-fahrettin-medium
(github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models). sherpa-onnx 1.13.x gerekir;
2.x sürümünde gömülü espeak-ng yok.

Çıktı: out_dir/ses/NNN.wav (cümle başına) ve out_dir/ses/durations.json.
make_video.py bu dosyaları görürse kare sürelerini sese göre ayarlar ve sesi videoya ekler.
"""
import json, os, re, sys
import numpy as np, sherpa_onnx, soundfile as sf

PAUSE = 0.35  # cümleler arası sessizlik (sn)

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
ORD = {"bir": "birinci", "iki": "ikinci", "üç": "üçüncü", "dört": "dördüncü", "beş": "beşinci",
       "altı": "altıncı", "yedi": "yedinci", "sekiz": "sekizinci", "dokuz": "dokuzuncu",
       "on": "onuncu", "yirmi": "yirminci", "otuz": "otuzuncu", "kırk": "kırkıncı",
       "elli": "ellinci", "altmış": "altmışıncı", "yetmiş": "yetmişinci", "seksen": "sekseninci",
       "doksan": "doksanıncı", "yüz": "yüzüncü", "sıfır": "sıfırıncı"}
SPELL = {"PSG": "Pe Se Ge", "VAR": "Var"}

def num(n):
    n = int(n)
    if n == 0: return "sıfır"
    out = []
    if n >= 100:
        h = n // 100
        out.append(("" if h == 1 else ONES[h] + " ") + "yüz"); n %= 100
    if n >= 10: out.append(TENS[n // 10]); n %= 10
    if n: out.append(ONES[n])
    return " ".join(out)

def ordinal(n):
    w = num(n).split()
    w[-1] = ORD[w[-1]]
    return " ".join(w)

def normalize(t):
    for k, v in SPELL.items(): t = re.sub(rf"\b{k}\b", v, t)
    t = re.sub(r"(\d+)-(\d+)", lambda m: f"{num(m[1])} {num(m[2])}", t)        # skor: 2-0
    t = re.sub(r"(\d+)\.(?=\s+[a-zçğıöşü])", lambda m: ordinal(m[1]), t)       # 29. dakika
    t = re.sub(r"(\d+)'(\w+)", lambda m: num(m[1]) + m[2], t)                   # 2'den
    t = re.sub(r"\d+", lambda m: num(m[0]), t)
    return t

def main():
    spec, out, d = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
    name = os.path.basename(d).replace("vits-piper-", "")
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{d}/{name}.onnx", tokens=f"{d}/tokens.txt",
                                                   data_dir=f"{d}/espeak-ng-data"),
        num_threads=4)))
    sd = os.path.join(out, "ses"); os.makedirs(sd, exist_ok=True)
    durations, n = [], 0
    for scene in json.load(open(spec))["scenes"]:
        for sentence in scene["say"]:
            a = tts.generate(normalize(sentence), sid=0, speed=1.05)
            s = np.asarray(a.samples, dtype=np.float32)
            s = s / max(1e-6, float(np.abs(s).max())) * 0.8  # tepe seviyesini eşitle
            s = np.concatenate([s, np.zeros(int(a.sample_rate * PAUSE), dtype=np.float32)])
            sf.write(os.path.join(sd, f"{n:03d}.wav"), s, a.sample_rate)
            durations.append(round(len(s) / a.sample_rate, 3)); n += 1
    json.dump(durations, open(os.path.join(sd, "durations.json"), "w"))
    print(f"{n} cümle, {sum(durations):.0f} sn ses -> {sd}")

if __name__ == "__main__":
    main()
