# -*- coding: utf-8 -*-
"""
下载并整理 Groove MIDI Dataset (GMD) —— 数据源第一条链路
====================================================
来源页面: https://magenta.tensorflow.org/datasets/groove
许可: CC BY 4.0 (见 data/raw/gmd_midionly/groove/LICENSE)
下载源: https://storage.googleapis.com/magentadata/datasets/groove/groove-v1.0.0-midionly.zip

做什么:
1. 下载 midionly 版 zip (~3.3MB, 1150 个真人鼓 MIDI + info.csv)
2. 解压到 data/raw/gmd_midionly/
3. 按 emo 亲缘 style (rock/punk/pop/indie/halftime/prog/folk/breakbeat)
   筛选出 data/emo_pool/ (约 448 首) 并生成 data/emo_pool_index.csv

用法: python scripts/download_gmd.py
"""
import csv
import os
import shutil
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://storage.googleapis.com/magentadata/datasets/groove/groove-v1.0.0-midionly.zip"
RAWDIR = os.path.join(ROOT, "data", "raw")
ZIP = os.path.join(RAWDIR, "groove-v1.0.0-midionly.zip")
GMD = os.path.join(RAWDIR, "gmd_midionly", "groove")
POOL = os.path.join(ROOT, "data", "emo_pool")
INDEX = os.path.join(ROOT, "data", "emo_pool_index.csv")

# emo 亲缘风格关键词 (GMD 里没有真正的 emo, 从 rock/punk/pop 迁移)
EMO_KEYWORDS = ["rock", "punk", "pop", "indie", "halftime", "prog", "folk", "breakbeat"]


def download():
    os.makedirs(RAWDIR, exist_ok=True)
    if os.path.exists(ZIP) and os.path.getsize(ZIP) > 3_000_000:
        print(f"[skip] zip 已存在: {ZIP}")
        return
    print(f"[download] {BASE}")
    # curl 直连 (storage.googleapis.com 国内直连可用; 若失败可加 -x 代理)
    cmd = ["curl", "-sS", "-L", "-m", "300", "-o", ZIP, BASE]
    subprocess.run(cmd, check=True)


def extract():
    if os.path.isdir(GMD) and os.path.exists(os.path.join(GMD, "info.csv")):
        print("[skip] 已解压")
        return
    os.makedirs(os.path.dirname(GMD), exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    ok = skip = 0
    for name in z.namelist():
        if name.endswith("/"):
            continue
        target = os.path.join(os.path.dirname(GMD), name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            ok += 1
        except OSError:
            skip += 1  # Windows zip 罕见先例: 文件名带 \r
    print(f"[extract] {ok} 个文件, 跳过 {skip} 个")
    # 清理文件名尾部 \r
    for root, _, files in os.walk(os.path.dirname(GMD)):
        for f in files:
            if f.endswith("\r"):
                os.rename(os.path.join(root, f), os.path.join(root, f.rstrip("\r")))


def build_pool():
    rows = list(csv.DictReader(open(os.path.join(GMD, "info.csv"), encoding="utf-8")))
    sel = [r for r in rows if any(k in r["style"].lower() for k in EMO_KEYWORDS)]
    os.makedirs(POOL, exist_ok=True)
    n = 0
    out = []
    for r in sel:
        src = os.path.join(GMD, r["midi_filename"])
        if os.path.exists(src):
            flat = r["midi_filename"].replace("/", "__")
            dst = os.path.join(POOL, flat)
            if not os.path.exists(dst):
                shutil.copy(src, dst)
            n += 1
            out.append({
                "id": r["id"], "style": r["style"], "bpm": r["bpm"],
                "beat_type": r["beat_type"], "timesig": r["time_signature"],
                "split": r["split"], "duration": r["duration"],
                "midi": "data/emo_pool/" + flat,
            })
    with open(INDEX, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"[pool] {n} 首 -> {POOL}")
    print(f"[index] {len(out)} 条 -> {INDEX}")


if __name__ == "__main__":
    download()
    extract()
    build_pool()
