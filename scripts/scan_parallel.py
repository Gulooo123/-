# -*- coding: utf-8 -*-
"""
scan_parallel.py —— 并行扫描已解压 LA 目录 (16 目录 × 4 进程)
============================================================
scan_library 单进程 31s/1000 → 24.5 万首约 2h 太慢。
并行版: 每个目录一个 worker, 结果聚合进 CSV。
用法: python -X utf8 scripts/scan_parallel.py
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDIS = os.path.join(ROOT, "data", "raw", "la", "MIDIs")
OUT = os.path.join(ROOT, "data", "la_scan.csv")

sys.path.insert(0, os.path.join(ROOT, "src"))
import scan_library as sl


def scan_chunk(args):
    """worker: 解析一个文件列表 chunk。"""
    chunk, = args
    rows = []
    for p in chunk:
        try:
            r = sl.scan_one(p)
            if r:
                rows.append(r)
        except Exception:
            continue
    return rows


def main():
    dirs = [d for d in sorted(os.listdir(MIDIS)) if os.path.isdir(os.path.join(MIDIS, d))]
    # 汇总所有文件路径, 切成 8 个 chunk (进程池并行)
    all_files = []
    for d in dirs:
        dpath = os.path.join(MIDIS, d)
        all_files += [os.path.join(dpath, f) for f in os.listdir(dpath)]
    n = len(all_files)
    k = 8
    chunks = [all_files[i::k] for i in range(k)]  # 交错切, 均匀
    print(f"{n} 文件 → {k} 进程并行 ...")
    t0 = time.time()
    total_rows = []
    with ProcessPoolExecutor(max_workers=k) as ex:
        futs = [ex.submit(scan_chunk, (c,)) for c in chunks]
        for f in as_completed(futs):
            try:
                total_rows += f.result()
                print(f"  +{len(total_rows)} 合格 ({time.time()-t0:.0f}s)")
            except Exception:
                continue
    rows = total_rows
    if not rows:
        print("无合格")
        return
    with open(OUT, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"完成: {len(rows)} 合格, 用时 {time.time()-t0:.0f}s -> {OUT}")
    # 汇总 tempo 覆盖 (验证 150-180 是否有)
    from collections import Counter
    b = Counter(int(float(r["tempo"]) // 10 * 10) for r in rows)
    print("tempo 分布:", dict(sorted(b.items())))


if __name__ == "__main__":
    main()
