# -*- coding: utf-8 -*-
"""
groove_gen.py —— 基于真人律动分布采样的生成器
===========================================
核心突破: 不拍脑袋摆 kick/snare, 而是:
  1. 检索最匹配的真人 groove (emopool)
  2. 从它的 16 格击打分布里采样 (继承真人的切分/偏移/密度习惯)
  3. 套上吉他 riff 的重音修正 → 输出.

这是文档"真人 MIDI 检索 → LLM 修改 → 生成"的正确落地第一版。

用法:
    python -X utf8 src/groove_gen.py --riff "X...X.......X..." --bpm 165 --out data/gen/live1.mid
"""
import argparse
import json
import os
import random

import pretty_midi

import groove as gr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROOVES = os.path.join(ROOT, "data", "grooves.json")

NOTE_KICK = 36
NOTE_SNARE = 38
NOTE_HAT = 42
NOTE_OHAT = 46
NOTE_CRASH = 49
NOTE_RIDE = 51
NOTE_TOM = 45  # Tom Low

PART_TO_PITCH = {
    "kick": NOTE_KICK, "snare": NOTE_SNARE, "hihat": NOTE_HAT,
    "open_hihat": NOTE_OHAT, "crash": NOTE_CRASH, "ride": NOTE_RIDE,
    "tom": NOTE_TOM,
}

# 生成时使用的部件 (排除超装饰性的)
PARTS_USED = ["kick", "snare", "hihat", "open_hihat", "crash", "ride", "tom"]


def load_grooves(path=GROOVES):
    return json.load(open(path, encoding="utf-8"))


# emo 味专用聚合: drummer3 rock + drummer7 pop 的真人素材 (低kick+高切分+回弹)
EMO_POOL = None  # 懒加载


def emo_style_candidates(grooves):
    return [g for g in grooves
            if ("drummer3" in g["source"] and "rock" in g["source"] and "beat" in g["source"])
            or ("drummer7" in g["source"] and "pop" in g["source"] and "beat" in g["source"])]


def pick_reference(grooves, bpm, style=None):
    """检索最接近的真人 groove (风格+tempo 过滤后, 聚合成 ONE 综合分布)。
    返回 { parts: {16格概率}, tempo, n_used }。聚合比单首更稳(真人习惯是跨歌统计的)。
    style="emo" 时用 emo 味素材池 (低kick+切分+回弹), 其他按来源过滤。"""
    from collections import Counter
    cands = [g for g in grooves if g["bars"] <= 4]
    if style == "emo":
        emo = [g for g in cands if g["source"] in emo_style_candidates(grooves)]
        if len(emo) >= 3:
            cands = emo
    elif style:
        styled = [g for g in cands if style.lower() in g["source"].lower()]
        if len(styled) >= 3:
            cands = styled

    # tempo 窗口: 最多选 30 首里 tempo 最接近的
    cands.sort(key=lambda g: abs(g["tempo"] - bpm))
    pool = cands[:30]

    agg = {}
    for part in PARTS_USED:
        cnt = Counter()
        for g in pool:
            for h in g["parts"].get(part, []):
                cnt[int(round(h["pos"] * 4)) % 16] += 1
        total = sum(cnt.values())
        if total == 0:
            continue
        agg[part] = [cnt.get(i, 0) / total for i in range(16)]
    return {"parts": agg, "tempo": bpm, "n_used": len(pool)}


def build_distribution(groove):
    """从真人 groove 构建 16 格分布 dict: {part: {16格: 概率}}。"""
    dist = {}
    for part in PARTS_USED:
        hits = groove["parts"].get(part, [])
        if not hits:
            continue
        grid = [0.0] * 16
        for h in hits:
            pos = h["pos"]
            # pos 是小节内拍数(0~4), 归 16 格
            slot = int(round(pos * 4)) % 16
            grid[slot] += 1.0
        total = sum(grid)
        dist[part] = [c / total for c in grid]
    return dist


def sample_hits(dist, rng, cells):
    """按分布采样一顿鼓型 (16 格 × N 小节), 应用吉他重音修正。
    cells: [[bool*16], ...] 吉他重音。
    采样规则:
      - 每格 p=真实概率; 用 p>=0.15 的格为"主击"(必打), p<0.15 为"装饰"(抽签)
      - 每小节最多打 2 次装饰, 避免全程八分噪音"""
    drum = {part: [] for part in PARTS_USED}
    n_bars = len(cells)

    for bi, bar_cells in enumerate(cells):
        guitar_hits = [i for i, c in enumerate(bar_cells) if c]
        for part, probs in dist.items():
            if not probs:
                continue
            # 主格: 概率排名前 7 的格 (真人分布平缓, 不靠阈值)
            ranked = sorted(enumerate(probs), key=lambda x: -x[1])
            main_slots = [(s, p) for s, p in ranked[:7] if p > 0.02]
            # 装饰格: 排名 8-13
            decor_slots = [s for s, p in ranked[7:13] if p > 0.01]
            rng.shuffle(decor_slots)

            # 主格按相对最高格的概率决定 (如 28% 最高格的 kick, 该格打 1.0,
            # 13% 的第8格打 0.5, 逐级衰减 = 真人"主底带错位")
            pmax = main_slots[0][1] if main_slots else 0.001
            for s, p in main_slots:
                hit_chance = min(1.0, p / pmax)
                if rng.random() > hit_chance:
                    continue
                if part == "hihat" and s in guitar_hits:
                    continue
                # kick: 在吉他重音处更稳, 非重音 75% 保留
                if part == "kick" and s not in guitar_hits and rng.random() < 0.25:
                    continue
                drum[part].append((bi, s))
            # 装饰: 每小节最多抽 1 次 (即兴感, 不喧宾夺主)
            for s in decor_slots[:1]:
                if rng.random() < 0.45:
                    if part == "hihat" and s in guitar_hits:
                        continue
                    drum[part].append((bi, s))
    return drum


def write_midi(drum, bpm, out, humanize=50, rng=None):
    rng = rng or random.Random(1)
    mid = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    track = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")
    beat_s = 60.0 / bpm
    for part, note_hits in drum.items():
        if not note_hits:
            continue
        pitch = PART_TO_PITCH.get(part)
        if pitch is None:
            continue
        for bi, slot in note_hits:
            t = (bi * 4 + slot / 4.0) * beat_s
            vel = 70 + int(30 * (rng.random() + humanize / 200.0))
            vel = min(120, max(30, vel))
            track.notes.append(
                pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + 0.12))
    mid.instruments.append(track)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    mid.write(out)
    return out


def parse_riff(riff_text):
    bars = []
    for line in riff_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cells = [ch not in (".", " ", "—", "-") for ch in line]
        while len(cells) < 16:
            if len(cells) == 8:
                d = []
                for c in cells:
                    d += [c, False]
                cells = d
                continue
            cells.append(False)
        bars.append(cells[:16])
    return bars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--riff", type=str, required=True,
                    help="吉他节奏, 每小节16格 (X=打 .=空), / 分隔多小节")
    ap.add_argument("--bpm", type=float, default=165)
    ap.add_argument("--style", type=str, default="", help="参考风格 (punk/rock/...)")
    ap.add_argument("--out", type=str, default=os.path.join(ROOT, "data", "gen", "live_drum.mid"))
    ap.add_argument("--humanize", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    grooves = load_grooves()
    ref = pick_reference(grooves, args.bpm, args.style)
    print(f"参考: {ref['n_used']} 首真人 groove 聚合 (tempo≈{ref['tempo']:.0f}bpm)")

    rng = random.Random(args.seed)
    bars = parse_riff(args.riff.replace("/", "\n"))
    print(f"吉他 {len(bars)} 小节, bpm={args.bpm}")
    drum = sample_hits(ref["parts"], rng, bars)
    out = write_midi(drum, args.bpm, args.out, args.humanize, rng)
    pm = pretty_midi.PrettyMIDI(out)
    print(f"生成 -> {out} ({sum(len(i.notes) for i in pm.instruments)} 音符)")


if __name__ == "__main__":
    main()
