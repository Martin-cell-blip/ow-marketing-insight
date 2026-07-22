# -*- coding: utf-8 -*-
"""首轮探索：B 站 OW 内容生态基础统计。
输出: analysis/explore_v1_summary.md + data/ow.duckdb
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "bilibili_videos.jsonl"
DB = ROOT / "data" / "ow.duckdb"
OUT = ROOT / "analysis" / "explore_v1_summary.md"

con = duckdb.connect(str(DB))
con.execute("""
CREATE OR REPLACE TABLE bili_videos AS
SELECT *,
       to_timestamp(pubdate) AS pub_ts,
       CASE WHEN tag LIKE '%创作者激励计划%' AND play <= 100 THEN TRUE ELSE FALSE END AS is_spam_suspect
FROM read_json_auto(?);
""", [str(RAW)])

def q(sql):
    return con.execute(sql).fetchall()

total = q("SELECT count(*), min(pub_ts), max(pub_ts) FROM bili_videos")[0]
spam = q("SELECT count(*) FROM bili_videos WHERE is_spam_suspect")[0][0]
clean_n = q("SELECT count(*) FROM bili_videos WHERE NOT is_spam_suspect")[0][0]
since_return = q("SELECT count(*) FROM bili_videos WHERE NOT is_spam_suspect AND pub_ts >= '2025-02-19'")[0][0]

monthly = q("""
SELECT strftime(pub_ts, '%Y-%m') AS m, count(*) AS n, sum(play) AS plays
FROM bili_videos WHERE NOT is_spam_suspect AND pub_ts >= '2025-01-01'
GROUP BY 1 ORDER BY 1
""")

top_play = q("""
SELECT title, author, play, danmaku, "like", strftime(pub_ts,'%Y-%m-%d') AS d
FROM bili_videos WHERE NOT is_spam_suspect
ORDER BY play DESC LIMIT 15
""")

top_authors = q("""
SELECT author, count(*) AS n, sum(play) AS total_play
FROM bili_videos WHERE NOT is_spam_suspect
GROUP BY 1 ORDER BY total_play DESC LIMIT 15
""")

tags = q("""
SELECT trim(t.tag_one) AS tg, count(*) AS n
FROM bili_videos, unnest(string_split(tag, ',')) AS t(tag_one)
WHERE NOT is_spam_suspect
GROUP BY 1 HAVING count(*) >= 20 ORDER BY n DESC LIMIT 25
""")

lines = ["# 首轮探索摘要（explore_v1）\n"]
lines.append(f"- 原始视频数：{total[0]}（时间范围 {total[1]} ~ {total[2]}）")
lines.append(f"- 疑似 spam（激励计划蹭税+播放≤100）：{spam} 条（{spam/total[0]*100:.1f}%），清洗后 {clean_n} 条")
lines.append(f"- 国服回归（2025-02-19）以来发布：{since_return} 条\n")
lines.append("## 月度发布量与播放（2025-01 起，清洗后）\n\n| 月份 | 视频数 | 总播放 |\n|---|---|---|")
for m, n, p in monthly:
    lines.append(f"| {m} | {n} | {int(p or 0):,} |")
lines.append("\n## 播放 TOP15\n\n| 标题 | UP主 | 播放 | 弹幕 | 点赞 | 发布 |\n|---|---|---|---|---|---|")
for t, a, p, d, l, dt in top_play:
    lines.append(f"| {t[:40]} | {a} | {p:,} | {d} | {l} | {dt} |")
lines.append("\n## UP主 TOP15（按总播放）\n\n| UP主 | 视频数 | 总播放 |\n|---|---|---|")
for a, n, p in top_authors:
    lines.append(f"| {a} | {n} | {int(p or 0):,} |")
lines.append("\n## 高频标签（≥20 次）\n\n| 标签 | 出现次数 |\n|---|---|")
for tg, n in tags:
    lines.append(f"| {tg} | {n} |")
lines.append("\n> 方法论警示：搜索 API 按综合排序返回每词至多 1000 条，是「可见性样本」而非全量普查；结论表述须写明此边界。")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"OK -> {OUT}")
print(f"total={total[0]}, spam={spam}, clean={clean_n}, since_return={since_return}")
