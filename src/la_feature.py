# -*- coding: utf-8 -*-
"""
la_feature.py —— LA 候选 → 完整 groove 特征 (两阶段扫的第二阶段)
===============================================================
从 merge_la_pool.py 筛出的 la_pool.csv 候选, 逐首完整解析提取:
  tempo / bars / 每小节 drum_notes (density) / 无切分 (简化)
输出: data/la_features.json, 供 retrieve.py 的 la: 源用 (替代目前的"猜特征")。

用法: python -X utf8 src/la_feature.py [--limit 2000]
"""
import argparse
import csv
import json
import os
import sys
import time

import mido

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LA_POOL = os.path.join(ROOT, "data", "la_pool.csv")
LA_MIDIS = os.path.join(ROOT, "data", "raw", "la", "MIDIs")
OUT = os.path.join(ROOT, "data", "la_features.json")

DRUM_CH = {9}


def extract(path):
    """完整解析单首, 返回特征 dict 或 None。"""
    try:
        mid = mido.MidiFile(path, clip=True)
    except Exception:
        return None
    tempo = 120.0
    drum_notes = 0
    total = 0
    last_beat = 0.0
    ppq = mid.ticks_per_beat or 480
    acc = 0.0
    for i, tr in enumerate(mid.tracks):
        for msg in tr:
            if msg.type == "set_tempo":
                tempo = 60.0 / (msg.tempo / 1e6)
            if msg.type == "note_on" and msg.velocity > 0:
                total += 1
                if msg.channel in DRUM_CH or i == 9:
                    drum_notes += 1
                    last_beat = max(last_beat, acc / ppq)
            acc += msg.time
    if drum_notes == 0 or last_beat < 1:
        return None
    n_bars = max(1, int(last_beat / 4) + 1)
    density = drum_notes / n_bars
    # 16格分布: kick/snare 位置 (第二遍累加 beat 保证精度)
    from collections import Counter
    pos16 = Counter()
    acc2 = 0.0
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "note_on" and msg.velocity > 0:
                if msg.channel in DRUM_CH or i == 9:
                    beat = acc2 / ppq
                    pos16[int(round(beat * 4)) % 16] += 1
            acc2 += msg.time
    return {
        "source": "la:" + os.path.relpath(path, LA_MIDIS).replace("\\", "/"),
        "tempo": round(tempo, 1),
        "bars": n_bars,
        "features": {
            "density": min(1.0, density / 15.0 * 0.9),
            "syncopation": 0.0,  # 简化,待增强
            "kick_density": 0.15,
            "snare_density": 0.30,
            "hihat_density": 0.30,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not os.path.exists(LA_POOL):
        print(f"[skip] 无 {LA_POOL}")
        return
    rows = list(csv.DictReader(open(LA_POOL, encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    print(f"解析 {len(rows)} 首 LA 候选 ...")
    t0 = time.time()
    out = []
    for i, r in enumerate(rows):
        if i % 500 == 0:
            print(f"  {i}/{len(rows)}")
        path = os.path.join(LA_MIDIS, r["path"])
        if not os.path.exists(path):
            continue
        try:
            f = extract(path)
            if f:
                out.append(f)
        except Exception:
            continue
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False)
    print(f"完成 {len(out)} 首, 用时 {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
