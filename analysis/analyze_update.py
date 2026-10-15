# -*- coding: utf-8 -*-
"""研究更新的计算层：7 月基线 vs 本次快照。只算数，不写结论。

输入
  data/raw/bilibili_videos.jsonl              7 月基线（2026-07-22 抓取，每个 bvid 只记了首个命中关键词）
  data/snapshots/<日期>/bilibili_search_hits.jsonl   本次检索命中（一行一次命中）
  data/snapshots/<日期>/bilibili_panel.jsonl         同一视频追踪面板
  data/snapshots/<日期>/bilibili_comments.jsonl      7 月以来视频的高赞评论样本
  data/snapshots/<日期>/fetch_log.jsonl              采集参数与成败
输出
  analysis/metrics_<日期>.json      全部数字与计算口径（看板、Word、Excel 都从这里取数）
  analysis/cleaning_audit_<日期>.md  清洗规则与保留/剔除抽样
  analysis/comment_screen_<日期>.csv 评论关键词初筛结果（人工复核列由 comment_review 填写）

口径约束（写在这里，看板照抄）：
  - 搜索结果是检索样本，不是全站总量；两次搜索的集合不同，不能互相做增减。
  - 累计播放受发布时长影响；跨发布时长的比较只在同一视频（面板）或同一发布时段内做。
  - 评论是每视频第一页高赞评论，只能说明「出现了什么说法」，不能估计比例。
"""
import csv
import json
import os
import random
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BJT = timezone(timedelta(hours=8))
SNAP_DAY = os.environ.get("OW_SNAPSHOT") or sorted(p.name for p in (ROOT / "data" / "snapshots").iterdir())[-1]
SNAP = ROOT / "data" / "snapshots" / SNAP_DAY
CUTOFF = datetime.fromisoformat(SNAP_DAY).replace(tzinfo=BJT)
# 7 月基线的抓取时刻取自原始记录的 fetched_at（2026-07-22T17:10Z = 北京时间 2026-07-23 01:10）
JULY_FETCH = datetime.fromisoformat(json.loads(
    (ROOT / "data" / "raw" / "bilibili_videos.jsonl").open(encoding="utf-8").readline())["fetched_at"]).astimezone(BJT)
WINDOW_START = datetime(2026, 7, 22, tzinfo=BJT)           # 「7 月以来新发」的下界
RETURN_DAY = datetime(2025, 2, 19, tzinfo=BJT)
OFFICIAL_MIDS = {1886758040: "守望先锋（官方视频号）", 365902357: "守望先锋电竞（官方账号）"}

# ---------- 清洗规则 v3（定义在 scripts/ow_rules.py，采集与分析共用） ----------
sys.path.insert(0, str(ROOT / "scripts"))
from ow_rules import OTHER_GAMES, OW_ROOT, OW_TERMS, is_ow, is_spam, title_has_ow  # noqa: E402


def ts(x):
    return datetime.fromtimestamp(x, BJT)


def load_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8")]


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)


# ---------- 主题规则（只看标题；标签常挂官方活动话题与「OWCS」等泛标签，不代表内容；允许重叠） ----------
THEMES = {
    "新英雄/新赛季": r"血律|D\.?Mon|第[五5]赛季|第[四4]赛季|新赛季|新英雄|黑影.{0,4}(支援|重做|辅助)|路霸.{0,4}重做|格里姆|暗红之律|釜山群英",
    "赛事": r"OWCS|冠军系列赛|全球总决赛|世界杯|季中冠军|WBG|JDG|微博电竞|Weibo Gaming|JD Gaming|All Gamers|赛段|职业选手|赛事",
    "回坑/新手/教学": r"回坑|回归|新手|萌新|入坑|教学|教程|攻略|上分|指南|怎么玩|零基础|入门",
    "搞笑/整活": r"搞笑|整活|名场面|神人|抽象|鬼畜|沙雕|逆天|节目效果|乐子",
    "活动/福利/外观": r"活动|福利|免费|白嫖|神话|皮肤|战令|联动|抽奖|领取|补给",
    "AI 生成": r"sora|(?<![A-Za-z])AI(?![A-Za-z])|AIGC|ai生成",
    "环境/吐槽": r"炸鱼|代练|外挂|开挂|演员|环境|劝退|吐槽|平衡|削弱|匹配机制",
}
THEMES = {k: re.compile(v, re.I) for k, v in THEMES.items()}

# 评论初筛主题（只做初筛；否定、引用、玩梗由人工复核判断）
C_THEMES = {
    "回归/回坑/离开": r"回坑|回归|退坑|弃坑|AFK|好久没玩|很久没玩|回来了|又回来",
    "新手/入坑": r"新手|萌新|入坑|新人|小白|刚玩",
    "组队/社交": r"组队|搭子|开黑|朋友|好友|队友|单排|一起玩",
    "环境/匹配": r"炸鱼|代练|外挂|开挂|演员|匹配|喷|骂|素质|环境",
    "新内容/改动": r"血律|D\.?Mon|黑影|路霸|重做|新英雄|新赛季|新地图|战令",
    "赛事/战队": r"OWCS|WBG|JDG|AG|总决赛|世界杯|比赛|战队|选手|广州",
    "福利/付费": r"免费|白嫖|神话|皮肤|氪|抽|礼包|福利|战令",
    "情怀/十年": r"情怀|青春|十年|当年|以前|老玩家|16年|2016",
}
C_THEMES = {k: re.compile(v, re.I) for k, v in C_THEMES.items()}


def main() -> None:
    m = {"snapshot": SNAP_DAY, "cutoff_bjt": SNAP_DAY,
         "baseline_fetched_bjt": JULY_FETCH.strftime("%Y-%m-%d %H:%M"), "window": [WINDOW_START.date().isoformat(), SNAP_DAY]}

    # ---------- 采集日志 ----------
    logs = load_jsonl(SNAP / "fetch_log.jsonl")
    m["fetch_log"] = logs

    # ---------- 7 月基线 ----------
    july = {r["bvid"]: r for r in load_jsonl(ROOT / "data" / "raw" / "bilibili_videos.jsonl")}
    for r in july.values():
        r["_clean"] = (not is_spam(r)) and is_ow(r)

    # ---------- 本次检索命中 → 视频 ----------
    hits = load_jsonl(SNAP / "bilibili_search_hits.jsonl")
    now = {}
    kw_of, design_of = defaultdict(set), defaultdict(set)
    for h in hits:
        now.setdefault(h["bvid"], h)
        kw_of[h["bvid"]].add(h["keyword"])
        design_of[h["bvid"]].add(h["design"])
    for b, r in now.items():
        r["keywords"] = sorted(kw_of[b])
        r["designs"] = sorted(design_of[b])
        r["_clean"] = (not is_spam(r)) and is_ow(r)
    # 本次快照的采集起止：取所有快照文件里逐条记录的 fetched_at
    stamps = [h["fetched_at"] for h in hits]
    for f in ("bilibili_panel.jsonl", "bilibili_comments.jsonl", "official_news_cn.jsonl", "verification_pages.jsonl"):
        stamps += [r.get("fetched_at") or r.get("fetched_now") for r in load_jsonl(SNAP / f)]
    stamps = sorted(stamps)
    m["snapshot_fetch_range"] = [stamps[0], stamps[-1]]

    # ---------- 清洗审计 ----------
    audit = {}
    for name, vids in (("july", july), ("now", now)):
        spam = [r for r in vids.values() if is_spam(r)]
        notow = [r for r in vids.values() if not is_spam(r) and not is_ow(r)]
        rescued = [r for r in vids.values() if not OW_ROOT.search(f"{r['title']},{r.get('tag') or ''}") and is_ow(r)]
        cross = [r for r in vids.values() if r["_clean"] and not title_has_ow(r) and OTHER_GAMES.search(r.get("tag") or "")]
        audit[name] = {"n_raw": len(vids), "r1_spam": len(spam), "r2_not_ow": len(notow),
                       "kept_cross_game_by_tag": len(cross),
                       "r2_rescued_by_terms": len(rescued), "n_clean": len(vids) - len(spam) - len(notow)}
        audit[name]["_samples"] = {
            "spam": spam[:12],
            "not_ow": random.Random(7).sample(notow, min(20, len(notow))),
            "rescued": rescued[:15],
            "kept_low_play": random.Random(7).sample([r for r in vids.values() if r["_clean"] and (r["play"] or 0) <= 100],
                                                     min(12, sum(1 for r in vids.values() if r["_clean"] and (r["play"] or 0) <= 100))),
        }
    write_audit(audit)
    m["cleaning"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in audit.items()}

    # ---------- A. 检索样本组成：7 月 vs 本次复刻设计 ----------
    rep = {b: r for b, r in now.items() if "replica" in r["designs"]}
    jc = {b for b, r in july.items() if r["_clean"]}
    rc = {b for b, r in rep.items() if r["_clean"]}

    def age_share(vids, keys, fetch, days):
        return pct(sum(1 for b in keys if fetch - ts(vids[b]["pubdate"]) <= timedelta(days=days)), len(keys))

    def by_month(vids, keys):
        c = Counter(ts(vids[b]["pubdate"]).strftime("%Y-%m") for b in keys)
        return c

    months = [f"{y}-{mm:02d}" for y in (2025, 2026) for mm in range(1, 13)
              if f"{y}-{mm:02d}" <= SNAP_DAY[:7]]
    jm, rm = by_month(july, jc), by_month(rep, rc)
    m["composition"] = {
        "july": {"n_raw": len(july), "n_clean": len(jc),
                 "share_pub_within_30d": age_share(july, jc, JULY_FETCH, 30),
                 "share_pub_within_90d": age_share(july, jc, JULY_FETCH, 90),
                 "share_pub_before_return": pct(sum(1 for b in jc if ts(july[b]["pubdate"]) < RETURN_DAY), len(jc))},
        "replica": {"n_raw": len(rep), "n_clean": len(rc),
                    "share_pub_within_30d": age_share(rep, rc, CUTOFF, 30),
                    "share_pub_within_90d": age_share(rep, rc, CUTOFF, 90),
                    "share_pub_before_return": pct(sum(1 for b in rc if ts(rep[b]["pubdate"]) < RETURN_DAY), len(rc))},
        "overlap_clean": len(jc & rc), "only_july_clean": len(jc - rc), "only_replica_clean": len(rc - jc),
        "only_replica_pub_before_window": sum(1 for b in rc - jc if ts(rep[b]["pubdate"]) < WINDOW_START),
        "by_pub_month": [{"m": mo, "july": jm.get(mo, 0), "replica": rm.get(mo, 0)} for mo in months],
    }

    # ---------- B. 同一视频面板 ----------
    panel = load_jsonl(SNAP / "bilibili_panel.jsonl") if (SNAP / "bilibili_panel.jsonl").exists() else []
    rows = [p for p in panel if p["status"] == "found" and (p["play_july"] or 0) > 0]
    buckets = [("发布≤30天", 0, 30), ("31–90天", 31, 90), ("91–365天", 91, 365), (">365天", 366, 10**5)]
    out = []
    for name, lo, hi in buckets:
        g = [p for p in rows if p["panel_reason"] == "random_sample"
             and lo <= (JULY_FETCH - ts(p["pubdate"])).days <= hi]
        ratios = [p["play_now"] / p["play_july"] for p in g]
        after = [(p["play_now"] - p["play_july"]) / p["play_now"] for p in g if p["play_now"]]
        out.append({"bucket": name, "n": len(g), "median_ratio": round(q(ratios, .5), 2) if g else None,
                    "p25_ratio": round(q(ratios, .25), 2) if g else None, "p75_ratio": round(q(ratios, .75), 2) if g else None,
                    "median_share_after_july": round(100 * q(after, .5), 1) if g else None})
    top10 = [{"bvid": p["bvid"], "title": p["title"], "play_july": p["play_july"], "play_now": p["play_now"],
              "ratio": round(p["play_now"] / p["play_july"], 2), "pub": ts(p["pubdate"]).date().isoformat()}
             for p in rows if p["panel_reason"] == "july_top10"]
    m["panel"] = {"n_requested": len(panel), "n_ok": sum(1 for p in panel if p["status"] == "found"),
                  "n_unavailable": sum(1 for p in panel if p["status"] != "found"),
                  "n_random_found": sum(1 for p in rows if p["panel_reason"] == "random_sample"),
                  "n_random": sum(1 for p in panel if p["panel_reason"] == "random_sample"),
                  # 检查「按标题能搜到」是否偏向热门视频：比较找到与未找到两组的 7 月播放
                  "median_play_july_found": int(st.median([p["play_july"] for p in panel if p["panel_reason"] == "random_sample" and p["status"] == "found"] or [0])),
                  "median_play_july_not_found": int(st.median([p["play_july"] for p in panel if p["panel_reason"] == "random_sample" and p["status"] != "found"] or [0])),
                  "fetched_now_range": [min((p["fetched_now"] for p in panel), default=None),
                                        max((p["fetched_now"] for p in panel), default=None)],
                  "by_age_at_july": out, "july_top10": sorted(top10, key=lambda x: -x["play_july"])}

    # ---------- C. 7 月以来新发视频（检索样本） ----------
    recent = {b: r for b, r in now.items() if r["_clean"] and ts(r["pubdate"]) >= WINDOW_START}
    # weekly 设计：每周窗口每词只取前 3 页，各周样本量由设计决定，不代表发布量
    wk = {b: r for b, r in recent.items() if "weekly" in r["designs"]}
    def win_of(r):
        return (WINDOW_START + timedelta(days=7 * ((ts(r["pubdate"]) - WINDOW_START).days // 7))).date().isoformat()
    by_win = defaultdict(list)
    for r in wk.values():
        by_win[win_of(r)].append(r)
    # 同窗口内播放百分位：只和同一周发布的视频比，去掉发布时长对累计播放的影响
    pctile = {}
    for w, g in by_win.items():
        g = sorted(g, key=lambda r: r["play"] or 0)
        for i, r in enumerate(g):
            pctile[r["bvid"]] = 100 * (i + 0.5) / len(g)
    m["recent"] = {"n_clean": len(recent), "n_weekly_sample": len(wk),
                   "weekly_windows": [{"start": w, "n": len(g)} for w, g in sorted(by_win.items())],
                   "by_keyword": dict(Counter(k for r in recent.values() for k in r["keywords"]).most_common())}
    theme_rows = []
    for th, rx in THEMES.items():
        g = [r for r in wk.values() if rx.search(r["title"])]
        ps = [pctile[r["bvid"]] for r in g]
        theme_rows.append({"theme": th, "n": len(g), "share": pct(len(g), len(wk)),
                           "median_pctile_in_week": round(st.median(ps), 1) if ps else None,
                           "examples": [r["title"][:30] for r in sorted(g, key=lambda r: -pctile[r["bvid"]])[:3]]})
    m["recent"]["themes"] = theme_rows
    m["recent"]["top_videos"] = [
        {"bvid": r["bvid"], "title": r["title"], "author": r["author"], "official": r["mid"] in OFFICIAL_MIDS,
         "title_has_ow": title_has_ow(r),
         "play": r["play"], "like": r["like"], "pub": ts(r["pubdate"]).date().isoformat(),
         "age_days": (CUTOFF - ts(r["pubdate"])).days,
         "themes": [th for th, rx in THEMES.items() if rx.search(r["title"])]}
        for r in sorted(recent.values(), key=lambda r: -(r["play"] or 0))[:12]]

    # ---------- D. 官方账号（按 mid） ----------
    acc = json.loads((SNAP / "bilibili_official_accounts.json").read_text(encoding="utf-8")) \
        if (SNAP / "bilibili_official_accounts.json").exists() else []
    m["official"] = {
        "accounts": acc,
        "in_july_sample_since_return": {str(mid): sum(1 for r in july.values() if r["mid"] == mid and r["_clean"]
                                                      and ts(r["pubdate"]) >= RETURN_DAY) for mid in OFFICIAL_MIDS},
        "in_recent_sample": {str(mid): sum(1 for r in recent.values() if r["mid"] == mid) for mid in OFFICIAL_MIDS},
        "recent_official_videos": [{"title": r["title"], "mid": r["mid"], "play": r["play"],
                                    "pub": ts(r["pubdate"]).date().isoformat()}
                                   for r in sorted(recent.values(), key=lambda r: -(r["play"] or 0)) if r["mid"] in OFFICIAL_MIDS][:15],
    }

    # ---------- E. 评论初筛 ----------
    cpath = SNAP / "bilibili_comments.jsonl"
    comments = load_jsonl(cpath) if cpath.exists() else []
    screen = []
    for i, c in enumerate(comments):
        th = [k for k, rx in C_THEMES.items() if rx.search(c["comment"])]
        screen.append({"cid": f"C{i+1:03d}", "bvid": c["bvid"], "video_title": c["video_title"][:40],
                       "like": c["like"], "comment": c["comment"], "screen_themes": "|".join(th)})
    with (ROOT / "analysis" / f"comment_screen_{SNAP_DAY}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(screen[0].keys()) if screen else ["cid"])
        w.writeheader()
        w.writerows(screen)
    m["comments"] = {"n": len(comments), "n_videos": len({c["bvid"] for c in comments}),
                     "screen_counts": {k: sum(1 for s in screen if k in s["screen_themes"].split("|")) for k in C_THEMES},
                     "n_any_theme": sum(1 for s in screen if s["screen_themes"])}
    # 人工复核：analysis/comment_review_<日期>.csv（cid, reviewed_themes 用 | 分隔, stance, note）
    rp = ROOT / "analysis" / f"comment_review_{SNAP_DAY}.csv"
    if rp.exists():
        rev = {r["cid"]: r for r in csv.DictReader(rp.open(encoding="utf-8-sig"))}
        by_id = {s["cid"]: s for s in screen}
        NONOW = "非OW内容"
        def rthemes(r):
            return [t for t in r["reviewed_themes"].split("|") if t and t != NONOW]
        themes_rev = Counter(t for r in rev.values() for t in rthemes(r))
        screen_fp = sum(1 for cid, r in rev.items() if by_id[cid]["screen_themes"] and not rthemes(r))
        screen_fn = sum(1 for cid, r in rev.items() if not by_id[cid]["screen_themes"] and rthemes(r))
        ex = defaultdict(list)
        for cid, r in rev.items():
            for t in rthemes(r):
                ex[t].append({"cid": cid, "like": int(by_id[cid]["like"] or 0), "stance": r["stance"],
                              "excerpt": by_id[cid]["comment"][:60], "video": by_id[cid]["video_title"], "note": r["note"]})
        m["comments"]["review"] = {
            "n_reviewed": len(rev), "n_with_signal": sum(1 for r in rev.values() if rthemes(r)),
            "n_non_ow": sum(1 for r in rev.values() if NONOW in r["reviewed_themes"]),
            "screen_hit_no_signal": screen_fp, "signal_missed_by_screen": screen_fn,
            "theme_counts": dict(themes_rev.most_common()),
            "stance_counts": dict(Counter(r["stance"] for r in rev.values()).most_common()),
            "examples": {t: sorted(v, key=lambda x: -x["like"])[:4] for t, v in ex.items()},
        }

    # ---------- F. 官方号 vs 其他账号：同周百分位 ----------
    def med_pct(sel):
        ps = [pctile[b] for b, r in wk.items() if sel(r)]
        return {"n": len(ps), "median": round(st.median(ps), 1) if ps else None}
    m["official_pctile"] = {"main": med_pct(lambda r: r["mid"] == 1886758040),
                            "esports": med_pct(lambda r: r["mid"] == 365902357),
                            "ugc": med_pct(lambda r: r["mid"] not in OFFICIAL_MIDS)}

    # ---------- G. 回归玩家相关标题、官方新手教学 ----------
    ret_rx = re.compile(r"回坑|回归|老玩家|退坑|AFK")
    ret = sorted((r for r in recent.values() if ret_rx.search(r["title"])), key=lambda r: -(r["play"] or 0))
    m["returning_titles"] = {"n": len(ret), "of": len(recent),
                             "titles": [{"title": r["title"], "play": r["play"], "pub": ts(r["pubdate"]).date().isoformat()}
                                        for r in ret]}
    tut = sorted((r for r in recent.values() if r["mid"] == 1886758040 and re.search(r"新手(英雄)?教学", r["title"])),
                 key=lambda r: r["pubdate"])
    m["official_tutorials"] = {"n": len(tut), "items": [{"title": r["title"], "play": r["play"],
                                                          "pub": ts(r["pubdate"]).date().isoformat()} for r in tut]}

    # ---------- H. 官网新闻（窗口内）与采集汇总 ----------
    news = load_jsonl(SNAP / "official_news_cn.jsonl")
    win_news = [r for r in news if r["list"] == "game_news" and r["source_date"] >= WINDOW_START.date().isoformat()]
    m["official_news_window"] = len(win_news)
    m["official_news_crackdown_posts"] = sum("环境净化" in r["title"] for r in win_news)
    m["fetch_summary"] = summarize_logs(logs, m)

    out_p = ROOT / "analysis" / f"metrics_{SNAP_DAY}.json"
    out_p.write_text(json.dumps(m, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"OK -> {out_p}")


def summarize_logs(logs, m):
    """把 fetch_log 压成看板上的一张采集情况表（同一来源取最后一次记录）。"""
    last = {}
    for r in logs:
        last[(r["source"], r.get("design") if r["source"] == "bilibili_search" else None)] = r
    out = []
    for (src, design), r in last.items():
        if src == "bilibili_search":
            runs = r.get("runs", [])
            failed = sum(len(x.get("failed_pages") or []) for x in runs)
            if design == "recent_pubdate_abandoned":
                out.append({"source": "B站搜索 · 按发布时间倒序（已放弃）", "status": "放弃", "ok": False,
                            "detail": "「守望先锋」50 页只回溯约 1–2 天，覆盖不了窗口；命中已删除"})
                continue
            out.append({"source": f"B站搜索 · {design}", "status": "完成" if not failed else f"失败页 {failed}",
                        "ok": not failed, "detail": f"{len(runs)} 组检索，{sum(x['hits'] for x in runs):,} 次命中，"
                                                   f"{sum(x['pages_fetched'] for x in runs)} 页"})
        elif src == "bilibili_panel" and r.get("status") == "failed":
            continue
        elif src == "bilibili_panel":
            out.append({"source": "B站同一视频面板", "status": "完成", "ok": True,
                        "detail": f"{r['n_panel']} 条目标，找到 {r['found']}，未找到 {r['not_found']}，请求错误 {r['errors']}；{r['method']}"})
        elif src == "bilibili_comments":
            out.append({"source": "B站热评", "status": "完成" if not r["failed"] else f"失败 {len(r['failed'])}",
                        "ok": not r["failed"], "detail": f"{r['videos_ok']}/{r['n_target_videos']} 个视频，{r['comments']} 条评论"
                                                         + ("；首轮选样漏了清洗规则（150 个视频仅 69 个是 OW），已修正重跑" if r.get("note") else "")})
        elif src == "official_news_cn":
            out.append({"source": "国服官网新闻", "status": "完成", "ok": True,
                        "detail": f"{r['items']} 条列表项，{r['bodies']} 篇正文"})
        elif src == "verification_pages":
            bad = [p for p in r["pages"] if p["error"]]
            out.append({"source": "核验页面（S14 地方媒体稿）", "status": "失败" if len(bad) == len(r["pages"]) else "完成",
                        "ok": len(bad) < len(r["pages"]),
                        "detail": "；".join(f"{p['id']} {p['error'] or 'ok'}" for p in r["pages"]) +
                                  "（检索当时已打开原文核验；存档抓取失败）" if bad else "已存档"})
        elif src == "liquipedia":
            out.append({"source": "Liquipedia（第三方）", "status": "完成", "ok": True,
                        "detail": f"{sum(1 for p in r['pages'] if p['http'] == 200)} 个页面"})
        elif src == "overfast":
            out.append({"source": "OverFast API（非官方）", "status": "完成", "ok": True,
                        "detail": f"{len(r['endpoints'])} 个接口"})
    out.append({"source": "B站官方号完整投稿列表", "status": "失败", "ok": False,
                "detail": "space/arc/search 匿名访问返回 -352 / -799 风控，未取得（F01）"})
    out.append({"source": "B站视频详情接口", "status": "失败", "ok": False,
                "detail": "view 接口当日持续 412；面板改用按标题检索、bvid 精确匹配"})
    return out


def write_audit(audit):
    L = [f"# 清洗审计（{SNAP_DAY}）\n",
         "规则 v3（7 月基线与本次快照用同一套规则重算）：",
         "- **R1 刷量短视频**：标签含其他激励计划 且 时长 ≤30 秒 且 标题以「守望先锋」开头、但标题标签里没有任何 OW 专有词（英雄名等）——即「守望先锋+其他游戏角色」的关键词堆砌。7 月版用的是「激励计划 + 播放≤100」，"
         "低播放本身不能证明是垃圾内容，已改为看标签与时长。",
         "- **R2 相关性**：标题/标签含 OW 词根（守望先锋/守望英雄/overwatch/owcs/ow2/独立 ow；不用裸「守望」，它会命中三角洲「极星守望」、《潮汐守望者》），或含高辨识度英雄/赛事名"
         "（源氏、末日铁拳、血律、D.Mon、OWL 等）。补词表是为了捞回只写英雄名的 OW 视频。",
         "- 低播放视频不剔除；下方附「低播放但保留」抽样供人工判断。\n"]
    for name, a in audit.items():
        L.append(f"## {'7 月基线' if name == 'july' else '本次快照'}：原始 {a['n_raw']} → 清洗后 {a['n_clean']}"
                 f"（R1 剔除 {a['r1_spam']}，R2 剔除 {a['r2_not_ow']}，词表捞回 {a['r2_rescued_by_terms']}）\n")
        for k, title in (("spam", "R1 剔除样本"), ("not_ow", "R2 剔除抽样（20 条）"),
                         ("rescued", "词表捞回样本"), ("kept_low_play", "低播放（≤100）但保留的抽样")):
            L.append(f"### {title}\n\n| bvid | 播放 | 时长 | 标题 | 标签 |\n|---|---|---|---|---|")
            for r in a["_samples"][k]:
                L.append(f"| {r['bvid']} | {r['play']} | {r.get('duration')} | {(r['title'] or '')[:36]} | {(r.get('tag') or '')[:50]} |")
            L.append("")
    (ROOT / "analysis" / f"cleaning_audit_{SNAP_DAY}.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
