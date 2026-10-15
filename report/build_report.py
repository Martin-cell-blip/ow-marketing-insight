# -*- coding: utf-8 -*-
"""把 data.json 注入 template.html 生成单文件 index.html，并同步到 docs/（GitHub Pages 实际展示的文件）。

docs/archive/ 同步保留 7 月基线报告，页脚链接指向它。
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
tpl = (HERE / "template.html").read_text(encoding="utf-8")
out = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
          .replace("/*__TITLE__*/", data["meta"]["title"]))
(HERE / "index.html").write_text(out, encoding="utf-8")
(DOCS / "archive").mkdir(parents=True, exist_ok=True)
shutil.copyfile(HERE / "index.html", DOCS / "index.html")
for p in (HERE / "archive").iterdir():
    shutil.copyfile(p, DOCS / "archive" / p.name)
print(f"OK -> {HERE / 'index.html'} ({len(out)//1024} KB), synced to {DOCS}")
