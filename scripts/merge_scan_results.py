# -*- coding: utf-8 -*-
"""
merge_scan_results.py —— 合并新旧两批扫描结果 (解压补全后增量扫)
================================================================
流程:
 1. 24.5 万好文件已解压 → 并行扫描得 la_scan.csv (第一批)
 2. 分段下载重下 zip 后 → 解压补齐 → 再扫增量得 la_scan_batch2.csv
 3. 本脚本合并两批 → la_scan.csv 最终完整版

用法: python -X utf8 scripts/merge_scan_results.py
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B1 = os.path.join(ROOT, "data", "la_scan.csv")
B2 = os.path.join(ROOT, "data", "la_scan_batch2.csv")
OUT = os.path.join(ROOT, "data", "la_scan_final.csv")


def main():
    fields = None
    all_rows = []
    for b in [B1, B2]:
        if os.path.exists(b):
            rows = list(csv.DictReader(open(b, encoding="utf-8")))
            fields = fields or list(rows[0].keys())
            all_rows += rows
            print(f"{b}: {len(rows)} 行")
    if not all_rows:
        print("无可用批次")
        return
    # 去重 (按 path)
    seen = set()
    uniq = []
    for r in all_rows:
        if r["path"] in seen:
            continue
        seen.add(r["path"])
        uniq.append(r)
    with open(OUT, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=fields or list(uniq[0].keys()))
        w.writeheader()
        w.writerows(uniq)
    print(f"合并完成: {len(uniq)} 条 (去重后) -> {OUT}")


if __name__ == "__main__":
    main()
