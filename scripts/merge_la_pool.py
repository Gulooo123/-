# -*- coding: utf-8 -*-
"""
merge_la_pool.py —— 将 LA 内容扫描结果并入双库检索
================================================
扫描完成后运行。从 data/la_scan.csv 挑出"摇滚架构"候选:
  - 有鼓轨 / 4/4 / 120-180bpm / 密度区间合理
并把选出的候选打进 data/grooves.json? 不——
更稳: 单独建 data/la_grooves.json + data/la_pool.csv, retrieve.py 默认双库。

筛选规则 (v1 保守):
  density_per_bar 10-70 (太稀=不是鼓作, 太密=噪音)
  tempo 100-200
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "data", "la_scan.csv")
OUT_CSV = os.path.join(ROOT, "data", "la_pool.csv")
OUT_JSON = os.path.join(ROOT, "data", "la_grooves.json")

TEMPO_MIN, TEMPO_MAX = 100.0, 200.0
DENS_MIN, DENS_MAX = 10.0, 70.0


def main():
    rows = list(csv.DictReader(open(SCAN, encoding="utf-8")))
    print(f"扫描结果 {len(rows)} 行")
    sel = []
    for r in rows:
        try:
            tempo = float(r["tempo"])
            dens = float(r["density_per_bar"])
        except (ValueError, KeyError):
            continue
        if TEMPO_MIN <= tempo <= TEMPO_MAX and DENS_MIN <= dens <= DENS_MAX:
            sel.append(r)
    print(f"筛选出 {len(sel)} 首 (tempo {TEMPO_MIN}-{TEMPO_MAX}, dens {DENS_MIN}-{DENS_MAX})")

    if sel:
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sel[0].keys()))
            w.writeheader()
            w.writerows(sel)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(sel, f, ensure_ascii=False)
        print(f"-> {OUT_CSV}")
        print(f"-> {OUT_JSON}")


if __name__ == "__main__":
    main()
