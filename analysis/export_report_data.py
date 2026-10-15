# -*- coding: utf-8 -*-
"""清洗 v2 + 导出可视化看板所需聚合数据。
清洗规则：
  R1 剔除挂机/蹭激励计划 spam（tag 含创作者激励计划 且 play<=100）
  R2 相关性过滤：title 或 tag 必含 OW 词根（守望/overwatch/owcs/ow2/独立词 ow）
     —— 修复 OWCS 关键词混入的英雄联盟内容（TES/MSI 等）
输出: report/archive/2026-07-24_data.json（7 月历史基线，保留可复跑；当前看板见 analysis/analyze_update.py）
"""
import json
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "ow.duckdb"
OUT = ROOT / "report" / "archive" / "2026-07-24_data.json"

OFFICIAL = ["守望先锋", "守望先锋电竞", "暴雪游戏", "网易暴雪"]

con = duckdb.connect(str(DB))
con.create_function("is_ow", lambda title, tag: bool(re.search(
    r"守望|overwatch|owcs|ow2|(?<![a-z])ow(?![a-z])",
    f"{title or ''},{tag or ''}", re.I)), ["VARCHAR", "VARCHAR"], "BOOLEAN")

con.execute("""
CREATE OR REPLACE VIEW clean AS
SELECT * FROM bili_videos
WHERE NOT is_spam_suspect AND is_ow(title, tag);
""")

def rows(sql, params=None):
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

n_raw = con.execute("SELECT count(*) FROM bili_videos").fetchone()[0]
n_clean = con.execute("SELECT count(*) FROM clean").fetchone()[0]
n_return = con.execute("SELECT count(*) FROM clean WHERE pub_ts >= '2025-02-19'").fetchone()[0]
plays_return = con.execute("SELECT sum(play) FROM clean WHERE pub_ts >= '2025-02-19'").fetchone()[0]

monthly = rows("""
SELECT strftime(pub_ts,'%Y-%m') AS m, count(*) AS n, sum(play) AS plays
FROM clean WHERE pub_ts >= '2025-01-01' GROUP BY 1 ORDER BY 1""")

top_videos = rows("""
SELECT title, author, play, "like" AS likes, danmaku, strftime(pub_ts,'%Y-%m-%d') AS d
FROM clean WHERE pub_ts >= '2025-02-19' ORDER BY play DESC LIMIT 10""")

# 官方 vs 二创：单条均值对比
ph = ",".join(["?"] * len(OFFICIAL))
acct = rows(f"""
SELECT CASE WHEN author IN ({ph}) THEN author ELSE 'UGC' END AS grp,
       count(*) AS n, sum(play) AS plays,
       round(sum(play)/count(*)) AS avg_play
FROM clean WHERE pub_ts >= '2025-02-19'
GROUP BY 1 ORDER BY plays DESC""", OFFICIAL)

top_ugc = rows(f"""
SELECT author, count(*) AS n, sum(play) AS plays, round(sum(play)/count(*)) AS avg_play
FROM clean WHERE pub_ts >= '2025-02-19' AND author NOT IN ({ph})
GROUP BY 1 ORDER BY plays DESC LIMIT 8""", OFFICIAL)

official_detail = rows(f"""
SELECT author, count(*) AS n, sum(play) AS plays, round(sum(play)/count(*)) AS avg_play
FROM clean WHERE pub_ts >= '2025-02-19' AND author IN ({ph})
GROUP BY 1 ORDER BY plays DESC""", OFFICIAL)

tags = rows("""
SELECT trim(t.x) AS tag, count(*) AS n
FROM clean, unnest(string_split(tag, ',')) AS t(x)
WHERE pub_ts >= '2025-02-19' AND len(trim(t.x)) BETWEEN 2 AND 12
  AND trim(t.x) NOT IN ('守望先锋','守望先锋2','OW','ow','overwatch','ow2','OW2','游戏','Overwatch')
GROUP BY 1 ORDER BY n DESC LIMIT 16""")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "meta": {"n_raw": n_raw, "n_clean": n_clean, "n_return": n_return,
             "plays_return": int(plays_return or 0),
             "fetched": "2026-07-22", "window": "2025-02-19 ~ 2026-07-22"},
    "monthly": monthly, "top_videos": top_videos,
    "acct": acct, "top_ugc": top_ugc, "official_detail": official_detail,
    "tags": tags,
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"raw={n_raw} clean={n_clean} since_return={n_return} plays={plays_return}")
print(f"OK -> {OUT}")
