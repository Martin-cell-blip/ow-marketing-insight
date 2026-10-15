# -*- coding: utf-8 -*-
"""抓取 Liquipedia OWCS 2026 中国赛区页面 wikitext（MediaWiki API）。

Liquipedia API 使用条款：须带说明性 UA，parse 请求 ≥30s 间隔。
第三方社区维基（非官方），用于赛程/赛果对照；官方口径以 ow.blizzard.cn 为准。
输出: data/snapshots/<日期>/liquipedia_<slug>.json
"""
import json
import time
from datetime import datetime, timezone

import requests

from snapshot import log_run, snapshot_dir

API = "https://liquipedia.net/overwatch/api.php"
UA = "OWMarketingInsight/0.1 (personal research project; contact: zhunmingm@gmail.com)"
PAGES = [
    "Overwatch_Champions_Series/2026/China/Stage_2",
    "Overwatch_Champions_Series/2026/China/Stage_3",
    "Overwatch_Champions_Series/2026/Midseason_Championship",
    "Overwatch_Champions_Series/2026/World_Finals",
]


def main() -> None:
    snap = snapshot_dir()
    status = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for i, page in enumerate(PAGES):
        if i:
            time.sleep(31)  # API 条款要求
        r = requests.get(API, params={
            "action": "parse", "page": page, "prop": "wikitext", "format": "json",
        }, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}, timeout=30)
        body = r.json() if r.status_code == 200 else {}
        status.append({"page": page, "http": r.status_code, "error": (body.get("error") or {}).get("code")})
        if r.status_code != 200 or "error" in body:
            print(f"[FAIL] {page}: {status[-1]}")
            continue
        slug = page.replace("/", "_").lower()
        (snap / f"liquipedia_{slug}.json").write_text(
            json.dumps({"_meta": {"fetched_at": fetched_at, "page": page},
                        "data": body}, ensure_ascii=False),
            encoding="utf-8")
        print(f"[OK] {page}")
    log_run(snap, "liquipedia", pages=status, note="第三方来源；parse 间隔 31s")


if __name__ == "__main__":
    main()
