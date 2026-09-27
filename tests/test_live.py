import json
import os
from pathlib import Path

import pytest

from indie_brief.rank import build_snapshot

LIVE_DIR = Path(
    os.environ.get(
        "TRENDHUNTER_BRIEFS",
        "/Users/apple/Desktop/code/AI/hunter/trendhunter/apps/crawler/data/briefs",
    )
)


def test_live_trendhunter_snapshot_separates_arguments_from_sitewide():
    files = sorted(path for path in LIVE_DIR.glob("*/*.json") if path.is_file())
    if not files:
        pytest.skip("no TrendHunter snapshots")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    snapshot = build_snapshot(payload)
    assert snapshot.arguments
    assert snapshot.products
    assert {item.source for item in snapshot.arguments} <= {"hn", "v2ex", "ai_today", "reddit_subs"}
    sitewide_titles = {
        item.get("title") for item in payload.get("sitewide", []) if isinstance(item, dict)
    }
    argument_titles = {item.title for item in snapshot.arguments}
    assert sitewide_titles.isdisjoint(argument_titles)
