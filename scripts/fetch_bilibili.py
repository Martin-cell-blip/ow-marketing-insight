# -*- coding: utf-8 -*-
"""抓取 B 站守望先锋相关视频的搜索命中（web 搜索 API，公开无需登录）。

三种检索设计，全部写入同一个命中表（一行 = 一次命中，保留 设计/关键词/排序/窗口/页/位次）：
  replica   ：复刻 2026-07 基线——同 5 个关键词、综合排序、≤50 页。用于和 7 月比较样本组成。
  extension ：新增关键词（回坑/新手/新赛季/新英雄/中国赛区），综合排序、≤20 页。
  weekly    ：7-22 起按自然周切窗（pubtime_begin_s/pubtime_end_s），每窗每词综合排序取前 3 页。
              让「7 月以来新发视频」在各周都有样本，不被最近几天挤占；仍是检索样本，不是普查。
（曾试过按发布时间倒序翻页：「守望先锋」37 页只覆盖约 1 天，已放弃，见 fetch_log。）

同一 bvid 可被多个关键词命中；去重在分析阶段按 bvid 做，命中关键词全部保留。
用法：python fetch_bilibili.py [--designs replica,extension,weekly] [--append]
输出: data/snapshots/<日期>/bilibili_search_hits.jsonl + fetch_log.jsonl
"""
import argparse
import json
import re
import time
from datetime import datetime, timedelta

import requests

from snapshot import BJT, log_run, now_iso, snapshot_dir

KEYWORDS_JULY = ["守望先锋", "守望先锋2", "守望先锋 国服", "守望先锋 十周年", "OWCS"]
KEYWORDS_EXTRA = ["守望先锋 回坑", "守望先锋 新手", "守望先锋 新赛季", "守望先锋 血律", "OWCS 中国"]
KEYWORDS_WEEKLY = ["守望先锋", "守望先锋 国服", "OWCS", "守望先锋 回坑", "守望先锋 新手"]
WINDOW_START = datetime(2026, 7, 22, tzinfo=BJT)  # 7 月基线抓取日
DESIGNS = {
    "replica": (KEYWORDS_JULY, 50),
    "extension": (KEYWORDS_EXTRA, 20),
    "weekly": (KEYWORDS_WEEKLY, 3),
}
BASE = "https://api.bilibili.com/x/web-interface/search/type"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SLEEP = 1.0
TAG_RE = re.compile(r"<[^>]+>")


def clean(s):
    return TAG_RE.sub("", s or "")


def weeks(end):
    """[WINDOW_START, end) 按 7 天切窗，最后一窗截到 end。"""
    a = WINDOW_START
    while a < end:
        b = min(a + timedelta(days=7), end)
        yield a, b
        a = b


def get_page(sess, params):
    for wait in (0, 30, 90):  # -412 风控：两次退避后放弃该页
        time.sleep(wait)
        r = sess.get(BASE, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
    return {"code": f"http_{r.status_code}"}


def run_one(sess, f, design, kw, max_pages, window=None):
    params = {"search_type": "video", "keyword": kw}
    if window:
        params["pubtime_begin_s"] = int(window[0].timestamp())
        params["pubtime_end_s"] = int(window[1].timestamp()) - 1
    n_hits, pages_ok, failed, stop = 0, 0, [], "max_pages"
    for page in range(1, max_pages + 1):
        body = get_page(sess, {**params, "page": page})
        if body.get("code") != 0:
            failed.append({"page": page, "code": body.get("code")})
            stop = "api_error"
            break
        results = body.get("data", {}).get("result") or []
        if not results:
            stop = "no_more_results"
            break
        pages_ok += 1
        fetched_at = now_iso()
        for rank, v in enumerate(results, 1):
            if v.get("type") != "video":
                continue
            f.write(json.dumps({
                "design": design, "keyword": kw, "order": "totalrank",
                "window": [window[0].date().isoformat(), window[1].date().isoformat()] if window else None,
                "page": page, "rank": rank,
                "bvid": v.get("bvid"), "aid": v.get("id"), "title": clean(v.get("title")),
                "author": v.get("author"), "mid": v.get("mid"),
                "typename": v.get("typename"), "play": v.get("play"),
                "danmaku": v.get("danmaku"), "like": v.get("like"),
                "favorites": v.get("favorites"), "review": v.get("review"),
                "tag": v.get("tag"), "duration": v.get("duration"),
                "pubdate": v.get("pubdate"),
                "description": clean(v.get("description")),
                "fetched_at": fetched_at,
            }, ensure_ascii=False) + "\n")
            n_hits += 1
        time.sleep(SLEEP)
    return {"design": design, "keyword": kw, "window": [w.date().isoformat() for w in window] if window else None,
            "max_pages": max_pages, "pages_fetched": pages_ok, "hits": n_hits,
            "stop_reason": stop, "failed_pages": failed}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", default="replica,extension,weekly")
    ap.add_argument("--append", action="store_true", help="追加到已有命中表（续跑某个设计）")
    args = ap.parse_args()
    snap = snapshot_dir()
    end = datetime.fromisoformat(snap.name).replace(tzinfo=BJT) + timedelta(days=1)  # 截至快照日 24:00
    out = snap / "bilibili_search_hits.jsonl"
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    sess.get("https://www.bilibili.com/", timeout=15)  # 领 buvid cookie

    with out.open("a" if args.append else "w", encoding="utf-8") as f:
        for design in args.designs.split(","):
            kws, max_pages = DESIGNS[design]
            runs = []
            for kw in kws:
                for window in (list(weeks(end)) if design == "weekly" else [None]):
                    runs.append(run_one(sess, f, design, kw, max_pages, window))
                    f.flush()
                    r = runs[-1]
                    print(f"[{design}] {kw} {r['window'] or ''}: {r['hits']} hits, stop={r['stop_reason']}")
            log_run(snap, "bilibili_search", design=design, order="totalrank", runs=runs,
                    note="replica=复刻7月；extension=新增关键词；weekly=按周切窗每窗前3页；均为检索样本")
    print(f"DONE -> {out}")


if __name__ == "__main__":
    main()
