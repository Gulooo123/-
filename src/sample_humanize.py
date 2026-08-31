# -*- coding: utf-8 -*-
"""
sample_humanize.py —— 从真人 groove 采样 velocity/时间分布 (文档第5节)
====================================================================
原理: 机械=全一样, 真人=每个 hit 的 velocity/时间有自然分布。GMD 里已是真人演奏,
所以最聪明的 humanize 不是随机抖动, 而是从真实数据里采样统计特性(均值/方差), 再应用到生成。

用法:
    python -X utf8 src/sample_humanize.py --style punk --bpm 144 --count 4
"""
import argparse
import json
import os
import random
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROOVES = os.path.join(ROOT, "data", "grooves.json")


def load():
    return json.load(open(GROOVES, encoding="utf-8"))


def collect(grooves, style=None, bpm=None):
    """收集某风格的 velocity 统计。"""
    gs = grooves
    if style:
        gs = [g for g in gs if style.lower() in g["source"].lower()]
    if bpm:
        gs = [g for g in gs if abs(g["tempo"] - bpm) < 25]
    vels = []
    offs = []
    for g in gs:
        for part, hits in g["parts"].items():
            for h in hits[:40]:  # 每首取一部分, 防超密
                vels.append(h["vel"])
                if h["pos"] - round(h["pos"]) != 0:
                    # 切分 hit: 相对网格的偏移 = 律动错位
                    offs.append(round(h["pos"] - round(h["pos"]), 3))
    if not vels:
        return None
    return {
        "n0": len(gs),
        "vel_stdev": statistics.pstdev(vels),
        "vel_mean": statistics.mean(vels),
        "off_stdev": statistics.pstdev(offs) if offs else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", type=str, default="", help="风格过滤")
    ap.add_argument("--bpm", type=float, default=0, help="bpm 相近过滤")
    args = ap.parse_args()

    # 全库统计 + 分风格统计
    print("=== 全库真人 velocity 统计 ===")
    info = collect(load())
    if info:
        print(f"  来源 {info['n0']} 首 | vel 均值 {info['vel_mean']:.1f} 波动 {info['vel_stdev']:.1f} | 切分偏移波动 {info['off_stdev']:.3f}")

    if args.style or args.bpm:
        print(f"=== 过滤: style={args.style or '*'} bpm={args.bpm or '*'} ===")
        info = collect(load(), args.style, args.bpm or None)
        if info:
            print(f"  来源 {info['n0']} 首 | vel 均值 {info['vel_mean']:.1f} 波动 {info['vel_stdev']:.1f}")
            print(f"  => 建议 humanize 速度抖动用 ±{info['vel_stdev']:.0f} (真人方差)")
            print(f"  => 建议 humanize 时间抖动用 ±{info['off_stdev']*1000*60/ (args.bpm or 145):.1f} ms 量级")
        else:
            print("  无匹配")


if __name__ == "__main__":
    main()
