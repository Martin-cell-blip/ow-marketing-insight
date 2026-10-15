# -*- coding: utf-8 -*-
"""抓取 OverFast API 英雄与职责数据（unofficial 公开 API）。
非官方 API（数据抓自暴雪英文官网），用于英雄数与职责构成。
输出: data/snapshots/<日期>/overfast_*.json
"""
import json
from datetime import datetime, timezone

import requests

from snapshot import log_run, snapshot_dir

BASE = "https://overfast-api.tekrop.fr"


def main() -> None:
    snap = snapshot_dir()
    done = []
    meta = {"fetched_at": datetime.now(timezone.utc).isoformat(), "source": BASE}
    for ep, name in [("/heroes", "overfast_heroes"), ("/roles", "overfast_roles"),
                     ("/gamemodes", "overfast_gamemodes"), ("/maps", "overfast_maps")]:
        r = requests.get(BASE + ep, timeout=30)
        r.raise_for_status()
        (snap / f"{name}.json").write_text(
            json.dumps({"_meta": meta, "data": r.json()}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"[OK] {ep} -> {name}.json")
        done.append(ep)
    log_run(snap, "overfast", endpoints=done)


if __name__ == "__main__":
    main()
