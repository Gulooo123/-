# -*- coding: utf-8 -*-
"""
groove.py —— MIDI → 结构化 Groove
第 1 步: 解析 GMD 鼓 MIDI, 提取每件乐器的 hit 位置(小节内拍点) + velocity, 落成 JSON 库。

设计要点 (呼应 GPT 文档第 5-8 节):
- 不把原始 MIDI 喂给 LLM, 转成结构化的"节拍网格"表示 (position 单位: 1 = 1 拍)
- position 不由 LLM 自己编, 从真人演奏量化后得来
- velocity 原样保留 (真人 feel 的精华)
- 特征: density / syncopation / kick/snare/hihat density 等

鼓键位 (GM, GMD 实测分布: 36=Kick 38/40=Snare 42/44=HiHat-closed/open 46=open 51=Ride 49=Cymbal 43/48/41=Toms 22/26/57=percs)
"""
import csv
import json
import os
from collections import Counter

import pretty_midi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL = os.path.join(ROOT, "data", "emo_pool")
OUT = os.path.join(ROOT, "data", "grooves.json")

# 鼓部件 → GM 音高
PARTS = {
    "kick":   [36, 35],
    "snare":  [38, 40, 37],
    "hihat":  [42, 44],
    "open_hihat": [46, 44],
    "ride":   [51, 59, 53],
    "crash":  [49, 57, 55],
    "tom":    [41, 43, 45, 47, 48, 50, 22, 26],
}


def parse_midi(path):
    pm = pretty_midi.PrettyMIDI(path)
    tempo = pm.get_tempo_changes()[1][0] if len(pm.get_tempo_changes()[1]) else 120.0

    # 找鼓轨 (is_drum 或 音高落在鼓键位里)
    drum = None
    for ins in pm.instruments:
        if ins.is_drum:
            drum = ins
            break
    if drum is None:
        # GMD 是 channel 9 (is_drum=True), 没有就捞所有含鼓音高的轨
        for ins in pm.instruments:
            if any(n.pitch in [p for ps in PARTS.values() for p in ps] for n in ins.notes):
                drum = ins
                break
    if drum is None:
        return None

    beats_per_bar = 4  # GMD 全 4/4, 保守按 4 处理
    seconds_per_beat = 60.0 / tempo
    # 小节边界: 0, 4拍, 8拍... 取第一个 hit 前的整小节作为起点更稳
    # GMD 每个文件是独立 groove (1-8 小节), 直接按 GM bar 切
    bar_len = beats_per_bar * seconds_per_beat

    notes = drum.notes
    if not notes:
        return None

    # 按小节分组
    bars = {}
    for n in notes:
        bar_idx = int(n.start // bar_len)
        bars.setdefault(bar_idx, []).append(n)

    # 只保留相对 0 起的 bar, features 按 bar 数平均
    n_bars = max(bars.keys()) + 1

    # 每件乐器的 hit 列表 (position = 拍内小数值)
    part_hits = {}
    for part, pitches in PARTS.items():
        hits = []
        for bar_idx in sorted(bars):
            for n in bars[bar_idx]:
                if n.pitch in pitches:
                    pos = (n.start - bar_idx * bar_len) / seconds_per_beat  # 拍数, 偏移到 bar 内
                    hits.append({
                        "bar": bar_idx,
                        "pos": round(pos, 3),
                        "vel": n.velocity,
                    })
        part_hits[part] = hits

    # 特征
    grid = 16  # 16 分网格, 判定 "同步切分"
    total_slots = n_bars * beats_per_bar * (grid // 4)
    hits_count = sum(len(h) for h in part_hits.values())
    density = min(1.0, hits_count / total_slots)

    syncopated = 0
    for part, hits in part_hits.items():
        for h in hits:
            eighths = h["pos"] * 2  # 以 8 分音符为单位
            if abs(eighths - round(eighths)) > 0.05 and abs(h["pos"] - round(h["pos"])) > 0.05:
                syncopated += 1
    syncopation = syncopated / max(1, hits_count)

    result = {
        "source": os.path.relpath(path, ROOT).replace("\\", "/"),
        "tempo": round(tempo, 1),
        "bars": n_bars,
        "beats_per_bar": beats_per_bar,
        "parts": part_hits,
        "features": {
            "density": round(density, 3),
            "syncopation": round(syncopation, 3),
            "kick_density": round(len(part_hits["kick"]) / total_slots, 3),
            "snare_density": round(len(part_hits["snare"]) / total_slots, 3),
            "hihat_density": round(len(part_hits["hihat"]) / total_slots, 3),
        },
    }
    return result


def build_all():
    files = sorted(f for f in os.listdir(POOL) if f.endswith(".mid"))
    grooves = []
    errs = 0
    for f in files:
        g = parse_midi(os.path.join(POOL, f))
        if g:
            grooves.append(g)
        else:
            errs += 1
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(grooves, fp, ensure_ascii=False, indent=None, separators=(",", ":"))
    print(f"解析 {len(grooves)} 个 groove, 失败 {errs} 个 -> {OUT}")


if __name__ == "__main__":
    build_all()
