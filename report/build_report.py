# -*- coding: utf-8 -*-
"""把 data.json 注入 template.html 生成单文件 index.html。"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
tpl = (HERE / "template.html").read_text(encoding="utf-8")
out = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
(HERE / "index.html").write_text(out, encoding="utf-8")
print(f"OK -> {HERE / 'index.html'} ({len(out)//1024} KB)")
