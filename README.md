# OW Marketing Insight — 《守望先锋》B 站内容与玩家信号研究（截至 2026-10-15）

> 个人研究作品，关联申请线：网易雷火 · 全球游戏市场品牌营销。以中国大陆市场和 B 站为主，中文资料为主，英文资料只用于核验。
> 与暴雪娱乐 / 网易无隶属关系，不使用任何官方美术资产。

**看板**：`report/index.html`（单文件，双击即可打开；`docs/index.html` 为同一文件，用于 GitHub Pages）。
**历史基线**：2026-07 首版报告保留在 `report/archive/2026-07-24_index.html`，原始数据保留在 `data/raw/`。

## 本次更新回答的问题

1. 2026-07-22 以来，游戏版本、赛事和 B 站内容传播发生了哪些值得营销人员关注的变化？
2. 当前公开样本里，不同玩家有哪些具体需求、参与动机与阻力？
3. 哪些发现值得转成内容、社区活动或营销实验？

## 三种时间，分开记

| 时间 | 含义 | 记录位置 |
|---|---|---|
| 事件发生时间 | 版本上线、赛事举办等实际发生的日期 | `analysis/evidence_sources.json` 的 `event_time` |
| 来源发布时间 | 官网新闻、媒体稿件的发布日期 | `source_published` / `official_news_cn.jsonl` 的 `source_date` |
| 数据采集时间 | 本项目抓取的时刻（北京时间） | 每条原始记录的 `fetched_at`，汇总见 `fetch_log.jsonl` |

研究截止日 = 2026-10-15（北京时间，实际执行当天）。7 月基线实际抓取于 2026-07-22T17:10Z，即北京时间 2026-07-23 01:10（原报告按当地时间记为 07-22）；「7 月以来」窗口统一从 2026-07-22 00:00（北京时间）起算。

## 数据与采样

| 层 | 来源 | 本次做法 | 位置 |
|---|---|---|---|
| 官方信息 | 《守望先锋》国服官网新闻、赛事新闻（ow.blizzard.cn） | 列表页 1–8 页 + 2026-07-01 后正文 | `data/snapshots/2026-10-15/official_news_cn.jsonl` |
| 内容生态 | B 站 web 搜索 API（匿名） | 三种检索设计，见下 | `bilibili_search_hits.jsonl` |
| 同一视频追踪 | B 站视频详情接口 | 7 月基线中固定种子随机 600 条 + 官方号视频 + 7 月 TOP10，取当前计数 | `bilibili_panel.jsonl` |
| 官方账号核验 | B 站 card 接口（按 mid） | 认证字段、投稿数 | `bilibili_official_accounts.json` |
| 评论 | B 站 reply 接口（匿名，第一页按热度） | 7 月以来主题视频 ∪ 窗口内播放 TOP60，上限 150 个视频 | `bilibili_comments.jsonl` |
| 赛事 | Liquipedia（第三方维基） | 中国赛区 Stage 2/3、季中冠军赛、全球总决赛 wikitext | `liquipedia_*.json` |
| 游戏元数据 | OverFast API（非官方） | 英雄、职责、地图、模式 | `overfast_*.json` |
| 候选检索 | yichen-unified-search（AnySearch 后端） | 有界检索候选，关键主张均打开原文核验 | 结论只引用已打开的原文 |

**B 站检索设计**（全部写进同一命中表，保留 设计 / 关键词 / 窗口 / 页 / 位次；按 bvid 去重时保留全部命中关键词）：

- `replica`：复刻 7 月——同 5 个关键词（守望先锋、守望先锋2、守望先锋 国服、守望先锋 十周年、OWCS），综合排序，每词 ≤50 页。只用于和 7 月比较**样本组成**。
- `extension`：新增 5 个关键词（回坑、新手、新赛季、血律、OWCS 中国），综合排序，每词 ≤20 页。
- `weekly`：2026-07-22 起按自然周切窗（`pubtime_begin_s/end_s`），5 个关键词每窗取前 3 页。让每一周都有样本，用于「7 月以来新发视频」的主题分析。
- 已放弃：按发布时间倒序翻页。「守望先锋」37 页只能回溯约 1 天，覆盖不了窗口；尝试记录在 `fetch_log.jsonl`，命中已删除。

**清洗规则 v3**（7 月基线和本次快照用同一套规则重算，抽样见 `analysis/cleaning_audit_2026-10-15.md`）：

- R1 刷量短视频：挂其他激励计划标签、时长 ≤30 秒、标题以「守望先锋」开头但没有任何 OW 专有词（「守望先锋+其他游戏角色」式关键词堆砌）。**不以低播放为依据**。
- R2 相关性：标题/标签含 OW 词根（守望先锋、overwatch、owcs 等；不用裸「守望」，它会命中三角洲「极星守望」和《潮汐守望者》），或含高辨识度英雄/赛事名。仍会漏掉只用昵称（如「铁拳」）的视频，误差记录在审计文件里。

## 复跑

依赖：Python 3（`requests`、`openpyxl`；7 月版旧脚本另需 `duckdb`）、Node（全局 `docx` 包，用于 Word）、LibreOffice（Excel 公式重算）。

```bash
cd scripts
# 采集（写入 data/snapshots/<北京时间日期>/；OW_SNAPSHOT=YYYY-MM-DD 可指定已有快照续跑）
python fetch_official_news.py
python fetch_bilibili.py                 # 约 15 分钟；可用 --designs weekly --append 续跑单个设计
python fetch_bilibili_panel.py           # 约 12 分钟
python fetch_bilibili_comments.py        # 依赖本快照的命中表
python fetch_liquipedia.py               # 条款要求每次 parse 间隔 31 秒
python fetch_overfast.py
cd ..
# 计算 → 看板数据 → 页面
python analysis/analyze_update.py        # → analysis/metrics_<日期>.json、清洗审计、评论初筛表
python analysis/code_comments_2026-10-15.py   # 人工复核记录 → comment_review_<日期>.csv（新快照需重新人工复核）
python analysis/analyze_update.py        # 再跑一次，汇入复核结果
python analysis/build_report_data.py     # → report/data.json（合并计算结果、来源表与研究判断）
python report/build_report.py            # → report/index.html，并同步 docs/
python analysis/export_office.py         # → deliverables/ 下的 Word 摘要、Excel 证据表、视频脚本 Word
```

7 月版脚本保留可复跑：`analysis/explore_v1.py`、`analysis/export_report_data.py`（输出到 `report/archive/`）。

## 主要数字从哪来

| 数字 | 原始记录 | 计算 |
|---|---|---|
| 样本组成（30 天内发布占比、两次重叠条数） | `data/raw/bilibili_videos.jsonl`、快照 `bilibili_search_hits.jsonl`（design=replica） | `analyze_update.py` A 段；清洗规则 `scripts/ow_rules.py` |
| 同一视频增长倍数 | 快照 `bilibili_panel.jsonl`（play_july / play_now） | B 段，按 7 月时发布时长分组取中位与四分位 |
| 新发视频主题占比、同周百分位 | `bilibili_search_hits.jsonl`（design=weekly） | C 段；主题只看标题，百分位在同一周发布的视频内计算 |
| 官方号同周百分位、投稿总数 | `bilibili_search_hits.jsonl`（按 mid）、`bilibili_official_accounts.json` | F 段 |
| 回坑标题条数、官方新手教学条数 | `bilibili_search_hits.jsonl` | G 段 |
| 评论主题与立场 | `bilibili_comments.jsonl` → `comment_screen_*.csv` → `comment_review_*.csv` | E 段；人工复核记录在 `code_comments_2026-10-15.py` |
| 版本、活动、赛事事实 | `official_news_cn.jsonl`、`verification_pages.jsonl`、`liquipedia_*.json`、`overfast_*.json` | `analysis/evidence_sources.json`（S01–S17、F01–F02），采集时间由 `build_report_data.py` 回填 |

所有计算结果写在 `analysis/metrics_2026-10-15.json`；看板、Word、Excel 都只从 `report/data.json` 取数，判断文字里的数字由脚本填入。

## 读数口径（看板与文档都遵守）

- 搜索结果是**检索样本**，不是全站总量。两次搜索返回的视频集合不同，只比较样本组成，不拿两次的条数或播放做增减。
- 累计播放随发布时长一直增长。跨时间的比较只在**同一视频**（面板）或**同一周发布**的视频之间做（同周播放百分位）。
- 单次抓取的累计播放按发布月份汇总，不等于各月实际观看量，本版不再画这种曲线。
- 高赞评论样本只说明「出现了哪些说法」，不能估计全体玩家的痛点比例或满意度。关键词命中只做初筛，主题与立场经人工复核。
- 结论分三档：**事实**（可回到原始记录或官方原文）、**推断**（有数据支撑的解释，存在其他解释）、**待验证假设**。
- 公开播放量不用于推算回流、留存或付费。

## 主要限制

- 官方账号完整投稿列表匿名访问被 B 站风控拒绝，官方号窗口内发了多少条无法统计（只核验了账号身份与投稿总数）。
- 评论只取每视频第一页热评，匿名态，不含登录可见内容；小红书、知乎本轮未重新采集。7 月版里引用的小红书/知乎数字没有留存原始记录，已从看板撤下。
- 全球总决赛的场馆信息来自广州市白云区融媒体与 Liquipedia，截至检索时未在 ow.blizzard.cn 赛事新闻列表找到主办方公告。季中冠军赛名次、世界杯中国队成绩本轮未核验。

## 目录

```
data/raw/                      2026-07 历史基线（不覆盖）
data/snapshots/2026-10-15/     本次快照 + fetch_log.jsonl
scripts/                       采集脚本（snapshot.py 统一快照目录与日志）
analysis/                      计算、清洗审计、评论复核、来源表、研究判断
report/                        看板模板、数据、页面；archive/ 为 7 月版
docs/                          GitHub Pages 展示文件（构建时同步）
deliverables/                  Word 摘要、Excel 证据表
```
