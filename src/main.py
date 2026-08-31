# -*- coding: utf-8 -*-
"""
main.py —— 写鼓小助手 CLI 主入口
===============================
把 解析/检索/生成 串成一条命令。

用法:
    # 看库统计
    python -X utf8 src/main.py info

    # 检索相似律动 (168bpm 切分型)
    python -X utf8 src/main.py search --bpm 168 --density 0.6 --sync 0.5 --count 6

    # 生成 (用真人律动采样)
    python -X utf8 src/main.py gen --riff "X...X.......X..." --bpm 167 --bars 4 --out data/gen/cli1.mid

    # 真人统计参考
    python -X utf8 src/main.py stats --style punk
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import groove
import groove_gen
import retrieve
import sample_humanize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_DIR = os.path.join(ROOT, "data", "gen")


def cmd_info(args):
    gs = groove_gen.load_grooves()
    print(f"GMD 真人 groove: {len(gs)} 首")
    print(f"LA 池: {len(retrieve.load_la())} 首 (待 LA 扫描后启用)")
    print(f"生成目录: {GEN_DIR}")


def cmd_search(args):
    tv = [min(1.0, abs(args.bpm - 150) / 200), args.density, args.sync, 0.15, 0.10, 0.30]
    print(f"=== 检索 (bpm≈{args.bpm}, style={args.style or 'any'}) ===")
    for d, g in retrieve.retrieve(tv, args.count, prefer_beat=True, style=args.style,
                                  sources=tuple(args.sources.split(",")),
                                  target_tempo=args.bpm):
        print(f"  {d:.3f}  {retrieve.fmt(g)}")


def cmd_gen(args):
    grooves = groove_gen.load_grooves()
    ref = groove_gen.pick_reference(grooves, args.bpm, args.style)
    print(f"参考: {ref['n_used']} 首真人 groove 聚合 (tempo≈{ref['tempo']:.0f}bpm)")
    import random
    rng = random.Random(args.seed)
    bars = groove_gen.parse_riff(args.riff.replace("/", "\n"))
    if args.bars and args.bars > len(bars):
        n_in = len(bars)
        bars = [bars[i % n_in] for i in range(args.bars)]
    drum = groove_gen.sample_hits(ref["parts"], rng, bars)
    out = groove_gen.write_midi(drum, args.bpm, args.out, args.humanize, rng)
    print(f"生成 -> {out}")


def cmd_stats(args):
    sh = sample_humanize
    info = sh.collect(sh.load(), args.style or None, args.bpm or None)
    if info:
        print(f"style={args.style or '*'} bpm={args.bpm or '*'} | 来源 {info['n0']} 首")
        print(f"  vel 均值 {info['vel_mean']:.1f} 波动 {info['vel_stdev']:.1f}")
        print(f"  切分偏移波动 {info['off_stdev']:.3f}")


def main():
    ap = argparse.ArgumentParser(prog="drum-helper")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("info"); p.set_defaults(fn=cmd_info)

    p = sub.add_parser("search")
    p.add_argument("--bpm", type=float, default=160)
    p.add_argument("--density", type=float, default=0.6)
    p.add_argument("--sync", type=float, default=0.5)
    p.add_argument("--style", type=str, default="")
    p.add_argument("--sources", type=str, default="gmd,la")
    p.add_argument("--count", type=int, default=6)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("gen")
    p.add_argument("--riff", required=True)
    p.add_argument("--bpm", type=float, default=167)
    p.add_argument("--style", type=str, default="")
    p.add_argument("--bars", type=int, default=0)
    p.add_argument("--humanize", type=int, default=50)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", type=str, default=os.path.join(GEN_DIR, "cli_out.mid"))
    p.set_defaults(fn=cmd_gen)

    p = sub.add_parser("stats")
    p.add_argument("--style", type=str, default="")
    p.add_argument("--bpm", type=float, default=0)
    p.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
