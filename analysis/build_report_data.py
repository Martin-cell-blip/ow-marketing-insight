# -*- coding: utf-8 -*-
"""研究判断层：把计算结果、来源表和人工判断合成 report/data.json（看板、Word、Excel 共用）。

数字一律从 analysis/metrics_<日期>.json 取，判断文字里不手写数字；
证据强度三档：事实 / 推断 / 待验证假设。来源 ID 见 analysis/evidence_sources.json。
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP_DAY = os.environ.get("OW_SNAPSHOT") or sorted(p.name for p in (ROOT / "data" / "snapshots").iterdir())[-1]
SNAP = ROOT / "data" / "snapshots" / SNAP_DAY
M = json.loads((ROOT / "analysis" / f"metrics_{SNAP_DAY}.json").read_text(encoding="utf-8"))
SRC = json.loads((ROOT / "analysis" / "evidence_sources.json").read_text(encoding="utf-8"))


def fmt(n):
    return f"{n / 1e4:.1f} 万" if n >= 1e4 else f"{n:,}"


# ---------- 来源表：补采集时间 ----------
def fetched_at_of(s):
    f = s.get("snapshot_file")
    if not f:
        return None
    p = SNAP / f
    if f.endswith(".jsonl"):
        for line in p.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("url") == s["url"]:
                return r["fetched_at"]
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(d, list):
        return d[0].get("fetched_at")
    return d["_meta"]["fetched_at"]


for s in SRC:
    s["fetched_at"] = fetched_at_of(s)

# ---------- 常用数字 ----------
comp, pan, rec, off, cm = M["composition"], M["panel"], M["recent"], M["official"], M["comments"]
cj, cr = comp["july"], comp["replica"]
acc = {a["mid"]: a for a in off["accounts"]}
main_acc, esp_acc = acc[1886758040], acc[365902357]
th = {t["theme"]: t for t in rec["themes"]}
pct_off = M["official_pctile"]
age = {b["bucket"]: b for b in pan["by_age_at_july"]}
young, old = pan["by_age_at_july"][0], pan["by_age_at_july"][-1]
ret_titles = M["returning_titles"]
tut = M["official_tutorials"]
news_n = M["official_news_window"]
rv = cm.get("review", {})

meta = {
    "title": f"守望先锋 B 站内容与玩家信号 · 研究更新（截至 {SNAP_DAY}）",
    "h1": f"《守望先锋》<span class=\"thin\">·</span> B 站内容与玩家信号<br><span class=\"hl\">研究更新</span> <span class=\"thin\">截至</span> <span class=\"hl num\">{SNAP_DAY}</span>",
    "sub": (f"在 2026-07 基线之上重新采集：<b>国服官网 7 月以来 {news_n} 条新闻 × B 站三种检索设计 × 同一视频追踪面板 × 高赞评论人工复核</b>。"
            "回答三个问题：7 月以来变了什么、玩家在意什么、哪些值得做成内容和实验。"),
    "cutoff": SNAP_DAY, "baseline_fetch": M["baseline_fetched_bjt"],
    "baseline_note": "7 月原报告按当地时间记为 2026-07-22",
    "snapshot_fetch": f"{M['snapshot_fetch_range'][0][:10]} {M['snapshot_fetch_range'][0][11:16]}–{M['snapshot_fetch_range'][1][11:16]}",
    "author": "马准名",
}

stats = [
    {"v": f"{M['cleaning']['now']['n_clean']:,}", "unit": "", "k": "本次检索样本中的 OW 视频（清洗后，去重）"},
    {"v": f"{rec['n_clean']:,}", "unit": "", "k": "其中 2026-07-22 以来发布"},
    {"v": f"{sum(1 for s in SRC if s['id'].startswith('S'))}", "unit": "条", "k": "打开原文核验的来源（官方为主）"},
    {"v": f"{pan['n_random_found']}", "unit": "条", "k": "同一视频追踪面板（随机样本命中）"},
]

toc = [("find", "核心发现"), ("tl", "节点"), ("fix", "旧结论核验"), ("sample", "样本口径"), ("panel", "同一视频"),
       ("recent", "新发内容"), ("voice", "玩家之声"), ("seg", "人群"), ("rec", "建议与指标"), ("topics", "内容选题"),
       ("method", "方法与来源")]

leads = {
    "find": "每条按「事实 / 推断 / 待验证假设」标注证据强度。事实可回到原始记录或官方原文；推断有数据支撑但存在其他解释；待验证假设需要新的数据才能成立。",
    "timeline": "只列已打开原文核验的节点。事件时间与来源发布时间分开标；斜纹卡片为截至研究截止日仍在进行或尚未开始的节点。",
    "corrections": "先核验 7 月版的说法，不预设旧建议正确。改动原因多数是口径问题：把检索样本当总量、把不同发布时长的累计播放直接比较、证据没有留存原始记录。",
    "composition": (f"7 月与 10 月用同样的 5 个关键词、同样的综合排序和翻页上限各抓一次。两次清洗后各约 {cj['n_clean']:,} / {cr['n_clean']:,} 条，"
                    f"但同时出现在两次样本里的只有 <b>{comp['overlap_clean']:,} 条</b>——两次拿到的基本是两批视频。"),
    "panel": (f"把 7 月样本里固定种子抽出的 {pan['n_random']} 条视频按标题重新检索、按 bvid 精确匹配，读当前计数（与 7 月同一测量来源），"
              f"找回 {pan['n_random_found']} 条。<b>找回的视频偏热门</b>：它们 7 月播放中位数 {pan['median_play_july_found']:,}，"
              f"未找回的只有 {pan['median_play_july_not_found']:,}，所以下面的倍数代表「能被搜到的视频」，不代表全部。"),
    "recent": (f"用按周切窗的检索（每周每词取前 3 页）取 7-22 以来的新发视频，共 {rec['n_weekly_sample']:,} 条。"
               "主题按标题规则归类（可重叠）；播放只和<b>同一周发布</b>的视频比，用百分位表示，去掉发布时长的影响。"),
    "voice": (f"从 7 月以来的 OW 视频里，按标题优先选玩家需求相关的视频，取匿名可见的第一页热评，共 {cm['n']} 条、{cm['n_videos']} 个视频。"
              "关键词只做初筛，主题与立场逐条人工复核。"),
    "segments": "人群划分是分析框架，不是真实用户画像。只为有证据的人群写阻力与主张；证据不足的部分明确写出。",
    "priority": "建议是基于证据的判断，尚未验证。指标分两套：有官方后台时用的北极星，以及个人只有公开数据时的代理指标——后者不能证明回流、留存或付费。",
    "topics": "优先选个人用录屏 + 旁白 + 字幕能做出来的选题。游戏观点、个人经历必须由作者本人提供或确认，脚本不代写。",
    "method": "采集参数、成败、清洗规则与全部来源都在下面；原始数据在 data/snapshots/ 与 data/raw/，可复跑。",
}

# ---------- 核心发现 ----------
findings = [
    {
        "title": "官方在 7 月后明显加码「新玩家承接」；检索样本里讲给回归玩家的内容很少",
        "strength": "事实",
        "fact": (f"官网：8-12 起新玩家高级战令半价（S03），10-07 起注册不足 60 天的新玩家可免费领满级神话皮肤（S10）。"
                 f"B 站官方号在 8 月中下旬和 10-08 至 10-10 分两批发布「新手英雄教学」，检索样本里已见 {tut['n']} 条。"
                 f"同期对回归玩家有用的机制也存在：第5赛季往期战令返场且进度继承（S09），嘉年华神话代券（S07，已于 10-06 截止）。"
                 f"但 7 月以来 {rec['n_clean']:,} 条新发视频里，标题提到回坑/回归/老玩家的只有 {ret_titles['n']} 条。"),
        "interpretation": "官方资源向「全新玩家」倾斜，回归玩家能用的机制分散在赛季公告里，没人把它们按回归玩家的视角串起来讲。评论里有人自述「玩得越来越少、看得越来越多」「脱坑很久仍爱看」，说明 B 站上存在仍在看内容的离开玩家，是这类讲述的潜在观众。",
        "alternatives": "回归玩家可能不需要专门内容（直接看赛季预览即可）；B 站标题不写「回坑」不等于视频不服务回归玩家；检索样本也可能漏掉了这类视频。",
        "meaning": "这是个人和官方都能补的内容缺口：把「往期战令进度还在、离开期间多了哪些英雄、哪些福利已截止」按离开时长讲清楚，成本低、可核验。",
        "next": "做一条回坑补课视频验证需求（见内容选题 01）；用评论里的提问类型判断回归玩家最卡在哪。",
    },
    {
        "title": "两次检索样本都偏向最近一个月，7 月版的「月度热度曲线」不成立",
        "strength": "事实",
        "fact": (f"7 月样本中 {cj['share_pub_within_30d']}% 的视频发布于抓取前 30 天内；10 月复刻抓取为 {cr['share_pub_within_30d']}%。"
                 f"两次清洗后样本只重叠 {comp['overlap_clean']:,} 条。7 月报告里「2026-07 供给峰值」「三次抬升」来自同一类按发布月汇总的累计播放。"
                 f"同一视频追踪面板显示：7 月时发布不足 30 天的视频，到 10 月播放中位涨到 {young['median_ratio']} 倍；发布超过一年的只涨到 {old['median_ratio']} 倍。"),
        "interpretation": "B 站综合排序偏爱新视频，所以无论哪天抓，最近一个月都会显得最「热」。这是采样方式造成的形状，不是生态趋势。",
        "alternatives": "也可能确实存在近期供给增长，但两次搜索的结果无法区分这两种情况；要回答它需要固定口径的连续采样（例如每周同一时刻的按周切窗检索）。",
        "meaning": "对营销监测的直接含义：不要用「搜到多少条、总播放多少」做热度 KPI。要比，就固定窗口、固定关键词、按同周百分位比。",
        "next": "保留本次按周切窗设计，每周同一时间复跑一次，积累可比的时间序列。",
    },
    {
        "title": "放在同一周里比，官方号视频排在前列；7 月「官方电竞号不如 UGC」的结论反转",
        "strength": "推断",
        "fact": (f"按周切窗样本中，官方视频号视频的同周播放百分位中位数为 {pct_off['main']['median']}（n={pct_off['main']['n']}），"
                 f"官方电竞号为 {pct_off['esports']['median']}（n={pct_off['esports']['n']}），其他账号为 {pct_off['ugc']['median']}。"
                 f"官方视频号投稿总数 {main_acc['archive_count']}，7 月报告里「只发了 15 条」是它在检索样本里出现的次数（S17）。"),
        "interpretation": "7 月用的是「所有视频累计播放的平均值」，被少数爆款 UGC 和发布时长差异拉偏；控制同周发布后，官方内容并不弱。",
        "alternatives": "官方视频本身更容易被检索排到前三页，百分位是在检索样本内部算的，不等于全站排名；官方样本量也小。",
        "meaning": "「官方缺供给 / 缺形态」的旧判断不能再用。更有价值的问题是官方已有的新手教学和英雄预览，能否被 UGC 接住、转述给回归和新玩家。",
        "next": "需要时可补一轮：按官方 mid 拿完整投稿列表（本次被风控拒绝），与 UGC 同周对比。",
    },
    {
        "title": "新英雄与外观内容在同周更突出；赛事回放多但单条播放偏低",
        "strength": "推断",
        "fact": (f"按标题归类：新英雄/新赛季占样本 {th['新英雄/新赛季']['share']}%，同周百分位中位 {th['新英雄/新赛季']['median_pctile_in_week']}；"
                 f"活动/福利/外观 {th['活动/福利/外观']['share']}%，中位 {th['活动/福利/外观']['median_pctile_in_week']}；"
                 f"赛事 {th['赛事']['share']}%，中位 {th['赛事']['median_pctile_in_week']}。"),
        "interpretation": "版本节点（D.Mon、血律、皮肤）带动注意力；赛事内容以逐场回放为主，供给被切碎，单条难以出头。",
        "alternatives": "「OWCS」是 5 个检索词之一，会抬高赛事占比；赛事的主要消费在直播端，回放播放不能代表赛事热度；标题规则会漏判。",
        "meaning": "做赛事相关内容，与其再发一条回放，不如做「给不看比赛的人的入口」类讲解；版本节点仍是最稳的流量窗口。",
        "next": "总决赛前用同一套同周百分位跟踪「赛事讲解类」与「回放类」的差异（待验证）。",
    },
    {
        "title": "10 月到 12 月集中了三个线下与赛事节点",
        "strength": "事实",
        "fact": ("城市挑战者秋季赛不限段位、22 城，城市赛 10-25 至 12-26（S11）；OWCS 中国赛区第三赛段 10-03 至 11-08（S15，第三方）；"
                 "全球总决赛 12-02 至 12-06 在广州，12-04 起在广州体育馆（S14，地方媒体与第三方一致，未见主办方原文）。"),
        "interpretation": "对回归玩家与赛事观众，这是一年里「有理由回来看看」的集中时段，且有线下落点。",
        "alternatives": "节点密集不代表需求同步上升；总决赛场馆信息仍需等主办方公告最终确认。",
        "meaning": "个人实验与内容发布宜在 11 月中旬前完成预热，总决赛周集中发布，而不是全年平均用力。",
        "next": "按 09 节的小规模实验执行；主办方公告发布后更新 S14 来源。",
    },
]

# ---------- 时间线 ----------
def src(i):
    return next(s for s in SRC if s["id"] == i)


timeline = [
    {"event_time": "2026-07-29 至 08-02", "title": "季中冠军赛 · 巴黎", "detail": "16 队；国服赛区第二阶段冠军 WBG 出战（官方电竞号有其小组赛回放）", "source_id": "S13"},
    {"event_time": "2026-08-12", "title": "第4赛季：D.Mon 上线 + 战令改版", "detail": "战令改为可自选升级路线；同日新玩家高级战令半价", "source_id": "S01"},
    {"event_time": "2026-09-09 至 10-11", "title": "璀璨系列赛 S3", "detail": "全段位免费参赛，16 强争 10 万元，可获职业队试训资格", "source_id": "S06"},
    {"event_time": "2026-09-13 至 10-06", "title": "暴雪嘉年华：血律公布 + 全员神话代券", "detail": "完成一局即可兑换第1–14赛季任一神话礼包（已截止）", "source_id": "S07"},
    {"event_time": "2026-09-23 起", "title": "竞逐环境治理升级", "detail": "代练双方并罚、炸鱼小号连坐；第1赛季以来禁赛 30,776 个账号（官方自报）", "source_id": "S08"},
    {"event_time": "2026-10-07", "title": "第5赛季：血律 + 黑影转支援 + 往期战令返场", "detail": "往期战令可从当时进度继续；新玩家 60 天内领满级神话", "source_id": "S09"},
    {"event_time": "2026-10-25 至 12-26", "title": "城市挑战者秋季赛", "detail": "不限段位，22 城，经官方小程序报名", "source_id": "S11", "future": True, "status": "未开始"},
    {"event_time": "2026-10-03 至 11-08", "title": "OWCS 中国赛区第三赛段", "detail": "8 队，奖金池 70 万元（第三方维基）", "source_id": "S15", "future": True, "status": "进行中"},
    {"event_time": "2026-12-02 至 12-06", "title": "OWCS 全球总决赛 · 广州", "detail": "12-04 至 06 在广州体育馆 1 号馆", "source_id": "S14", "future": True, "status": "未开始"},
]
for n in timeline:
    s = src(n["source_id"])
    n["source_type"] = "官方" if s["source_type"] == "官方" else s["source_type"].split("（")[0]
    n["source_published"] = s["source_published"]

# ---------- 旧结论核验 ----------
corrections = [
    {"old": "标题「国服回归 500 天」", "status": "修正",
     "why": "7 月数据窗口 2025-02-19 至 2026-07-22 实为 518 天；本版改为带截止日期的标题。"},
    {"old": "月度视频数与播放曲线：回归首月冲高、下半年回落、2026 年三次抬升", "status": "撤下",
     "why": f"按发布月汇总的是单次抓取的累计播放，且检索样本偏向近期（{cj['share_pub_within_30d']}% / {cr['share_pub_within_30d']}% 发布于抓取前 30 天）。曲线形状主要由采样造成。"},
    {"old": "官方主号单条均值是 UGC 的 3.3 倍，但只发了 15 条", "status": "修正",
     "why": f"15 是检索样本里出现的条数；按 mid 核验，官方视频号投稿共 {main_acc['archive_count']} 条（S17）。均值比较混入不同发布时长，改用同周百分位。"},
    {"old": "官方电竞号单条均值 3.9 万，低于 UGC 大盘", "status": "修正",
     "why": f"同周百分位下官方电竞号中位 {pct_off['esports']['median']}，高于其他账号的 {pct_off['ugc']['median']}；旧结论被少数 UGC 爆款拉高的均值误导。"},
    {"old": "TOP10 爆款里 AI 二创、女团联动、角色叙事「各占一席，爆款要素换代」", "status": "修正",
     "why": f"TOP10 混合了 17 个月内不同发布时长的视频，且「ow神人转场」被规则误标为 AI。7 月以来的按周样本中，标题含 AI 的视频 {th['AI 生成']['n']} 条（{th['AI 生成']['share']}%），不足以称为趋势。"},
    {"old": "「守望先锋英雄召集」等官方话题标签出现 1,244 次，渗透率真实", "status": "修正",
     "why": "这些是投稿者参与官方活动时挂的话题标签，标签计数反映检索样本里的参与情况，不能代表渗透率。"},
    {"old": "小红书「找搭子」主流、规则吐槽 75–149 赞、坦诚沟通 106 赞等玩家之声数字", "status": "撤下",
     "why": "项目内没有留存这些数字的原始记录，本轮也未重新采集小红书与知乎，无法回溯，不再展示。"},
    {"old": "全球总决赛 2026-12-02 至 06 在中国举办", "status": "保留",
     "why": "日期一致，并补充城市与场馆：广州、广州体育馆（S14）。主办方原文仍待找到。"},
    {"old": "国服合作战队为 WBG / JDG / AG", "status": "保留", "why": "国服赛事官网 7-16 观赛指南确认（S13）。"},
    {"old": "建议：回归玩家数据年报 H5（依据：LoL/Dota2 生态对比显示 OW 官方数据内容近乎空白）", "status": "撤下",
     "why": "README 称样本清单在 analysis/，实际不存在；依据无法核验。"},
    {"old": "建议：官方 AI 二创征集赛（依据：TOP1 为 sora2 视频）", "status": "撤下", "why": "单条视频不构成趋势证据，见上。"},
    {"old": "建议：赛事二创共创企划，北极星 = 话题二创投稿数/周", "status": "修正",
     "why": "方向保留为待验证假设；投稿数容易被灌水，且需要官方授权，个人无法执行。本版改为个人可执行的总决赛前小规模实验（09 节）。"},
]

charts = {
    "composition_desc": "按发布月份统计两次检索样本的视频数，两次都在各自抓取月份达到最高。",
    "composition_caption": (f"<b>两次样本都在「自己抓取的那个月」最高。</b>7 月样本最高在 2026-07，10 月样本最高在 2026-10（只过了半个月）。"
                            f"这说明柱子高低主要反映检索排序偏好新视频，而不是各月实际发布量。"),
    "composition_note": "这张图只用来说明口径问题。两次的条数不能相减得出「增长 / 下降」，也不代表各月的真实发布量或观看量。",
    "panel_desc": "按 7 月抓取时的发布时长分组，展示同一视频从 7 月到 10 月播放增长倍数的中位数与四分位区间。",
    "panel_caption": (f"<b>越新的视频涨得越多。</b>7 月时发布不到 30 天的视频，到 10 月中位涨到 {young['median_ratio']} 倍；"
                      f"发布超过一年的只涨到 {old['median_ratio']} 倍。所以拿新旧视频的累计播放排榜，比的主要是「发布了多久」。"),
    "theme_desc": "7 月以来新发视频按标题主题归类，左侧为样本占比，右侧为同周发布视频中播放百分位的中位数。",
    "theme_caption": "<b>占比和表现不是一回事。</b>百分位 50 表示与同一周发布的视频相比居中；高于 50 说明这类内容在同周更容易拿到播放。主题可重叠，未归类的视频不显示。",
    "top_note": "这是 7 月以来新发视频按当前累计播放的排序，越早发布越占优（见「已发布天数」）；只用来看「有哪些内容」，不用来比较内容效果。",
}

# ---------- 玩家之声（人工复核后的读法） ----------
VOICE_READING = json.loads((ROOT / "analysis" / f"voice_reading_{SNAP_DAY}.json").read_text(encoding="utf-8"))
voice = {
    "themes": [{"theme": t, "n": rv["theme_counts"].get(t, 0), "reading": VOICE_READING["readings"][t],
                "examples": rv["examples"].get(t, [])[:2]} for t in VOICE_READING["order"] if rv["theme_counts"].get(t)],
    "note": (f"{cm['n']} 条评论来自 {cm['n_videos']} 个视频的第一页热评（匿名可见，通常每视频 3 条），"
             f"全部 {rv['n_reviewed']} 条逐条人工复核：有玩家需求信号的 {rv['n_with_signal']} 条；"
             f"关键词初筛命中 {cm['n_any_theme']} 条，其中 {rv['screen_hit_no_signal']} 条复核后判定为玩梗或无关，"
             f"另有 {rv['signal_missed_by_screen']} 条有信号却没被关键词命中；{rv['n_non_ow']} 条讨论的是其他游戏，不计入主题。"
             "高赞评论偏向玩梗和共鸣，只说明「出现了哪些说法」，不能估计玩家整体的比例或满意度。"),
}

segments = json.loads((ROOT / "analysis" / f"segments_{SNAP_DAY}.json").read_text(encoding="utf-8"))
plan = json.loads((ROOT / "analysis" / f"plan_{SNAP_DAY}.json").read_text(encoding="utf-8"))

fetch_summary = M["fetch_summary"]
limits = [
    "B 站搜索结果是检索样本，按综合排序截断，不是全站普查；关键词设计会影响主题占比。",
    "官方账号完整投稿列表匿名访问被风控拒绝（F01）；视频详情接口当日持续 412，面板改用按标题检索、bvid 精确匹配。",
    "评论为匿名可见的第一页热评，偏向高赞玩梗；小红书、知乎本轮未重新采集。",
    "全球总决赛场馆信息来自地方媒体与第三方维基，主办方原文未找到（S14）；季中冠军赛名次与世界杯中国队成绩未核验（F02）。",
    "公开播放量不能推算回流、留存或付费；所有营销建议均为未经验证的判断。",
]
method_notes = [
    "清洗 R1：挂其他激励计划标签、时长 ≤30 秒、标题以「守望先锋」开头但无任何 OW 专有词的关键词堆砌短视频；不以低播放为依据。",
    "清洗 R2：标题或标签含 OW 词根（不用裸「守望」），或含高辨识度英雄/赛事名；跨游戏泛内容作为残余噪声保留并计数。",
    f"清洗结果：7 月 {M['cleaning']['july']['n_raw']:,} → {M['cleaning']['july']['n_clean']:,}；本次 {M['cleaning']['now']['n_raw']:,} → {M['cleaning']['now']['n_clean']:,}。抽样见 analysis/cleaning_audit_{SNAP_DAY}.md。",
    "复跑：scripts/ 下 6 个采集脚本 → analysis/analyze_update.py → analysis/build_report_data.py → report/build_report.py → analysis/export_office.py。",
    "三种时间分开记录：事件发生时间（evidence_sources.event_time）、来源发布时间（source_published）、采集时间（每条记录 fetched_at）。",
]

data = {
    "meta": meta, "stats": stats, "toc": toc, "leads": leads, "findings": findings, "timeline": timeline,
    "corrections": corrections, "charts": charts, "composition": comp, "panel": pan, "recent": rec,
    "voice": voice, "segments": segments, "priority": plan["priority"], "experiment": plan["experiment"],
    "topics": plan["topics"], "sources": SRC, "fetch_summary": fetch_summary, "limits": limits,
    "method_notes": method_notes,
}
out = ROOT / "report" / "data.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK -> {out}")
