# -*- coding: utf-8 -*-
"""
scan_library.py —— LA 全集快速扫描器 (mido 版)
===========================================
只提取: 有无鼓轨 / tempo / 鼓轨音符数 / 总小节估计。
不要完整特征——LA 只是候选池预筛, 选中的进完整解析。

速度: mido 底层解析, 40万首约 10-15 分钟。

输出: data/la_scan.csv
"""
import csv
import os
import sys
import time

import mido

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LA_DIR = os.path.join(ROOT, "data", "raw", "la", "MIDIs")
OUT = os.path.join(ROOT, "data", "la_scan.csv")

# 鼓音高 (GM 标准)
DRUM_PITCHES = {36, 35, 38, 40, 42, 44, 46, 51, 59, 49, 57, 41, 43, 45, 47, 48, 50}


def scan_one(path):
    """返回 tuple 行或 None。"""
    try:
        mid = mido.MidiFile(path, clip=True)
    except Exception:
        return None
    if mid.type != 1 and mid.type != 0:
        return None
    tempo = 120.0
    drum_notes = 0
    total_notes = 0
    last_beat = 0.0  # 用最后一个鼓 note 的绝对拍数估计时长
    drum_present = False
    is_drum_ch = {9}  # 默认 10 号通道为鼓
    ppq = mid.ticks_per_beat or 480
    abs_ticks = 0.0
    for i, tr in enumerate(mid.tracks):
        ch_is_drum = (i == 9)
        for msg in tr:
            if msg.type == 'set_tempo':
                # msg.tempo = 每拍微秒 (mido), bpm = 60 / (us/1e6)
                tempo = 60.0 / (msg.tempo / 1e6)
            if msg.type == 'note_on' and msg.velocity > 0:
                total_notes += 1
                if msg.channel in is_drum_ch or ch_is_drum:
                    drum_notes += 1
                    drum_present = True
                    last_beat = max(last_beat, abs_ticks / ppq)
            abs_ticks += msg.time
    if not drum_present or drum_notes == 0 or last_beat < 1:
        return None
    if not (30 <= tempo <= 300):
        return None
    # 每小节鼓音符数 (密度指标, 应对长短文件的公平性)
    n_bars = max(1, int(last_beat / 4) + 1)
    density = drum_notes / n_bars
    row = {
        "path": os.path.relpath(path, LA_DIR).replace("\\", "/"),
        "tempo": round(tempo, 1),
        "drum_notes": drum_notes,
        "total_notes": total_notes,
        "n_bars": n_bars,
        "density_per_bar": round(density, 2),
    }
    return row


def main(limit=0, out=OUT):
    files = []
    for root, _, names in os.walk(LA_DIR):
        for n in names:
            if n.endswith(".mid") or n.endswith(".midi"):
                files.append(os.path.join(root, n))
    files.sort()
    if limit:
        files = files[:limit]
    print(f"扫描 {len(files)} 个文件 (mido 快速版) ...")
    t0 = time.time()
    rows = []
    for i, f in enumerate(files):
        if i % 20000 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(files)}  (+{len(rows)} 合格) {el:.0f}s")
        r = scan_one(f)
        if r:
            rows.append(r)
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"完成: 合格 {len(rows)}, 用时 {time.time()-t0:.0f}s -> {out}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(limit=limit)
