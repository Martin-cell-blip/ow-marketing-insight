# -*- coding: utf-8 -*-
"""抓取《守望先锋》国服官网新闻列表与赛事官网新闻（公开页面，ow.blizzard.cn）。

列表页结构：/news/index.html、/news/index_2.html ...（与站内「加载更多」同一来源）。
每条记录：标题、摘要、来源发布日期（列表页 content-date）、URL；
对 2026-07-01 以后发布的条目再取正文文本，供核验具体主张。
输出: data/snapshots/<日期>/official_news_cn.jsonl、verification_pages.jsonl
"""
import html
import json
import re
import sys
import time

import requests

from snapshot import log_run, now_iso, snapshot_dir

LISTS = [
    ("game_news", "https://ow.blizzard.cn/news/", 8),     # 最多翻 8 页
    ("owcs_news", "https://ow.blizzard.cn/owcs/news/", 1),
]
BODY_SINCE = "2026-07-01"
# 官网之外、用于核验具体主张的公开页面（保存正文与采集时间，便于回查）
VERIFY_PAGES = [
    ("S14", "https://guangzhoubaiyun.gz-cmc.com/pages/2026/09/24/97eaee2b43f44786a85d8dbee9468fc9.html"),
    ("S14", "https://m.163.com/game/article/L7JJD3FK0525JO75.html"),  # 同一篇白云融媒稿的网易号转载
]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ITEM = re.compile(r'class="list-item-container".*?content-title">(.*?)</div>.*?content-intro">(.*?)</div>'
                  r'.*?content-date">(.*?)</div>.*?href="([^"]+)"', re.S)
OWCS_ITEM = re.compile(r'<a[^>]+href="([^"]*owcs/news/(\d{8})/[^"]+)"[^>]*>(.*?)</a>', re.S)


def text_of(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", "\n", s))
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def get(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def fetch_verify_pages(snap) -> None:
    rows = []
    for sid, url in VERIFY_PAGES:
        try:
            body, err = text_of(get(url))[:8000], None
        except requests.exceptions.RequestException as e:  # 地方媒体站点偶发超时，记下失败
            body, err = None, type(e).__name__
        rows.append({"source_id": sid, "url": url, "body_text": body, "error": err, "fetched_at": now_iso()})
    with (snap / "verification_pages.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log_run(snap, "verification_pages", pages=[{"id": r["source_id"], "error": r["error"]} for r in rows])
    print("verify:", [(r["source_id"], r["error"] or "ok") for r in rows])


def main() -> None:
    snap = snapshot_dir()
    if "--verify-only" in sys.argv:
        fetch_verify_pages(snap)
        return
    items, pages = {}, []
    for kind, base, max_pages in LISTS:
        for p in range(1, max_pages + 1):
            url = base if p == 1 else f"{base}index_{p}.html"
            page = get(url)
            found = 0
            if kind == "game_news":
                for t, intro, d, href in ITEM.findall(page):
                    items.setdefault(href, {"list": kind, "title": text_of(t), "intro": text_of(intro),
                                            "source_date": d.strip(), "url": href})
                    found += 1
            else:
                for href, d8, inner in OWCS_ITEM.findall(page):
                    t = text_of(inner).split("\n")[0]
                    items.setdefault(href, {"list": kind, "title": t, "intro": "",
                                            "source_date": f"{d8[:4]}-{d8[4:6]}-{d8[6:]}", "url": href})
                    found += 1
            pages.append({"url": url, "items": found})
            time.sleep(1.0)

    n_body = 0
    with (snap / "official_news_cn.jsonl").open("w", encoding="utf-8") as f:
        for it in sorted(items.values(), key=lambda x: x["source_date"], reverse=True):
            if it["source_date"] >= BODY_SINCE:
                if "ow.blizzard.cn" not in it["url"]:  # 列表里混有商城等外链，不抓正文
                    it["body_text"] = None
                    it["body_note"] = "external_link"
                else:
                    it["body_text"] = text_of(get(it["url"]))[:8000]
                    n_body += 1
                    time.sleep(1.0)
            it["fetched_at"] = now_iso()
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    log_run(snap, "official_news_cn", list_pages=pages, items=len(items), bodies=n_body,
            note="source_date=官网列表标注的发布日期（来源发布时间），不是事件发生时间")
    print(f"items={len(items)} bodies={n_body}")
    fetch_verify_pages(snap)


if __name__ == "__main__":
    main()
