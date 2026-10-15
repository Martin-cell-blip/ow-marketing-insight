# -*- coding: utf-8 -*-
"""快照目录与采集日志的共用约定。

- 新采集一律写入 data/snapshots/<北京时间日期>/，不覆盖 data/raw/（2026-07 历史基线）。
- 每次采集在快照目录的 fetch_log.jsonl 追加一行：来源、参数、成功/失败计数与错误摘要。
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BJT = timezone(timedelta(hours=8))


def snapshot_dir() -> Path:
    """OW_SNAPSHOT=YYYY-MM-DD 可指定快照（复跑同一天的后续步骤）；默认今天北京时间。"""
    day = os.environ.get("OW_SNAPSHOT") or datetime.now(BJT).strftime("%Y-%m-%d")
    d = ROOT / "data" / "snapshots" / day
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return datetime.now(BJT).isoformat(timespec="seconds")


def log_run(snap: Path, source: str, **fields) -> None:
    rec = {"source": source, "logged_at": now_iso(), **fields}
    with (snap / "fetch_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
