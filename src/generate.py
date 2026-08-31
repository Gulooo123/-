# -*- coding: utf-8 -*-
"""
generate.py —— 从吉他节奏生成鼓 MIDI
====================================
第 3 步基础版: 输入吉他节奏(格子文本) → 选一个参考 groove → 保留其速度/切分风格,
按吉他重音结构生成鼓型 → 输出 .mid。

吉他节奏格式 (4/4, 一小节一行, 16 分网格, X=打, .=空):
    X...X.......X...
    或写音符名: E5...G5...
更好用: 支持省略拍号, 自动检测小节长度。

鼓型策略 (文档第14节: 不要让 Kick 100% 跟吉他):
  - Kick: 跟随吉他重音 + backbeat 基础 (位置 0/2)
  - Snare: 保持 2/4 (backbeat), 吉他强切分处提前抢
  - HiHat: 8分律动, 在吉他空拍处加重 (反衬)
  - 速度: 参考 groove 的 swung 程度传递给 hihat
  - Humanize (文档第21节): 0%完全量化 / 25%轻微 / 50%真人感 / 100%松动
    velocity ±(5~15) + timing ±(5~15ms)

用法:
    python -X utf8 src/generate.py --riff "X...X.......X.../...X..X....X...." \
        --bpm 160 --out data/gen/out1.mid --humanize 50
    --bars 8: 小节反复, 第4/8小节自动插 fill(过门)
"""
import argparse
import os
import random

import pretty_midi

# GM 鼓音高
NOTE_KICK = 36
NOTE_SNARE = 38
NOTE_HAT_CLOSED = 42
NOTE_HAT_OPEN = 46
NOTE_RIDE = 51
NOTE_CRASH = 49
NOTE_TOM_MID = 48
NOTE_TOM_LOW = 45

# 默认 velocity 基准 (文档第5节: 真人感=变化, 不要全一样)
BASE_VEL = {
    "kick": 105, "snare": 115, "hat": 75, "open_hat": 62, "ride": 72,
    "crash": 95, "tom": 85,
}
JITTER = 8  # velocity ±抖动 (humanize=0 时)

# fill 滚动的 tom 音高轮换 (Tom 中/低交替)
NOTETOM = [NOTE_TOM_MID, NOTE_TOM_LOW, 47]  # 47=Tom mid2


def humanize_vel(vel, level, rng, max_jit=15):
    """humanize level 0-100 → velocity 抖动量 (文档21节: 0%量化→100%极端, ±5~15)。"""
    jit = max_jit * (level / 100.0)
    return max(1, min(127, int(vel + rng.randint(-int(jit), int(jit)))))


def humanize_tick(base_t, level, rng, max_ms=15.0, beat_s=0.25):
    """time 抖动: ±(max_ms * level%) 毫秒。"""
    ms = max_ms * (level / 100.0)
    return base_t + rng.uniform(-ms, ms) / 1000.0


def parse_riff(riff_text):
    """解析吉他节奏行, 返回 [[hit_or_None, ...], ...] 每小节16格。
    支持字符: X/x 打, . 空, 其他字母视为音符名(非空即打)。"""
    bars = []
    for line in riff_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cells = []
        for ch in line:
            cells.append(ch not in (".", " ", "—", "-"))
        # 规范化到 16 格 (补齐或截断)
        while len(cells) < 16:
            # 若输入已是 8 分格(8格), 双倍扩展
            if len(cells) == 8:
                doubled = []
                for c in cells:
                    doubled += [c, False]
                cells = doubled
                continue
            cells.append(False)
        cells = cells[:16]
        bars.append(cells)
    return bars


def choose_reference(style="punk", seed=42):
    """从 emo_pool 挑一个参考 groove 文件 (按 style 关键字)."""
    files = os.listdir(os.path.join(ROOT, "data", "emo_pool"))
    cands = [f for f in files if f.endswith(".mid") and style.lower() in f.lower()]
    if not cands and files:
        cands = [f for f in files if f.endswith(".mid")]
    rng = random.Random(seed)
    return os.path.join(ROOT, "data", "emo_pool", rng.choice(cands)) if cands else None


def build_drum(bars, bpm, filepath, swing=0.10, rng=None, humanize=50, fill_every=0):
    """bars: [[bool*16], ...], 生成鼓轨 (含 humanize + 可选 fill)。
    humanize: 0-100 (0=完全量化), fill_every: 每 N 小节插一次 fill(0=不插)。"""
    rng = rng or random.Random(42)
    mid = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    drum_track = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    kick_notes = []
    snare_notes = []
    hat_notes = []
    open_hat_notes = []
    ride_notes = []
    crash_notes = []
    tom_notes = []

    tom_roll_notes = []  # (bar, step, pitch, vel) 支持多音高

    # 小节内 16 分网格 → 秒
    def tick(bari, step):
        # 每拍 0.25s @ 120bpm; 16分 = 0.25*(60/bpm)
        beat_s = 60.0 / bpm
        return (bari * 4 + step / 4.0) * beat_s + (0.02 if swing else 0) * step

    # fill 小节标记: 每 fill_every 的末尾小节 (bari 从 0 开始, 第4小节=bi 3)
    fill_bars = set()
    if fill_every:
        for k in range(1, len(bars) + 1):
            if k % fill_every == 0:
                fill_bars.add(k - 1)

    for bi, cells in enumerate(bars):
        if bi in fill_bars:
            # 过门小节: 1拍 hihat + 2-4拍 tom/snare 滚动
            hat_notes.append((bi, 0, BASE_VEL["hat"]))
            hat_notes.append((bi, 2, BASE_VEL["hat"] - 10))
            for s in [6, 8, 10, 12, 14]:
                tom_roll_notes.append((bi, s,
                                       NOTETOM[s % 3],
                                       humanize_vel(BASE_VEL["tom"], humanize, rng)))
            snare_notes.append((bi, 14, BASE_VEL["snare"]))
            crash_notes.append((bi, 0, BASE_VEL["crash"]))
            continue
        # 吉他重音索引
        acc = [i for i, c in enumerate(cells) if c]
        big_acc = [i for i in acc if i % 4 in (0, 2)]  # 正拍重音
        off_acc = [i for i in acc if i % 4 not in (0, 2)]  # 切分重音

        # Kick: backbeat 基础 + 部分吉他重音跟进 (60%跟进,留白感)
        kick_steps = {0}  # 第0拍落底
        for i in acc:
            if i % 4 == 0 and i not in kick_steps and rng.random() < 0.55:
                kick_steps.add(i)
        for i in off_acc:
            if rng.random() < 0.45:
                kick_steps.add(i)

        # Snare: 2拍/4拍 backbeat; 吉他强切分处 0.3 概率提前抢一拍
        snare_steps = {4, 12}
        for i in off_acc:
            if rng.random() < 0.3:
                snare_steps.add(i)

        # HiHat: 8分律动 = 每 2 格; 吉他空拍处强化(velocity高,反衬)
        hat_steps = set(range(0, 16, 2))
        hat_velup = set(i for i in range(16) if not cells[i])

        for s in hat_steps:
            vel = humanize_vel(BASE_VEL["hat"], humanize, rng)
            if s in hat_velup:
                vel += 12 if humanize < 30 else rng.randint(8, 16)
            hat_notes.append((bi, s, vel))

        # 把 kick/snare 生成成具体音符
        for s in kick_steps:
            kick_notes.append((bi, s, humanize_vel(BASE_VEL["kick"], humanize, rng)))
        for s in snare_steps:
            snare_notes.append((bi, s, humanize_vel(BASE_VEL["snare"], humanize, rng)))

        # 偶发开放 hihat (第2/3拍前)
        if rng.random() < 0.5:
            open_hat_notes.append((bi, 14, humanize_vel(BASE_VEL["open_hat"], humanize, rng)))

        # Ride/crash: 小节头 crash, 后段 ride
        crash_notes.append((bi, 0, BASE_VEL["crash"]))
        ride_notes.append((bi, 8, humanize_vel(BASE_VEL["ride"], humanize, rng)))

        # Tom: 用离和弦远的重音在收尾添点色彩
        if big_acc and bi in (0, len(bars) - 1):
            tom_notes.append((bi, big_acc[-1], humanize_vel(BASE_VEL["tom"], humanize, rng)))

    def place(notes, pitch):
        for bar, step, vel in notes:
            t = tick(bar, step)
            # 时间 humanize: 只抖最边缘 5-15%, 保留 groove 骨架感
            t = humanize_tick(t, humanize, rng)
            drum_track.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + 0.12))

    place(kick_notes, NOTE_KICK)
    place(snare_notes, NOTE_SNARE)
    place(hat_notes, NOTE_HAT_CLOSED)
    place(open_hat_notes, NOTE_HAT_OPEN)
    place(ride_notes, NOTE_RIDE)
    place(crash_notes, NOTE_CRASH)
    place(tom_notes, NOTE_TOM_LOW)

    # fill 滚动: 多音高单独放
    for bar, step, pitch, vel in tom_roll_notes:
        t = tick(bar, step)
        t = humanize_tick(t, humanize, rng)
        drum_track.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + 0.12))

    mid.instruments.append(drum_track)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    mid.write(filepath)
    return filepath


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--riff", type=str, required=True,
                    help="吉他节奏, 每小节一行16格 (X=打 .=空), 多小节用 / 分隔")
    ap.add_argument("--bpm", type=float, default=165)
    ap.add_argument("--out", type=str, default=os.path.join(ROOT, "data", "gen", "drum_out.mid"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--humanize", type=int, default=50, choices=range(0, 101),
                    help="0=完全量化 25=轻微 50=真人感 75=明显松动 100=极端")
    ap.add_argument("--bars", type=int, default=0,
                    help="目标小节数, 大于输入小节则循环复制")
    ap.add_argument("--fill", type=int, default=0,
                    help="每 N 小节插一次过门(fill), 0=不插")
    args = ap.parse_args()

    riff_text = args.riff.replace("/", "\n")
    bars = parse_riff(riff_text)
    if args.bars and args.bars > len(bars):
        n_in = len(bars)
        bars = [bars[i % n_in] for i in range(args.bars)]
    print(f"解析 {len(bars)} 小节, bpm={args.bpm}, humanize={args.humanize}, fill_every={args.fill}")

    rng = random.Random(args.seed)
    filepath = build_drum(bars, args.bpm, args.out, rng=rng,
                          humanize=args.humanize, fill_every=args.fill)
    print(f"生成 -> {filepath}")
    # 验证
    pm = pretty_midi.PrettyMIDI(filepath)
    print(f"验证: 鼓音符 {sum(len(i.notes) for i in pm.instruments)} 个")


if __name__ == "__main__":
    main()
