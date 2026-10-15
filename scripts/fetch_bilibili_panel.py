# -*- coding: utf-8 -*-
"""同一视频追踪面板：对 7 月基线里的一批 bvid 重新取当前计数，并核验官方账号身份。

为什么要有它：两次搜索返回的视频集合不同，不能直接比较。只有「同一个 bvid 在两个时点的计数」
才能回答累计指标随发布时长增长多少。

面板构成（固定、可复跑）：
  - 7 月基线中 2025-02-19 以后发布的视频，按固定种子随机抽 600 条
  - 7 月看板展示过的 TOP10 视频与两个官方账号（按 mid）在基线中的回归后视频
取数方式：用视频标题调搜索接口，在第一页结果里按 bvid 精确匹配，读搜索卡片上的播放/点赞。
  7 月基线的计数同样来自搜索卡片，前后是同一个测量来源。
  （视频详情接口 /x/web-interface/view 在 2026-10-15 对本机 IP 持续返回 412 风控，未使用。）
  搜不到的视频记为 not_found，不补值。
官方账号：用 mid 调 card 接口取 Official 认证字段，不只依赖昵称。
输出: data/snapshots/<日期>/bilibili_panel.jsonl / bilibili_official_accounts.json
"""
import json
import random
import re
import time
from datetime import datetime

import requests

from snapshot import BJT, ROOT, log_run, now_iso, snapshot_dir

BASELINE = ROOT / "data" / "raw" / "bilibili_videos.jsonl"
OFFICIAL_MIDS = [1886758040, 365902357]  # 「守望先锋」「守望先锋电竞」，7 月数据中出现的 mid
SINCE = int(datetime(2025, 2, 19, tzinfo=BJT).timestamp())
N_SAMPLE, SEED = 600, 20261015
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SEARCH = "https://api.bilibili.com/x/web-interface/search/type"


def panel_targets(base):
    since = [r for r in base if (r["pubdate"] or 0) >= SINCE]
    picked = {r["bvid"]: "random_sample" for r in random.Random(SEED).sample(since, N_SAMPLE)}
    for r in base:
        if r["mid"] in OFFICIAL_MIDS and (r["pubdate"] or 0) >= SINCE:
            picked.setdefault(r["bvid"], "official_mid")
    # 7 月看板 TOP10 的口径：R1 非 spam + R2 含 OW 词根，回归后发布，按播放降序
    ow = re.compile(r"守望|overwatch|owcs|ow2|(?<![a-z])ow(?![a-z])", re.I)
    clean = [r for r in since if not ("创作者激励计划" in (r["tag"] or "") and r["play"] <= 100)
             and ow.search(f"{r['title']},{r['tag'] or ''}")]
    for r in sorted(clean, key=lambda r: -r["play"])[:10]:
        picked.setdefault(r["bvid"], "july_top10")
    return picked


def main() -> None:
    snap = snapshot_dir()
    base = [json.loads(l) for l in BASELINE.open(encoding="utf-8")]
    july = {r["bvid"]: r for r in base}
    picked = panel_targets(base)

    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    sess.get("https://www.bilibili.com/", timeout=15)

    accounts = []
    for mid in OFFICIAL_MIDS:
        c = sess.get("https://api.bilibili.com/x/web-interface/card", params={"mid": mid}, timeout=20).json()
        d = c.get("data") or {}
        card = d.get("card") or {}
        accounts.append({"mid": mid, "code": c.get("code"), "name": card.get("name"),
                         "official": card.get("Official"), "fans": card.get("fans"),
                         "archive_count": d.get("archive_count"), "fetched_at": now_iso()})
        time.sleep(1.0)
    (snap / "bilibili_official_accounts.json").write_text(
        json.dumps(accounts, ensure_ascii=False, indent=1), encoding="utf-8")

    found, missing, errors = 0, 0, []
    with (snap / "bilibili_panel.jsonl").open("w", encoding="utf-8") as f:
        for bvid, why in picked.items():
            j = july[bvid]
            query = re.sub(r"[【】\[\]（）()#|｜]", " ", j["title"])[:40]
            try:
                r = sess.get(SEARCH, params={"search_type": "video", "keyword": query, "page": 1}, timeout=20)
            except requests.exceptions.ConnectionError as e:  # 本机代理偶发断连，记下这一条继续
                errors.append({"bvid": bvid, "error": type(e).__name__})
                time.sleep(10)
                continue
            if r.status_code != 200:
                errors.append({"bvid": bvid, "error": f"http_{r.status_code}"})
                time.sleep(60)
                continue
            hit = next((v for v in (r.json().get("data") or {}).get("result") or [] if v.get("bvid") == bvid), None)
            f.write(json.dumps({
                "bvid": bvid, "panel_reason": why, "status": "found" if hit else "not_found",
                "title": j["title"], "mid": j["mid"], "pubdate": j["pubdate"],
                "play_july": j["play"], "like_july": j["like"], "fetched_july": j["fetched_at"],
                "play_now": hit.get("play") if hit else None, "like_now": hit.get("like") if hit else None,
                "danmaku_now": hit.get("danmaku") if hit else None,
                "fetched_now": now_iso(),
            }, ensure_ascii=False) + "\n")
            found += bool(hit)
            missing += not hit
            time.sleep(1.0)
    log_run(snap, "bilibili_panel", n_panel=len(picked), found=found, not_found=missing,
            errors=len(errors), error_samples=errors[:20], method="按标题搜索第一页、bvid 精确匹配，读搜索卡片计数",
            design=f"7月基线2025-02-19后发布随机{N_SAMPLE}条(seed={SEED})+官方mid+7月TOP10",
            note="视频详情接口 view 本日持续 412，未使用")
    print(f"panel {len(picked)}: found={found} not_found={missing} errors={len(errors)}")


if __name__ == "__main__":
    main()
