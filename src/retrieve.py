# -*- coding: utf-8 -*-
"""
retrieve.py —— 特征检索器
========================
第 2 步: 输入吉他节奏描述(或直接挑特征) → 从 grooves.json 检索相似 groove。

MVP 用欧氏距离 (文档: 第一阶段不需要向量库)。

用法:
    # 交互式问特征
    python -X utf8 src/retrieve.py --bpm 170 --style rock --count 5
    # 或全默认, 随机看
    python -X utf8 src/retrieve.py --count 8
"""
import argparse
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROOVES = os.path.join(ROOT, "data", "grooves.json")

# 检索特征向量: [tempo(归一化), density, syncopation, kick, snare, hihat]
DEFAULT_TEMPO = 170.0
FEATURE_WEIGHTS = [0.30, 0.25, 0.25, 0.10, 0.05, 0.05]


def load():
    return json.load(open(GROOVES, encoding="utf-8"))


def vec(g, tempo_norm_factor=200.0):
    f = g["features"]
    return [
        min(1.0, abs(g["tempo"] - DEFAULT_TEMPO) / tempo_norm_factor),  # 距离中心越近越好
        f["density"],
        f["syncopation"],
        f["kick_density"],
        f["snare_density"],
        f["hihat_density"],
    ]


def distance(a, b):
    return sum(w * (x - y) ** 2 for w, x, y in zip(FEATURE_WEIGHTS, a, b)) ** 0.5


def retrieve(target_vec, n=8, exclude=None, prefer_beat=False):
    gs = load()
    scored = []
    for g in gs:
        if exclude and g["source"] == exclude:
            continue
        v = vec(g)
        d = distance(target_vec, v)
        # beat 优先: fill 型(过门) 惩罚 0.06, 让它排后 (文档: 律动>过门)
        if prefer_beat and "fill" in g["source"]:
            d += 0.06
        scored.append((d, g))
    scored.sort(key=lambda x: x[0])
    return scored[:n]


def fmt(g):
    f = g["features"]
    parts = sorted(
        (p for p, hits in g["parts"].items() if hits),
        key=lambda p: -len(g["parts"][p]))
    head = " ".join(f"{p}({len(g['parts'][p])})" for p in parts[:4])
    return (
        f"[{g['tempo']:>5.0f}bpm] dens={f['density']:.2f} sync={f['syncopation']:.2f} "
        f"| {g['source']} | {head}"
    )


def random_pick(n=3):
    gs = load()
    return random.sample(gs, n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bpm", type=float, default=DEFAULT_TEMPO)
    ap.add_argument("--density", type=float, default=0.6, help="0-1 目标密度")
    ap.add_argument("--sync", type=float, default=0.5, help="0-1 目标切分强度")
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--random", action="store_true", help="不看特征, 随机出几个")
    args = ap.parse_args()

    if args.random:
        print("=== 随机 3 首 (先乱看) ===")
        for g in random_pick():
            print("  " + fmt(g))
        print("\n推荐: 加参数检索 --bpm 170 --density 0.6 --sync 0.5")
    else:
        # 目标向量: bpm → 与150接近得分为低
        tv = [
            min(1.0, abs(args.bpm - 150.0) / 200.0),
            args.density, args.sync,
            0.15, 0.10, 0.30,
        ]
        print(f"=== 检索 (bpm≈{args.bpm}, density={args.density}, sync={args.sync}) ===")
        for d, g in retrieve(tv, args.count, prefer_beat=True):
            print(f"  {d:.3f}  {fmt(g)}")
