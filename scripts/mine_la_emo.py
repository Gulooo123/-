# -*- coding: utf-8 -*-
"""
mine_la_emo.py —— LA 快钻 emo 提速池
==================================
正是 GMD 缺 150-180bpm 的真人律动参考, LA 40万首必有快鼓轨。
这个脚本从 la_scan.csv 直接捞 tempo 150-180 的鼓轨(不二次解析, 用快速扫描结果),
先出候选清单, 再按 drum_notes 中位决定要不要完整解析(la_feature.py)。

用法 (LA 扫描完成后):
    python -X utf8 scripts/mine_la_emo.py [--tempo-min 150] [--tempo-max 180]
"""
import argparse
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "data", "la_scan.csv")
OUT = os.path.join(ROOT, "data", "la_emo_candidates.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tempo-min", type=float, default=150)
    ap.add_argument("--tempo-max", type=float, default=180)
    ap.add_argument("--drum-min", type=int, default=20, help="鼓音符最小(排除太简陋)")
    args = ap.parse_args()

    if not os.path.exists(SCAN):
        print(f"[skip] {SCAN} 不存在 (先跑 src/scan_library.py)")
        return

    rows = list(csv.DictReader(open(SCAN, encoding="utf-8")))
    sel = []
    for r in rows:
        try:
            tempo = float(r["tempo"])
            drum = int(r["drum_notes"])
        except (ValueError, KeyError):
            continue
        if args.tempo_min <= tempo <= args.tempo_max and drum >= args.drum_min:
            sel.append(r)
    # drum_notes 中位数附近的优先 (长演奏极值丢掉)
    if sel:
        dvals = sorted(int(r["drum_notes"]) for r in sel)
        med = dvals[len(dvals)//2]
        sel.sort(key=lambda r: abs(int(r["drum_notes"]) - med))
        print(f"emolane 150-180bpm 候选: {len(sel)} 首 (drum_notes≥{args.drum_min})")
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sel[0].keys()))
            w.writeheader()
            w.writerows(sel)
        print(f"-> {OUT}")
        print(f"前10: {[(r['tempo'], r['drum_notes']) for r in sel[:10]]}")
    else:
        print("无匹配")


if __name__ == "__main__":
    main()
