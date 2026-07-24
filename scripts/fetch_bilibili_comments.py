# -*- coding: utf-8 -*-
"""抓取热评样本（B 站公开 reply API）。

方法边界（如实标注）：匿名态（含 wbi 签名）只能取每视频前 3 条热评，
完整评论区需登录态——故本脚本按「热评样本」设计：每视频 3 条按点赞
排序的最高信号评论，用广视频池换取样本量。
选样：主题视频（回归|萌新|新手|排位|上分|劝退|入坑|匹配 全量）∪ 全站播放 TOP200。
输出: data/raw/bilibili_comments.jsonl（不存用户名，仅存文本/点赞/时间）
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "ow.duckdb"
OUT = ROOT / "data" / "raw" / "bilibili_comments.jsonl"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
THEME = r"回归|萌新|新手|排位|上分|劝退|入坑|匹配"

con = duckdb.connect(str(DB), read_only=True)
rows = con.execute("""
SELECT bvid, title, play FROM bili_videos
WHERE NOT is_spam_suspect
  AND regexp_matches(title || ',' || coalesce(tag,''), ?)
UNION
SELECT bvid, title, play FROM (
  SELECT bvid, title, play FROM bili_videos
  WHERE NOT is_spam_suspect ORDER BY play DESC LIMIT 200)
ORDER BY play DESC
""", [THEME]).fetchall()
print(f"target videos: {len(rows)}")

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
sess.get("https://www.bilibili.com/", timeout=15)

fetched_at = datetime.now(timezone.utc).isoformat()
n = 0
with OUT.open("w", encoding="utf-8") as f:
    for bvid, title, play in rows:
        try:
            view = sess.get("https://api.bilibili.com/x/web-interface/view",
                            params={"bvid": bvid}, timeout=20).json()
            aid = view.get("data", {}).get("aid")
        except Exception as e:
            print(f"[WARN] view {bvid}: {e}")
            continue
        if not aid:
            continue
        try:
            r = sess.get("https://api.bilibili.com/x/v2/reply",
                         params={"type": 1, "oid": aid, "pn": 1, "sort": 1},
                         timeout=20).json()
        except Exception as e:
            print(f"[WARN] reply {bvid}: {e}")
            continue
        for rep in (r.get("data") or {}).get("replies") or []:
            msg = (rep.get("content") or {}).get("message", "").strip()
            if not msg:
                continue
            f.write(json.dumps({
                "bvid": bvid, "video_title": title,
                "comment": re.sub(r"\s+", " ", msg)[:500],
                "like": rep.get("like"), "ctime": rep.get("ctime"),
                "fetched_at": fetched_at,
            }, ensure_ascii=False) + "\n")
            n += 1
        if n % 60 < 3:
            print(f"[..] {bvid} 累计 {n}")
        time.sleep(0.6)
print(f"DONE: {n} comments -> {OUT}")
