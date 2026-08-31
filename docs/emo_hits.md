# Emo 味参考素材清单 (已鉴定)

> 从 GMD 真库 448 首里按特征挖出的 emo 味参考。
> 目录: data/emo_pool/ (对应 GMD midionly, CC-BY-4.0)

## 一、最"emo"的素材 (低kick+高切分+中速, 核心参考)

| 文件 | tempo | 特征 (density/sync/kick) | 味道 |
|------|-------|-----|------|
| drummer3__session1__28_rock_120_beat | 120 | 0.38/1.00/0.00 | 极致留白+全切分 (kick 几乎不打!) |
| drummer3__session1__36_rock_120_beat | 120 | 0.50/0.88/0.00 | 无 kick 切分, 反拍全靠 snare/hihat |
| drummer2__session2__2_rock_130_beat | 130 | 0.78/0.88/0.10 | 高切分+低 kick |
| drummer3__session1__47_rock_120_beat | 120 | **0.19**/0.67/0.0 | 全库最稀疏——留白之王 |
| drummer7__session2__100_pop_142_beat | 142 | 0.82/0.82/0.09 | emogaze 轻快切分 |
| drummer2__session2__9_rock_130_beat | 130 | 0.81/0.87/0.19 | 切分拉满 |

> ✅ **这些是 `--style emo` 聚合池的核心成分** (drummer3 rock + drummer7 pop)。

## 二、emo 律动图谱 (86 首真库聚合出的 16 格分布)

```
Kick  0:28%  8:13%  10:9%  14:8%  4:8%   12:7%  6:6%  11:4%
Snare 4:23%  12:23% 9:7%   8:6%   10:5%  7:4%  11:4% 14:4%
HiHat 8:11%  0:10%  4:10%  12:10% 6:9%   2:9%  10:8% 14:7%
```

**解读**：
- Kick: 只在第 1/3 拍落主(0/8), 后段用 10/14 的**切分错位**(不是每拍跟吉他!)
- Snare: 标准 2/4 backbeat (4/12) 但带 9/8/7 的**提前抢拍**
- HiHat: 8 分均匀但速度有弹性

## 三、留白型 (用于"呼吸段"作参考)

- drummer3__session1__47_rock_120_beat (density 0.19, 全库最稀疏)
- drummer1__session2__186_rock_115_fill (density 0.31)
- drummer1__session1__220_rock-halftime_140_fill (density 0.34 + sync 0.73)

## 四、怎么用

- **生成**: `python src/main.py gen --style emo`
- **聚合池**: 86 首 (drummer3 rock + drummer7 pop, beat 型)
- **后续 LA 扫描**后: 用同样的特征规则 (density<0.85, sync>0.55, 100-180bpm) 从 40 万首里再挖, 放大这个池
