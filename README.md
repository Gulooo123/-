# 写鼓小助手 (Drum Groove Assistant)

> 感觉架子鼓脑子里的节奏型太少了，干脆做一个资料库 + 助手出来，自己使用。

给 emo / midwest emo / math rock 吉他 riff 配鼓的本地工具。输入吉他 MIDI → 从真人鼓手 MIDI 库里检索参考 → 生成候选鼓型 → 输出可直接拖进 DAW 的 .mid。

**定位：个人创作工具，不对外服务。** 目标是"当我想不到鼓的时候，给我一个真正像鼓手一样的创作起点"。

## 数据源（已爬取的资源）

| 数据 | 内容 | 许可 | 体积 | 状态 |
|------|------|------|------|------|
| **GMD (Groove MIDI Dataset, midionly)** | 1150 个真人鼓 MIDI + info.csv（风格/BPM/拍号标注），9 件套鼓，含 velocity | CC BY 4.0 | zip 3.3MB / 解压 6.9MB | ✅ 已下载 `data/raw/gmd_midionly/` |
| **emo_pool** | 从 GMD 筛出的 rock/punk/pop 亲缘子集（448 首），空 emo 语料时代的主力 | CC BY 4.0 | 2.3MB | ✅ `data/emo_pool/` + `emo_pool_index.csv` |

### 目录结构

```
data/
  raw/gmd_midionly/groove/        # GMD 原始数据(含 info.csv, LICENSE)
  emo_pool/                       # 筛选后的 emo 候选池 (rock/punk/pop...)
  emo_pool_index.csv              # 检索索引: style/bpm/beat_type/split...
scripts/
  download_gmd.py                 # 下载+解压+筛选 GMD (可重复执行)
src/                              # (待开工) 解析/切分/检索/生成
docs/                             # (待补充) 笔记/思路
```

## GMD 风格分布（key 数据）

- rock 341 / funk 160 / jazz 101 / latin 97 / hiphop 95 / soul 63 / afrocuban 60 / punk 58
- **emo_pool 实际覆盖**: rock 281、punk 58、rock/halftime 37、funk/rock 20、pop/soft 13、rock/indie 10 …（共 448 首）
- BPM 范围 50~290

**重要缺口**：GMD 没有 midwest/math/emo 风格字段——它给"真人律动/velocity 变化"，不给"emo 节奏词汇"。
emo 味的参考律动要靠第 2 数据链路补（自己的 emo 歌扒谱 / 合法 MIDI 源），见 `docs/` 规划。

## 网络备注

- `storage.googleapis.com` / `magenta.tensorflow.org` **直连可下**，不需要代理
- `huggingface.co` 直连不通，走 `hf-mirror.com` 镜像
- **git 全局代理 127.0.0.1:7890 是死的**（本地没有服务监听），git 操作直接用直连
- `github.com` API + 仓库访问直连可用

## 复现下载

```bash
python scripts/download_gmd.py
```

## 进度

- [x] 第 0 步：GMD 下载 + 解压 + emo 候选池
- [x] 第 1 步：MIDI 解析 → 切 groove → 结构化表示（JSON 特征库） `src/groove.py` → `data/grooves.json`（448 条）
- [x] 第 2 步：按特征（BPM/density/syncopation/velocity）检索相似 groove `src/retrieve.py`（beat优先）
- [x] 第 3 步：吉他节奏→鼓 MIDI 生成 `src/generate.py`（backbeat+重音跟随+hihat律动+velocity抖动）
- [ ] 第 3 步：接 LLM 分析吉他 riff → 生成候选 → 输出 .mid
