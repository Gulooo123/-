# -*- coding: utf-8 -*-
"""render_wav.py —— MIDI → WAV 快速渲染 (用 ffmpeg 自带 GM 音源)
用法: python -X utf8 scripts/render_wav.py [--src data/gen/demo_pack] [--dst data/gen/demo_wav]
"""
import argparse
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "data", "gen", "demo_pack"))
    ap.add_argument("--dst", default=os.path.join(ROOT, "data", "gen", "demo_wav"))
    args = ap.parse_args()
    os.makedirs(args.dst, exist_ok=True)
    for f in sorted(os.listdir(args.src)):
        if not f.endswith(".mid"):
            continue
        base = os.path.splitext(f)[0]
        out = os.path.join(args.dst, base + ".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i",
                        os.path.join(args.src, f), "-ar", "44100", out])
        print(f"  {base}.wav")


if __name__ == "__main__":
    main()
