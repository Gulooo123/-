# -*- coding: utf-8 -*-
"""
bridge_la_to_gen.py —— LA 候选 → emo 生成池桥接
==============================================
la_feature.py 解析出的 la_features.json 是"检索用"的(只有特征),
但 groove_gen 的 pick_reference 需要 "source 含风格字段 + bars<=2 + parts".
本脚本从 la_features.json 里按特征捞"较像 emo 律动"的候选,
生成一个 la_gen_pool.json, 让 groove_gen 可以传 --pool la 使用。

用法 (la 链路完成后):
    python -X utf8 scripts/bridge_la_to_gen.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LA_FEAT = os.path.join(ROOT, "data", "la_features.json")
OUT = os.path.join(ROOT, "data", "la_gen_pool.json")


def main():
    if not os.path.exists(LA_FEAT):
        print(f"[skip] {LA_FEAT} 不存在 (先跑 src/la_feature.py)")
        return
    feats = json.load(open(LA_FEAT, encoding="utf-8"))
    print(f"LA 特征 {len(feats)} 首")

    # 对: density 0.4-0.9 (不太稀不太密), tempo 150-180 优先 (emo 提速)
    sel = []
    for f in feats:
        d = f["features"]["density"]
        t = f["tempo"]
        if 0.35 <= d <= 0.9 and 100 <= t <= 200:
            # 150-180 区间加分 (emo 主流)
            if 150 <= t <= 180:
                sel.append(f)
    sel.sort(key=lambda x: -abs(x["tempo"] - 165) < 10 and 1 or 0, reverse=True)  # 简化
    print(f"选出 {len(sel)} 首 (density 0.35-0.9, tempo 100-200)")

    if sel:
        with open(OUT, "w", encoding="utf-8") as fp:
            json.dump(sel, fp, ensure_ascii=False)
        print(f"-> {OUT}")
        # 展示 tempo 分布
        from collections import Counter
        print("tempo 分布:", dict(sorted(Counter(int(x["tempo"] // 10) * 10 for x in sel).items())))


if __name__ == "__main__":
    main()
