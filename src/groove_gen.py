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


def sample_hits_skeleton(dist, rng, bars, sparse=0.0):
    """确定性骨架 + 概率薄饰 (emo 图谱: kick@0/8 主落+backbeat snare+切分后错位)。
    每小节:
      kick: 0 必落, 3/4 拍(8格)按概率, 后段切分(10/14)*sparse
      snare: backbeat 4/12 必落, 切分抢拍(7/9)概率
      hihat: 8分均匀, 反衬强化
    奇数拍小节: 按拍数缩放到 beats*4 格, 骨架位置自适应。"""
    drum = {part: [] for part in PARTS_USED}

    for bi, (beats, bar_cells) in enumerate(bars):
        n_slots = beats * 4
        # 4/4 骨架格索引 → 本小节按比例缩放
        def s16(s):  # 4/4 的16分格 → 本小节格
            return int(round(s * beats / 4.0)) % n_slots

        guitar_hits = [i for i, c in enumerate(bar_cells) if c]

        # Kick: 0/8 主落 + 切分
        kick_slots = {s16(0)}
        for base in (s16(8),):
            if rng.random() < 0.85 - sparse * 0.3:
                kick_slots.add(base)
        # 切分错位: 10/14 在 emo 图谱里后段
        for off in (10, 14):
            if rng.random() < 0.35 * (1.0 - sparse * 0.5):
                kick_slots.add(s16(off))
        # Snare: backbeat + 切分抢拍
        snare_slots = {s16(4), s16(12)}
        if rng.random() < 0.3 * (1.0 - sparse):
            snare_slots.add(s16(7))
        if rng.random() < 0.25:
            snare_slots.add(s16(9))
        # HiHat: 8分均匀 (每2格), 反衬空拍强化 (vel 后续加)
        hat_slots = set(range(0, n_slots, 2))

        for s in kick_slots:
            drum["kick"].append((bi, beats, s))
        for s in snare_slots:
            # snare 不在 hihat 正打格才优 (避免两件同拍一起)
            drum["snare"].append((bi, beats, s))
        for s in hat_slots:
            if s in guitar_hits:
                continue  # 反衬: 吉他重拍处 hihat 弱化
            drum["hihat"].append((bi, beats, s))
        # 小节头 crash
        drum["crash"].append((bi, beats, 0))
    return drum


def sample_hits(dist, rng, bars, sparse=0.0, mode="prob"):
    """按分布采样一顿鼓型 (16 格 × N 小节), 应用吉他重音修正。
    bars: [(beats, [cells]), ...] 每小节独立拍数 (支持奇数拍 7/8 等)。
    sparse: 0-1 留白强度, >0 整体降低命中率 (文档22节: emo 留白>复杂)。
    采样规则:
      - 主格按真人概率衰减 (28% 主格打 1.0, 弱格打 0.5)
      - 装饰格每小节最多抽 1 次"""
    drum = {part: [] for part in PARTS_USED}
    n_bars = len(bars)

    if mode == "skeleton":
        return sample_hits_skeleton(dist, rng, bars, sparse)

    for bi, (beats, bar_cells) in enumerate(bars):
        guitar_hits = [i for i, c in enumerate(bar_cells) if c]
        for part, probs in dist.items():
            if not probs:
                continue
            # 16 格分布是 4/4 基准 (16=4拍), 奇数拍小节按拍数缩放索引
            scale = beats / 4.0
            # probs 索引 s(0-15) 对应 4/4 小节位置, 缩放到本小节 (beats*4 格)
            n_slots = beats * 4
            scaled = [0.0] * n_slots
            for s, p in enumerate(probs):
                scaled[int(s * scale) % n_slots] += p

            # 主格: 概率排名前 7 的格
            ranked = sorted(enumerate(scaled), key=lambda x: -x[1])
            main_slots = [(s, p) for s, p in ranked[:7] if p > 0.02]
            # 装饰格: 排名 8-13
            decor_slots = [s for s, p in ranked[7:13] if p > 0.01]
            rng.shuffle(decor_slots)

            # 主格按相对最高格的概率决定 (如 28% 最高格的 kick, 该格打 1.0,
            # 13% 的第8格打 0.5, 逐级衰减 = 真人"主底带错位")
            pmax = main_slots[0][1] if main_slots else 0.001
            for s, p in main_slots:
                hit_chance = min(1.0, p / pmax)
                # 留白: 整体衰减 (sparse=1 时非主格约 50% 概率不打)
                hit_chance *= (1.0 - sparse * 0.5)
                if rng.random() > hit_chance:
                    continue
                if part == "hihat" and s in guitar_hits:
                    continue
                # kick: 在吉他重音处更稳, 非重音 75% 保留
                if part == "kick" and s not in guitar_hits and rng.random() < 0.25:
                    continue
                drum[part].append((bi, beats, s))
            # 装饰: 每小节最多抽 1 次 (即兴感, 不喧宾夺主), sparse 更强时更少
            for s in decor_slots[:1]:
                if rng.random() < 0.45 * (1.0 - sparse * 0.6):
                    if part == "hihat" and s in guitar_hits:
                        continue
                    drum[part].append((bi, beats, s))
    return drum


def write_midi(drum, bpm, out, humanize=50, rng=None, bar_beats=None):
    rng = rng or random.Random(1)
    mid = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    track = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")
    beat_s = 60.0 / bpm
    # 预计算每小节起始拍 (支持奇数拍)
    bar_beats = bar_beats or []
    bar_start = []
    acc = 0.0
    for b in bar_beats:
        bar_start.append(acc)
        acc += b

    for part, note_hits in drum.items():
        if not note_hits:
            continue
        pitch = PART_TO_PITCH.get(part)
        if pitch is None:
            continue
        for bi, beats, slot in note_hits:
            t = (bar_start[bi] + slot / 4.0) * beat_s
            vel = 70 + int(30 * (rng.random() + humanize / 200.0))
            vel = min(120, max(30, vel))
            track.notes.append(
                pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + 0.12))
    mid.instruments.append(track)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    mid.write(out)
    return out


def parse_riff(riff_text, default_beats=4):
    """解析吉他节奏, 返回 [(beats, [cells]), ...] 小节列表。
    支持 7/8:xxxxxxx 前置指定拍号, 每小节独立拍数。
    cells 是网格序列, 16 分网格密度固定 (每拍 4 格)。"""
    bars = []
    for line in riff_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        beats = default_beats
        if ":" in line and line.split(":")[0].replace("/", "").isdigit():
            ts, line = line.split(":", 1)
            beats = int(ts.split("/")[0])  # "7/8" → 7
            line = line.strip()
        cells = [ch not in (".", " ", "—", "-") for ch in line]
        # 目标格数 = beats * 4 (每拍 4 个16分格)
        target = beats * 4
        while len(cells) < target:
            # 8 格表示 2 拍已是对半拍格, 按拍数自动扩展
            cells.append(False)
        cells = cells[:target]
        bars.append((beats, cells))
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
    ap.add_argument("--sparse", type=float, default=0.0, help="0-1 留白强度")
    ap.add_argument("--mode", type=str, default="prob", choices=["prob", "skeleton"],
                    help="prob=真人概率采样, skeleton=确定性emo骨架")
    args = ap.parse_args()

    grooves = load_grooves()
    ref = pick_reference(grooves, args.bpm, args.style)
    print(f"参考: {ref['n_used']} 首真人 groove 聚合 (tempo≈{ref['tempo']:.0f}bpm)")

    rng = random.Random(args.seed)
    # 小节分隔用 | (拍号里的 / 需要保留)
    bars = parse_riff(args.riff.replace("|", "\n"))
    beats = [b for b, _ in bars]
    print(f"吉他 {len(bars)} 小节 (拍号: {beats}), bpm={args.bpm}, sparse={args.sparse}, mode={args.mode}")
    drum = sample_hits(ref["parts"], rng, bars, sparse=args.sparse, mode=args.mode)
    out = write_midi(drum, args.bpm, args.out, args.humanize, rng, bar_beats=beats)
    pm = pretty_midi.PrettyMIDI(out)
    print(f"生成 -> {out} ({sum(len(i.notes) for i in pm.instruments)} 音符)")


if __name__ == "__main__":
    main()
