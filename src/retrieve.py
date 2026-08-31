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

双库 (GMD 池 + LA 池):
    --sources gmd,la   默认 gmd,la 全上, 任一库缺文件则自动跳过
"""
import argparse
import csv
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROOVES = os.path.join(ROOT, "data", "grooves.json")
LA_CSV = os.path.join(ROOT, "data", "la_pool.csv")   # merge_la_pool.py 产出

# 检索特征向量: [tempo(归一化), density, syncopation, kick, snare, hihat]
DEFAULT_TEMPO = 170.0
FEATURE_WEIGHTS = [0.30, 0.25, 0.25, 0.10, 0.05, 0.05]


def load():
    return json.load(open(GROOVES, encoding="utf-8"))


_la_cache = None


def load_la():
    """LA 池: CSV 行 → 简易 groove dict (无 parts, 只有特征)。"""
    global _la_cache
    if _la_cache is not None:
        return _la_cache
    if not os.path.exists(LA_CSV):
        _la_cache = []
        return _la_cache
    rows = list(csv.DictReader(open(LA_CSV, encoding="utf-8")))
    out = []
    for r in rows:
        try:
            tempo = float(r["tempo"])
            dens = float(r["density_per_bar"])  # 每小节鼓音符数 (10-70)
        except (ValueError, KeyError):
            continue
        # 校准: GMD 每小节鼓音符中位 15.1 ≈ density 1.0 (GMD中点密度)
        # LA 每小节 15 → density≈0.95; 10→0.75; 30→0.95(封顶); 70→1.0
        gmd_per_bar_med = 15.0
        density = min(1.0, dens / gmd_per_bar_med * 0.95)
        out.append({
            "source": "la:" + r["path"].replace("\\", "/"),
            "tempo": tempo,
            "features": {"density": round(density, 3),
                         "syncopation": 0.5,   # LA 无切分特征, 取中性 0.5
                         "kick_density": 0.15,
                         "snare_density": 0.30,
                         "hihat_density": 0.30},
        })
    _la_cache = out
    return out


def load_all(sources):
    gs = []
    if "gmd" in sources:
        gs += load()
    if "la" in sources:
        gs += load_la()
    return gs


def filter_style(gs, style):
    """style 关键词过滤。LA 池无风格标签(来源随机哈希), 默认不过滤 LA。"""
    if not style:
        return gs
    kw = style.lower()
    return [g for g in gs if kw in g["source"].lower() or g["source"].startswith("la:")]


def vec(g, tempo_norm_factor=200.0, target_tempo=DEFAULT_TEMPO):
    f = g["features"]
    return [
        min(1.0, abs(g["tempo"] - target_tempo) / tempo_norm_factor),  # 距离目标越近越好
        f["density"],
        f["syncopation"],
        f["kick_density"],
        f["snare_density"],
        f["hihat_density"],
    ]


def distance(a, b):
    return sum(w * (x - y) ** 2 for w, x, y in zip(FEATURE_WEIGHTS, a, b)) ** 0.5


def retrieve(target_vec, n=8, exclude=None, prefer_beat=False, style=None,
             sources=("gmd", "la"), tempo_band=25.0, target_tempo=DEFAULT_TEMPO):
    """sources: 参与检索的数据源; tempo_band: LA 池的 tempo 预筛窗口 (±bpm)。
    target_tempo: LA 预筛的中心 tempo (传 CLI 的 --bpm)。"""
    gs = filter_style(load_all(sources), style)
    scored = []
    for g in gs:
        if exclude and g["source"] == exclude:
            continue
        # LA 预筛: tempo 差超过窗口的直接跳过 (避免 40万全算)
        if g["source"].startswith("la:") and abs(g["tempo"] - target_tempo) > tempo_band:
            continue
        v = vec(g, target_tempo=target_tempo)
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
    if "parts" not in g or not any(g["parts"].values()):
        # LA 池: 只有特征, 无 parts (解析时再补)
        return (
            f"[{g['tempo']:>5.0f}bpm] dens={f['density']:.2f} sync={f['syncopation']:.2f} "
            f"| {g['source']} | (待解析)"
        )
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
    ap.add_argument("--style", type=str, default="", help="按风格过滤 (punk/rock/pop/halftime...)")
    ap.add_argument("--sources", type=str, default="gmd,la", help="gmd,la 逗号分隔")
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
        print(f"=== 检索 (bpm≈{args.bpm}, density={args.density}, sync={args.sync}, style={args.style or 'any'}, sources={args.sources}) ===")
        for d, g in retrieve(tv, args.count, prefer_beat=True, style=args.style,
                             sources=tuple(args.sources.split(",")),
                             target_tempo=args.bpm):
            print(f"  {d:.3f}  {fmt(g)}")
