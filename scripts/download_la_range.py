# -*- coding: utf-8 -*-
"""
download_la_range.py —— 分段下载 LA zip (修复 CDN 断流损坏)
==========================================================
把 9.2GB 分成 50MB 段, 每段独立请求断点续传, 失败自动重试。
避免单次长连接被 CDN 静默断流导致数据错位。

用法: python -X utf8 scripts/download_la_range.py
"""
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LA = os.path.join(ROOT, "data", "raw", "la")
ZIP = os.path.join(LA, "Los-Angeles-MIDI-Dataset-Ver-4-0-CC-BY-NC-SA.zip")
URL = ("https://hf-mirror.com/datasets/projectlosangeles/Los-Angeles-MIDI-Dataset/"
       "resolve/main/Los-Angeles-MIDI-Dataset-Ver-4-0-CC-BY-NC-SA.zip")

TARGET = 9194218582
SEG = 50 * 1024 * 1024  # 50MB


def get_range(start, end):
    """下载 [start, end) 段, 失败重试 5 次。"""
    for attempt in range(6):
        r = subprocess.run(
            ["curl", "-sS", "-L", "--fail", "-r", f"{start}-{end - 1}",
             "-o", os.path.join(LA, f"seg_{start}.part"), URL],
            capture_output=True, timeout=120)
        sz = os.path.getsize(os.path.join(LA, f"seg_{start}.part")) if os.path.exists(
            os.path.join(LA, f"seg_{start}.part")) else 0
        if sz == end - start:
            return True
        time.sleep(3)
    return False


def main():
    os.makedirs(LA, exist_ok=True)
    # 已下载部分的段表 (从现有文件推断)
    have = os.path.getsize(ZIP) if os.path.exists(ZIP) else 0
    print(f"已有 {have / 1024 / 1024:.0f}MB (部分损坏, 已弃)")

    # 删掉坏 zip (损坏数据不能续)
    if os.path.exists(ZIP):
        print("删除损坏 zip ...")
        os.remove(ZIP)

    # 分段下 (第0段直接落到 zip, 让后续拼)
    n_seg = (TARGET + SEG - 1) // SEG
    print(f"共 {n_seg} 段, 每段 {SEG // 1024 // 1024}MB")
    fparts = []
    for i in range(n_seg):
        start = i * SEG
        end = min(start + SEG, TARGET)
        part = os.path.join(LA, f"seg_{start}.part")
        if os.path.exists(part) and os.path.getsize(part) == end - start:
            print(f"  [skip] 段 {i} ({start}-{end})")
            fparts.append(part)
            continue
        print(f"  [seg {i}] {start}-{end} ...")
        if get_range(start, end):
            fparts.append(part)
        else:
            print(f"  [FAIL] 段 {i} 重试仍失败")
            return

    # 合并
    print("合并 ...")
    with open(ZIP, "wb") as out:
        for p in fparts:
            with open(p, "rb") as f:
                out.write(f.read())
    os.remove(ZIP) if False else None
    print(f"完成: {os.path.getsize(ZIP)} 字节 (期望 {TARGET})")


if __name__ == "__main__":
    main()
