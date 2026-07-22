# OW Marketing Insight — 守望先锋2 国服回归 500 天：数据驱动的市场洞察

> 用赛事×玩家×内容三源公开数据，量化《守望先锋2》国服回归后的生态图景，并输出可执行的营销建议。
> 关联申请线：网易雷火 · 全球游戏市场品牌营销（2027 届校招）。

## 研究问题

1. 国服回归 500 天（2025-02-19 至今），B 站守望先锋内容生态的量级、结构与爆款规律是什么？
2. OWCS 中国赛区（JDG/WBG/AG 合作战队，世界总决赛 2026-12 落地中国）的赛事数据里有哪些可做营销叙事的素材？
3. 对比 LoL/Dota2 的成熟数据生态（Riot API / OpenDota），OW 还有哪些数据资产未被利用——差距本身就是营销机会。

## 数据源（全部公开，已逐一验证可得）

| 层 | 来源 | 验证状态 |
|---|---|---|
| 内容生态 | B 站 web 搜索 API（视频元数据：播放/点赞/弹幕/收藏/标签/发布时间） | ✅ 2026-07-22 实测 200，1000 条/关键词 |
| 赛事数据 | Liquipedia OWCS 2026 China Stage 1/2（MediaWiki API，UA+限速） | ✅ 页面确认存在（战队/比分/奖金） |
| 游戏数据 | OverFast API（英雄/职责/玩家生涯，unofficial） | ✅ 2026-07-22 实测 /heroes 200 |
| 横向对比 | GitHub 开源项目扫描（OpenDota / Riot API 生态） | ✅ 样本清单见 analysis/ |

## 复现

```bash
python scripts/fetch_bilibili.py   # 内容生态原始数据 → data/raw/
python scripts/fetch_overfast.py   # 英雄/职责数据 → data/raw/
python scripts/fetch_liquipedia.py # OWCS 赛事 wikitext → data/raw/
```

分析与报告：

```bash
python analysis/explore_v1.py          # 落库 DuckDB + 首轮统计摘要
python analysis/export_report_data.py  # 清洗 v2 + 导出看板数据 report/data.json
python report/build_report.py          # 注入数据生成单文件看板 report/index.html
```

可视化看板：**[在线版（GitHub Pages）](https://martin-cell-blip.github.io/ow-marketing-insight/)** ｜ 源文件 `report/index.html`（单文件、零外部 JS 依赖、手写 SVG 图表，守望先锋风格但不使用任何官方美术资产）。

## 可信性纪律

- 所有数字可溯源至 `data/raw/` 原始抓取文件（含抓取时间戳）
- B 站数据含明显 spam（挂机刷量/蹭税视频），清洗规则成文于 analysis/
- 结论区分 [数据事实] 与 [推断]
