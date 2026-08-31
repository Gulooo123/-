# -*- coding: utf-8 -*-
"""
setup_la.py —— LA 全集解压 + 扫描 + 合并 (全自动)
===============================================
下载完成后运行:
  1. 解压 data/raw/la/*.zip → data/raw/la/MIDIs/ (40万 MIDI)
  2. 运行 src/scan_library.py 内容扫描 → data/la_scan.csv (mido 快速版, ~11分钟)
  3. 运行 scripts/merge_la_pool.py → data/la_pool.csv (候选池)

用法: python -X utf8 scripts/setup_la.py
"""
import os
import subprocess
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LA = os.path.join(ROOT, "data", "raw", "la")
ZIP = os.path.join(LA, "Los-Angeles-MIDI-Dataset-Ver-4-0-CC-BY-NC-SA.zip")
MIDIS_DIR = os.path.join(LA, "MIDIs")

EXPECT = 9194218582  # 完整 zip 大小 (中央目录确认过)

TARGET_DIRS = ["MIDIs", "META_DATA"]  # 我们只需要这两个


def unzip():
    if os.path.isdir(MIDIS_DIR):
        n = sum(1 for _, _, fs in os.walk(MIDIS_DIR) for _ in fs)
        if n > 400_000:
            print(f"[skip] 已解压 ({n} 文件)")
            return
    print(f"[unzip] 解压 {ZIP} ... (约 5-15 分钟, 40万小文件)")
    t0 = time.time()
    z = zipfile.ZipFile(ZIP)
    for m in z.infolist():
        # 只解我们需要的顶层目录 (跳过 Artwork/SOUNDFONT/CHORDS 等)
        top = m.filename.split("/", 1)[0]
        for target in TARGET_DIRS:
            if m.filename.startswith(target):
                z.extract(m, LA)
                break
    print(f"[unzip] 完成, 用时 {time.time()-t0:.0f}s")
    n = sum(1 for _, _, fs in os.walk(MIDIS_DIR) for _ in fs)
    print(f"  MIDIs: {n} 文件")


def scan():
    scan_py = os.path.join(ROOT, "src", "scan_library.py")
    print("[scan] 运行内容扫描器 ...")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.run([sys.executable, "-X", "utf8", scan_py], env=env, cwd=ROOT)


def merge():
    merge_py = os.path.join(ROOT, "scripts", "merge_la_pool.py")
    print("[merge] 筛选候选池 ...")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.run([sys.executable, "-X", "utf8", merge_py], env=env, cwd=ROOT)


if __name__ == "__main__":
    if not os.path.exists(ZIP):
        print("zip 不存在, 先下载（见 README / data/raw/la/）")
        sys.exit(1)
    sz = os.path.getsize(ZIP)
    if sz < EXPECT:
        print(f"zip 不完整: {sz} / {EXPECT} 字节, 先续传下载")
        sys.exit(1)
    unzip()
    scan()
    merge()
    print("=== LA 数据链路全部完成 ===")
