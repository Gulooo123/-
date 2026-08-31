# -*- coding: utf-8 -*-
"""
scan_incremental.py —— 增量扫描 LA 全集 (跳过已入 CSV 的)
========================================================
读取现有 data/la_scan.csv 的 path 集, 只扫全库里不在其中的,
结果写入 data/la_scan_batch2.csv (与 merge_scan_results.py 配合)。

用法: python -X utf8 scripts/scan_incremental.py [--workers 8]
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDIS = os.path.join(ROOT, "data", "raw", "la", "MIDIs")
CSV1 = os.path.join(ROOT, "data", "la_scan.csv")
CSV2 = os.path.join(ROOT, "data", "la_scan_batch2.csv")

sys.path.insert(0, os.path.join(ROOT, "src"))
import scan_library as sl


def scan_chunk(chunk):
    rows = []
    for p in chunk:
        try:
            r = sl.scan_one(p)
            if r:
                rows.append(r)
        except Exception:
            continue
    return rows


def main(workers=8):
    known = set()
    if os.path.exists(CSV1):
        for r in csv.DictReader(open(CSV1, encoding="utf-8")):
            known.add(r["path"])
    print(f"已知 {len(known)} 首")

    new_files = []
    for d in sorted(os.listdir(MIDIS)):
        dpath = os.path.join(MIDIS, d)
        if not os.path.isdir(dpath):
            continue
        for f in os.listdir(dpath):
            rel = f"{d}/{f}"
            if rel not in known:
                new_files.append(os.path.join(dpath, f))
    print(f"新增待扫: {len(new_files)} 首, {workers} 进程")

    t0 = time.time()
    chunks = [new_files[i::workers] for i in range(workers)]
    # 线程化 map 完成
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(scan_chunk, c) for c in chunks]
        total = []
        for f in as_completed(futs):
            try:
                total += f.result()
            except Exception:
                continue
            print(f"  +{len(total)} 合格 ({time.time()-t0:.0f}s)")

    if total:
        with open(CSV2, "w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=list(total[0].keys()))
            w.writeheader()
            w.writerows(total)
        print(f"完成 {len(total)} -> {CSV2}")
    else:
        print("无合格")


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    main(workers=w)
