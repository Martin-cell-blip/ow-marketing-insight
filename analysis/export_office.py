# -*- coding: utf-8 -*-
"""导出交付文档：Word 摘要（docx-js）+ Excel 证据与选题表（openpyxl）。数据来自 report/data.json。

输出: deliverables/OW研究更新摘要_<日期>.docx、deliverables/OW研究更新_证据与选题_<日期>.xlsx
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "report" / "data.json").read_text(encoding="utf-8"))
DAY = D["meta"]["cutoff"]
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)

FONT, HEAD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
FILL = PatternFill("solid", fgColor="F3F4F6")
WRAP = Alignment(wrap_text=True, vertical="top")
strip = lambda s: re.sub(r"<[^>]+>", "", str(s if s is not None else ""))


def sheet(wb, title, cols, rows, note=None):
    ws = wb.create_sheet(title)
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(name="Arial", size=9, italic=True, color="6B7280")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
        r0 = 2
    for j, (name, width) in enumerate(cols, 1):
        c = ws.cell(r0, j, name)
        c.font, c.fill, c.alignment = HEAD, FILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = width
    for i, row in enumerate(rows, r0 + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, strip(v))
            c.font, c.alignment = FONT, WRAP
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws, r0


wb = Workbook()
wb.remove(wb.active)

# 1. 来源与证据
src_rows = [[s["id"], s["topic"], s["claim"], s["event_time"], s["source_published"], s.get("fetched_at") or "（未存档）",
             s["source"], s["source_type"], s["strength"], s["url"]] for s in D["sources"]]
ws, r0 = sheet(wb, "来源与证据",
               [("ID", 6), ("主题", 10), ("主张", 60), ("事件发生时间", 18), ("来源发布时间", 16), ("采集时间（北京）", 22),
                ("来源", 28), ("来源类型", 14), ("证据强度", 18), ("URL", 50)],
               src_rows, note=f"研究截止 {DAY}（北京时间）。S=已打开原文核验的来源；F=采集或核验失败的记录。三种时间分列，互不替代。")
for i in range(r0 + 1, r0 + 1 + len(src_rows)):
    url = ws.cell(i, 10).value
    if url:
        ws.cell(i, 10).hyperlink = url
        ws.cell(i, 10).font = Font(name="Arial", size=10, color="0563C1", underline="single")

# 2. 新旧结论对比（末尾用公式统计各结果条数）
cor = D["corrections"]
ws, r0 = sheet(wb, "新旧结论对比", [("7 月报告的说法", 48), ("核验结果", 10), ("依据", 80)],
               [[c["old"], c["status"], c["why"]] for c in cor],
               note="先核验旧结论再提新结论。保留=有新证据支持；修正=方向或口径需改；撤下=证据无法回溯或口径错误。")
last = r0 + len(cor)
for k, label in enumerate(["保留", "修正", "撤下"]):
    r = last + 2 + k
    ws.cell(r, 1, f"「{label}」条数").font = HEAD
    ws.cell(r, 2, f'=COUNTIF(B{r0 + 1}:B{last},"{label}")').font = FONT

# 3. 核心发现
sheet(wb, "核心发现", [("#", 4), ("发现", 36), ("证据强度", 10), ("观察到的事实", 70), ("解释", 50), ("其他可能", 50),
                     ("对营销的意义", 50), ("下一步", 40)],
      [[i + 1, f["title"], f["strength"], f["fact"], f["interpretation"], f["alternatives"], f["meaning"], f["next"]]
       for i, f in enumerate(D["findings"])])

# 4. 三个内容选题
sheet(wb, "内容选题", [("#", 4), ("选题", 30), ("给谁看", 30), ("解决什么问题", 34), ("开场切入", 40), ("需要的素材", 50),
                     ("发布渠道", 16), ("为什么值得做", 50), ("最难成立的地方", 44)],
      [[i + 1, t["title"], t["audience"], t["problem"], t["hook"], t["materials"], t["channel"], t["why"], t["risk"]]
       for i, t in enumerate(D["topics"])],
      note="形式优先录屏 + 旁白 + 字幕。游戏观点与个人经历须由作者本人提供或确认，不代写。")

# 5. 采集情况
sheet(wb, "采集情况", [("来源", 34), ("状态", 10), ("说明", 90)],
      [[f["source"], f["status"], f["detail"]] for f in D["fetch_summary"]],
      note="来源不可用的如实记录；旧数据不冒充新数据。逐次参数见 data/snapshots/<日期>/fetch_log.jsonl。")

xlsx = OUT / f"OW研究更新_证据与选题_{DAY}.xlsx"
wb.save(xlsx)
# openpyxl 写出的公式没有缓存值；用本机 LibreOffice 重算一遍再覆盖回去
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
tmp = OUT / "_recalc"
subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(xlsx)],
               check=True, capture_output=True)
shutil.move(str(tmp / xlsx.name), str(xlsx))
tmp.rmdir()
print(f"OK -> {xlsx}")

docx = OUT / f"OW研究更新摘要_{DAY}.docx"
npm_root = subprocess.run("npm root -g", shell=True, capture_output=True, text=True, check=True).stdout.strip()
subprocess.run(["node", str(ROOT / "analysis" / "export_docx.js"), str(ROOT / "report" / "data.json"), str(docx)],
               check=True, env={**os.environ, "NODE_PATH": npm_root})
