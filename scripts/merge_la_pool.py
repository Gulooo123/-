# -*- coding: utf-8 -*-
"""
merge_la_pool.py —— LA 内容扫描 → 候选池筛选
==========================================
从 data/la_scan.csv 筛出"鼓轨合理"的候选:
  tempo 100-200 (emo/riff 常用区间)
  density_per_bar 5-30  (GMD 真人基准: 每小节 10-15 音符)

保留 drum_notes 总量作为二级排序 (长文件也不会误杀).

用法: python -X utf8 scripts/merge_la_pool.py
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "data", "la_scan.csv")
OUT_CSV = os.path.join(ROOT, "data", "la_pool.csv")
OUT_JSON = os.path.join(ROOT, "data", "la_grooves.json")

TEMPO_MIN, TEMPO_MAX = 100.0, 200.0
DENS_MIN, DENS_MAX = 5.0, 30.0  # 每小节鼓音符数 (GMD 真人中位 10.8)


def main():
    if not os.path.exists(SCAN):
        print(f"[skip] 扫描结果不存在: {SCAN} (先跑 src/scan_library.py)")
        return
    rows = list(csv.DictReader(open(SCAN, encoding="utf-8")))
    print(f"扫描: {len(rows)} 行")
    sel = []
    for r in rows:
        try:
            tempo = float(r["tempo"])
            dens = float(r["density_per_bar"])
        except (ValueError, KeyError):
            continue
        if TEMPO_MIN <= tempo <= TEMPO_MAX and DENS_MIN <= dens <= DENS_MAX:
            sel.append(r)
    # 二级排序: drum_notes 多的长文件排后 (避免超长表演片段)
    sel.sort(key=lambda r: float(r.get("drum_notes", 1e12)))
    print(f"筛选: {len(sel)} 首 (tempo {TEMPO_MIN}-{TEMPO_MAX}, 每小节 {DENS_MIN}-{DENS_MAX} 鼓音符)")

    if sel:
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sel[0].keys()))
            w.writeheader()
            w.writerows(sel)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(sel, f, ensure_ascii=False)
        print(f"-> {OUT_CSV} ({os.path.getsize(OUT_CSV)//1024}KB)")
        print(f"-> {OUT_JSON}")


if __name__ == "__main__":
    main()
