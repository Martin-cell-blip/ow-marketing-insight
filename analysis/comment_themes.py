# -*- coding: utf-8 -*-
"""B 站热评样本主题词频（2026-07 版，保留作历史）。

关键词命中只是初筛：不处理否定、引用和玩梗语境，不能直接解释为情绪或痛点。
2026-10 起改为 analyze_update.py 初筛 + code_comments_<日期>.py 逐条人工复核。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in
        (ROOT / "data" / "raw" / "bilibili_comments.jsonl").open(encoding="utf-8")]

themes = {
    "新手/萌新": r"新手|萌新|入坑|教学",
    "排位/匹配": r"排位|匹配|上分|段位|elo",
    "喷/环境": r"喷|骂|素质|挂机|演员|关闭聊天",
    "回归/国服": r"回归|国服|网易",
    "运营/活动": r"运营|活动|奖励|战令|皮肤",
    "平衡/版本": r"平衡|削|加强|版本|6v6|5v5|角斗",
    "情怀/爷青回": r"爷青|情怀|青春|回来了|十年",
}
print(f"total comments: {len(rows)}")
for k, pat in themes.items():
    hits = [r for r in rows if re.search(pat, r["comment"], re.I)]
    top = max(hits, key=lambda r: r["like"] or 0) if hits else None
    sample = f"{top['comment'][:46]} ({top['like']}赞)" if top else "-"
    print(f"{k}: {len(hits)} | top: {sample}")
