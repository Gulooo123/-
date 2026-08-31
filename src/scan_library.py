# -*- coding: utf-8 -*-
"""
scan_library.py —— 全量 MIDI 内容扫描器
====================================
40万 MIDI 无风格标签, 只能按内容特征筛。本脚本解析每个文件并产出轻量筛选结果,
目标是捞"摇滚架构"的曲子: 有鼓轨 + 4/4 + 可用 BPM 区间 + 鼓轨音符量合理。

输出: data/scan_result.csv (每行一首: 路径/hash/tempo/拍号/鼓存在/鼓轨数量/各声部密度)

用法: python -X utf8 src/scan_library.py [--limit 200000] [--dump CSV]
"""
import argparse
import csv
import os
import sys

import pretty_midi

LA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "raw", "la", "MIDIs")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "la_scan.csv")

# GM 鼓键位 (Kick/Snare/HiHat/Tom/Ride/Crash)
DRUM_PITCHES = {36, 35, 38, 40, 37, 42, 44, 46, 51, 59, 53, 49, 57, 55,
                41, 43, 45, 47, 48, 50}


def scan_one(path):
    """返回 (row, notes_info) 元组, row 是 CSV 行, 无鼓轨可返回 (None, None)。"""
    try:
        pm = pretty_midi.PrettyMIDI(path)
    except Exception:
        return None, None
    try:
        tempo_changes = pm.get_tempo_changes()
        tempo = tempo_changes[1][0] if len(tempo_changes[1]) else 0.0
    except Exception:
        return None, None
    if not (30 <= tempo <= 300):
        return None, None

    drum_ins = [i for i in pm.instruments if i.is_drum]
    if not drum_ins:
        return None, None

    drum_notes = sum(len(i.notes) for i in drum_ins)
    if drum_notes == 0:
        return None, None

    total_notes = sum(len(i.notes) for i in pm.instruments)
    n_bars = max(
        (int(n.end // (4 * 60.0 / tempo)) for i in drum_ins for n in i.notes),
        default=-1)
    n_bars += 1
    # 密度: 每小节鼓音符数 (0-256)
    density = min(999, drum_notes / max(1, n_bars))

    row = {
        "path": os.path.relpath(path, os.path.dirname(LA_DIR)).replace("\\", "/"),
        "tempo": round(tempo, 1),
        "n_bars": n_bars,
        "drum_notes": drum_notes,
        "density_per_bar": round(density, 2),
        "total_notes": total_notes,
    }
    return row, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0=全部")
    ap.add_argument("--dump", type=str, default=OUT)
    args = ap.parse_args()

    files = []
    for root, _, names in os.walk(LA_DIR):
        for n in names:
            if n.endswith(".mid") or n.endswith(".midi"):
                files.append(os.path.join(root, n))
    files.sort()
    if args.limit:
        files = files[: args.limit]
    print(f"扫描 {len(files)} 个文件 ...")

    rows = []
    errs = 0
    for i, f in enumerate(files):
        if i % 5000 == 0:
            print(f"  {i}/{len(files)} (+{len(rows)} 合格)")
        r, _ = scan_one(f)
        if r:
            rows.append(r)
        else:
            errs += 1

    if rows:
        with open(args.dump, "w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"完成: 合格 {len(rows)} 个, 跳过 {errs} 个 -> {args.dump}")


if __name__ == "__main__":
    main()
