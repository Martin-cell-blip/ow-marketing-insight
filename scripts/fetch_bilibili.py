# -*- coding: utf-8 -*-
"""抓取 B 站守望先锋相关视频元数据（web 搜索 API，公开无需登录）。

每个关键词最多返回 50 页 x 20 条 = 1000 条；跨关键词按 bvid 去重。
输出: data/raw/bilibili_videos.jsonl（一行一条，含抓取时间戳）
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

KEYWORDS = [
    "守望先锋",
    "守望先锋2",
    "守望先锋 国服",
    "守望先锋 十周年",
    "OWCS",
]
BASE = "https://api.bilibili.com/x/web-interface/search/type"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "bilibili_videos.jsonl"
SLEEP = 0.5          # 礼貌限速
MAX_PAGES = 50       # API 上限

TAG_RE = re.compile(r"<[^>]+>")


def clean(s: str) -> str:
    return TAG_RE.sub("", s or "")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    sess.get("https://www.bilibili.com/", timeout=15)  # 领 buvid cookie

    seen: set[str] = set()
    fetched_at = datetime.now(timezone.utc).isoformat()
    n_rows = 0
    with OUT.open("w", encoding="utf-8") as f:
        for kw in KEYWORDS:
            for page in range(1, MAX_PAGES + 1):
                params = {"search_type": "video", "keyword": kw, "page": page}
                for attempt in range(3):
                    r = sess.get(BASE, params=params, timeout=20)
                    if r.status_code == 200:
                        break
                    time.sleep(5 * (attempt + 1))  # -412 风控退避
                else:
                    print(f"[WARN] {kw} p{page}: HTTP {r.status_code}, 跳过")
                    continue
                body = r.json()
                if body.get("code") != 0:
                    print(f"[WARN] {kw} p{page}: code={body.get('code')}, 停止该词")
                    break
                results = body.get("data", {}).get("result") or []
                if not results:
                    break
                for v in results:
                    if v.get("type") != "video" or v.get("bvid") in seen:
                        continue
                    seen.add(v["bvid"])
                    f.write(json.dumps({
                        "bvid": v.get("bvid"),
                        "title": clean(v.get("title")),
                        "author": v.get("author"),
                        "mid": v.get("mid"),
                        "typename": v.get("typename"),
                        "play": v.get("play"),
                        "danmaku": v.get("danmaku"),
                        "like": v.get("like"),
                        "favorites": v.get("favorites"),
                        "review": v.get("review"),
                        "tag": v.get("tag"),
                        "duration": v.get("duration"),
                        "pubdate": v.get("pubdate"),
                        "description": clean(v.get("description")),
                        "keyword": kw,
                        "fetched_at": fetched_at,
                    }, ensure_ascii=False) + "\n")
                    n_rows += 1
                time.sleep(SLEEP)
            print(f"[OK] {kw}: 累计去重后 {len(seen)} 条")
    print(f"DONE: {n_rows} rows -> {OUT}")


if __name__ == "__main__":
    main()
