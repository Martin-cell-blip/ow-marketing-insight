# -*- coding: utf-8 -*-
"""抓取 OverFast API 英雄与职责数据（unofficial 公开 API）。
输出: data/raw/overfast_heroes.json / overfast_roles.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://overfast-api.tekrop.fr"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    meta = {"fetched_at": datetime.now(timezone.utc).isoformat(), "source": BASE}
    for ep, name in [("/heroes", "overfast_heroes"), ("/roles", "overfast_roles"),
                     ("/gamemodes", "overfast_gamemodes"), ("/maps", "overfast_maps")]:
        r = requests.get(BASE + ep, timeout=30)
        r.raise_for_status()
        (RAW / f"{name}.json").write_text(
            json.dumps({"_meta": meta, "data": r.json()}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"[OK] {ep} -> {name}.json")


if __name__ == "__main__":
    main()
