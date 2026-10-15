# -*- coding: utf-8 -*-
"""抓取热评样本（B 站公开 reply API，匿名态）。

方法边界：匿名态每视频只稳定拿到第一页按热度排序的评论（7 月实测为前 3 条，本次以实际返回为准），
完整评论区需登录态，本项目不使用登录态。所以这是「高赞评论样本」，不能估计全体玩家的痛点比例。

选样（基于本次快照的搜索命中，按 bvid 去重，先过清洗规则 v3——只取 OW 相关视频）：
  - 7 月以来（pubdate >= 2026-07-22）发布、**标题**命中玩家需求主题词的视频（标签常挂泛话题，不用）
  - 同窗口内播放最高的 60 条
  合计上限 150 条：主题视频按播放降序优先，余量由播放 TOP 补足。
（首轮版本漏了清洗规则，150 个目标里只有 69 个是 OW 视频，已重跑，见 fetch_log。）
不存用户名/用户 ID，只存文本、点赞、回复数、时间。
输出: data/snapshots/<日期>/bilibili_comments.jsonl
"""
import json
import re
import time
from datetime import datetime

import requests

from ow_rules import is_ow, is_spam
from snapshot import BJT, log_run, now_iso, snapshot_dir

THEME = re.compile(r"回归|回坑|退坑|萌新|新手|入坑|排位|匹配|劝退|新赛季|血律|黑影|路霸|组队|搭子")
WINDOW_START = int(datetime(2026, 7, 22, tzinfo=BJT).timestamp())
N_TOP, CAP = 60, 150
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def main() -> None:
    snap = snapshot_dir()
    vids = {}
    for line in (snap / "bilibili_search_hits.jsonl").open(encoding="utf-8"):
        h = json.loads(line)
        if (h["pubdate"] or 0) >= WINDOW_START and is_ow(h) and not is_spam(h):
            vids.setdefault(h["bvid"], h)
    recent = sorted(vids.values(), key=lambda v: -(v["play"] or 0))
    theme = [v for v in recent if THEME.search(v["title"])]
    targets = {v["bvid"]: v for v in theme[:CAP - N_TOP]}
    for v in recent:
        if len(targets) >= CAP:
            break
        targets.setdefault(v["bvid"], v)
    targets = list(targets.values())

    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    sess.get("https://www.bilibili.com/", timeout=15)

    n, ok, empty, failed = 0, 0, 0, []
    with (snap / "bilibili_comments.jsonl").open("w", encoding="utf-8") as f:
        for v in targets:
            try:
                r = sess.get("https://api.bilibili.com/x/v2/reply",
                             params={"type": 1, "oid": v["aid"], "pn": 1, "sort": 1}, timeout=20)
            except requests.exceptions.ConnectionError as e:  # 本机代理偶发断连，记下这一条继续
                failed.append({"bvid": v["bvid"], "code": type(e).__name__})
                time.sleep(10)
                continue
            body = r.json() if r.status_code == 200 else {"code": f"http_{r.status_code}"}
            if body.get("code") != 0:
                failed.append({"bvid": v["bvid"], "code": body.get("code")})
                time.sleep(30 if r.status_code == 412 else 1.5)
                continue
            reps = (body.get("data") or {}).get("replies") or []
            ok += 1
            empty += not reps
            for rank, rep in enumerate(reps, 1):
                msg = (rep.get("content") or {}).get("message", "").strip()
                if not msg:
                    continue
                f.write(json.dumps({
                    "bvid": v["bvid"], "video_title": v["title"], "video_play": v["play"],
                    "video_pubdate": v["pubdate"], "selected_by": "theme" if THEME.search(v["title"]) else "top_play",
                    "rank": rank, "comment": re.sub(r"\s+", " ", msg)[:500],
                    "like": rep.get("like"), "rcount": rep.get("rcount"), "ctime": rep.get("ctime"),
                    "fetched_at": now_iso(),
                }, ensure_ascii=False) + "\n")
                n += 1
            time.sleep(1.5)
    log_run(snap, "bilibili_comments", n_target_videos=len(targets), videos_ok=ok,
            videos_no_comments=empty, failed=failed, comments=n,
            n_theme_targets=sum(1 for v in targets if THEME.search(v["title"])),
            design=f"清洗后OW视频；窗口>=2026-07-22；标题主题词视频优先(≤{CAP - N_TOP})+播放TOP补足，上限{CAP}；匿名 reply sort=1 第一页",
            note="替换首轮结果：首轮未过清洗规则，150 个目标视频中仅 69 个为 OW 相关")
    print(f"targets={len(targets)} ok={ok} failed={len(failed)} comments={n}")


if __name__ == "__main__":
    main()
