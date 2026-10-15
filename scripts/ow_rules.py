# -*- coding: utf-8 -*-
"""清洗规则 v3：采集脚本（选评论目标）与分析脚本共用，保证两边口径一致。"""
import re

# 不用裸「守望」：会命中《三角洲行动》的「极星守望」和《潮汐守望者》
OW_ROOT = re.compile(r"守望先锋|守望先鋒|守望英雄|守望十周年|overwatch|owcs|ow2|(?<![a-z])ow(?![a-z])", re.I)
# 只收辨识度高、在其他游戏里基本不出现的英雄/系统名；「天使」「堡垒」「黑影」等常见词不收
OW_TERMS = re.compile(r"源氏|半藏|末日铁拳|莱因哈特|查莉娅|破坏球|西格玛|奥丽莎|拉玛刹|渣客女王|毛加|卢西奥|禅雅塔|"
                      r"巴蒂斯特|布丽吉塔|伊拉锐|无漾|弗蕾娅|骇灾|死怨|血律|D\.?Mon|秩序之光|托比昂|狂鼠|黑百合|猎空|"
                      r"卡西迪|索杰恩|法老之鹰|生命之梭|斩仇|瑞稀|朱诺|艾什|雾子|路霸|D\.Va|角斗领域", re.I)
INCENTIVE = re.compile(r"激励计划|激励")
# 只用于度量残余噪声：标题无 OW 字样、仅靠标签纳入、且标签里还有其他游戏名的「跨游戏泛内容」
OTHER_GAMES = re.compile(r"三角洲|无畏契约|瓦洛兰特|valorant|英雄联盟|穿越火线|解限机|漫威争锋|APEX|CS2|CSGO|暗区突围|"
                         r"永劫无间|王者荣耀|原神|崩坏|绝区零|鸣潮|第五人格|DOTA|彩虹六号|使命召唤|战地|逆战|和平精英|PUBG", re.I)


def title_has_ow(r):
    return bool(OW_ROOT.search(r.get("title") or "") or OW_TERMS.search(r.get("title") or ""))


def dur_s(d):
    parts = [int(x) for x in str(d or "0").split(":") if x.isdigit()]
    s = 0
    for p in parts:
        s = s * 60 + p
    return s


def is_spam(r):
    """R1 v3：挂其他激励计划标签 + 时长 ≤30 秒 + 标题以「守望先锋」开头但通篇没有任何 OW 专有词。
    典型样本是「守望先锋+其他游戏角色名」的关键词堆砌短视频。不以低播放为依据。"""
    tags = [t for t in (r.get("tag") or "").split(",") if t]
    other = any(INCENTIVE.search(t) and "守望" not in t for t in tags)
    title = (r.get("title") or "").strip()
    ow_specific = OW_TERMS.search(f"{title},{r.get('tag') or ''}")
    return other and dur_s(r.get("duration")) <= 30 and title.startswith("守望先锋") and not ow_specific


def is_ow(r):
    """R2 v3：标题或标签含 OW 词根，或含高辨识度英雄/赛事名。"""
    text = f"{r.get('title') or ''},{r.get('tag') or ''}"
    return bool(OW_ROOT.search(text) or OW_TERMS.search(text))
