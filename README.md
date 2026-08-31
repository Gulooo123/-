# 写鼓小助手 (Drum Groove Assistant)

> 感觉架子鼓脑子里的节奏型太少了，干脆做一个资料库 + 助手出来，自己使用。

给 emo / midwest emo / math rock 吉他 riff 配鼓的本地工具。输入吉他节奏 → 从真人鼓手 MIDI 库里检索参考 → 生成候选鼓型 → 输出可直接拖进 DAW 的 .mid。

**定位：个人创作工具，不对外服务。** 目标是"当我想不到鼓的时候，给我一个真正像鼓手一样的创作起点"。

## 快速开始

```bash
# 检索参考律动
python src/main.py search --bpm 168 --style emo

# 生成 (一行命里: 16格节奏 → 鼓)
python src/main.py gen --riff "X...X.......X..." --bpm 168 --style emo

# 生成 6 风格对比包 (一个 riff 六种味道)
python scripts/make_demo_pack.py --riff "X...X.......X..."
```

### `--mode` 双模式
- `prob` (默认): 真人概率采样 — 从 30 首真人 groove 聚合的 16 格分布采样, 还原真人"主底带错位"
- `skeleton`: 确定性骨架 — kick@0/8 + snare@backbeat 的教科书 4/4

### 节奏输入格式
```
X...X.......X...     # 4/4, 每小节16格一列 (X=打 .=空), 用 | 分隔小节
7/8:XXX..XX..X..X|4/4:X...X.......X...|5/8:XXX..X..X    # 奇数拍 (每小节独立)
```

### 其他参数
| 参数 | 说明 |
|------|------|
| `--sparse 0-1` | 留白强度 (emo 留白 > 复杂, 实测 22→13 音符) |
| `--humanize 0-100` | velocity ±5~15 抖动 + 时间错位 |
| `--bars N` | 小节循环 (做歌段) |
| `--seed` | 随机种子, 同种子可复现 |
| `--style` | emo / punk / rock (emo=低kick高切分素材池) |

## 数据源

| 数据 | 内容 | 许可 | 体积 | 状态 |
|------|------|------|------|------|
| **GMD (midionly)** | 1150 个真人鼓 MIDI, 9件套含 velocity | CC BY 4.0 | 3.3MB zip | ✅ `data/raw/gmd_midionly/` |
| **emo_pool** | GMD 筛出 rock/punk/pop 448 首 | CC BY 4.0 | 2.3MB | ✅ `data/emo_pool/` |
| **grooves.json** | 448 首解析成的结构化律动(16格分布+特征) | - | 小 | ✅ |
| **LA 全集** | 40.5万 MIDI (40万无标注, 需内容扫描) | CC BY-NC-SA 4.0 | 9.2GB zip | ⏳ 下载/扫描中 |

### 数据缺口 (重要)
**GMD 的 1-2 小节节奏型 tempo 上限 = 145bpm**。150-180bpm(emo 主流 riff 区间)缺真人参考。
→ 由 LA 全集 (40万首, 必有快鼓轨) 补, 扫描优先掏 150-180。

## 工具链 (src/)

| 文件 | 功能 |
|------|------|
| `main.py` | 统一 CLI (info/search/gen/stats) |
| `groove.py` | MIDI→结构化 groove (部件+16格位置+velocity+特征) |
| `groove_gen.py` | 生成器 (真人聚合采样 + 双模式 + 奇数拍 + sparse + 真库velocity) |
| `retrieve.py` | 特征检索器 (GMD+LA 双库, style过滤, beat优先) |
| `sample_humanize.py` | 真人 velocity 统计 (snare 重 104 vs kick 轻 60) |
| `scan_library.py` | LA 内容扫描 (mido 版, 40万首 ≈ 11分钟) |
| `la_feature.py` | LA 候选 → 完整特征 (两阶段扫描第二段) |

## 网络备注

- `storage.googleapis.com` / `magenta.tensorflow.org` 直连可下
- `huggingface.co` 直连不通 → 走 `hf-mirror.com`
- git 全局代理 127.0.0.1:7890 已死, 直连可用

## 复现

```bash
python scripts/download_gmd.py    # GMD 全链 (下载+解压+emo_pool)
python scripts/setup_la.py        # LA 全链 (解压+扫描+merge) 下载完数据后
```
