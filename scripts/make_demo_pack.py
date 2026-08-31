# -*- coding: utf-8 -*-
"""
make_demo_pack.py —— 生成一次 6 个风格的对比试听包
==================================================
把你一个 riff 生 6 版不同"味道"的鼓, 一套拖进 REAPER 对比。

用法: python -X utf8 scripts/make_demo_pack.py --riff "X...X.......X..."
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import groove_gen as gg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "gen", "demo_pack")


def variants():
    """(名, kwargs) 列表: 6 种风格方向。"""
    return [
        ("1_emo_prob",    dict(bpm=168, style="emo",   mode="prob",     sparse=0.0, seed=11)),
        ("2_emo_sparse",  dict(bpm=168, style="emo",   mode="prob",     sparse=0.6, seed=11)),
        ("3_emo_skeleton",dict(bpm=168, style="emo",   mode="skeleton", sparse=0.0, seed=11)),
        ("4_punk_drive",  dict(bpm=150, style="punk",  mode="prob",     sparse=0.0, seed=22)),
        ("5_rock_heavy",  dict(bpm=130, style="rock",  mode="prob",     sparse=0.0, seed=33)),
        ("6_slow_breath", dict(bpm=105, style="emo",   mode="prob",     sparse=0.8, seed=44)),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--riff", default="X...X.......X...")
    ap.add_argument("--bars", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    grooves = gg.load_grooves()
    for name, kw in variants():
        ref = gg.pick_reference(grooves, kw["bpm"], kw.get("style"))
        rng = random.Random(kw["seed"])
        bars = gg.parse_riff(args.riff)
        if args.bars > len(bars):
            n_in = len(bars)
            bars = [bars[i % n_in] for i in range(args.bars)]
        beats = [b for b, _ in bars]
        drum = gg.sample_hits(ref["parts"], rng, bars,
                              sparse=kw["sparse"], mode=kw["mode"])
        out = os.path.join(OUT_DIR, f"{name}.mid")
        gg.write_midi(drum, kw["bpm"], out, kw["humanize"] if "humanize" in kw else 50,
                      rng, bar_beats=beats)
        # 统计
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(out)
        n = sum(len(i.notes) for i in pm.instruments)
        print(f"  {name:18} {kw['bpm']:>4}bpm {kw.get('style','-'):>8} "
              f"mode={kw['mode']:9} sparse={kw['sparse']:.1f} -> {n}音符")

    print(f"\n全部生成 -> {OUT_DIR}")
    print("拖进 REAPER: 1_emo_prob 最像真人, 2_emo_sparse 留白, 3 骨架, 4/punk, 5/rock, 6/慢" )


if __name__ == "__main__":
    main()
