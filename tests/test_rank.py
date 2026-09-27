import json
from pathlib import Path

import pytest

from indie_brief.errors import BriefError
from indie_brief.rank import apply_focus, build_snapshot, split_focus

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot.json"


def _snapshot():
    return build_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_quotas_keep_viral_reddit_out_of_arguments():
    snapshot = _snapshot()
    assert [item.title for item in snapshot.arguments] == [
        "Why is billing so painful",
        "独立开发者怎么做付费",
    ]
    assert snapshot.arguments[0].url == "https://news.ycombinator.com/item?id=2"
    assert snapshot.arguments[0].comments == 18
    assert "Random guy knocked on my door" not in {item.title for item in snapshot.arguments}
    assert snapshot.context[0].title == "Random guy knocked on my door"
    assert snapshot.context[0].why == "Reddit 全站，80000 分"
    assert [item.source for item in snapshot.products] == ["product_hunt", "github"]
    assert snapshot.snapshot_id == "20260927T040000Z"
    assert snapshot.source_errors == {"lobsters": "HTTP 404"}


def test_focus_does_not_backfill():
    snapshot = _snapshot()
    focused = apply_focus(snapshot, split_focus("billing，Billing"))
    assert focused.focus == ["billing"]
    assert focused.focus_matched is True
    assert [item.source for item in focused.arguments] == ["hn"]
    assert [item.source for item in focused.products] == ["github"]
    assert focused.context == []
    assert focused.source_errors == {"lobsters": "HTTP 404"}


def test_unmatched_focus_stays_empty():
    focused = apply_focus(_snapshot(), ["没有这个词"])
    assert focused.focus_matched is False
    assert focused.arguments == []
    assert focused.products == []
    assert focused.context == []
    assert focused.message == "这份快照里没有匹配到这些关键词。"
    assert focused.source_errors == {"lobsters": "HTTP 404"}


def test_naive_timestamp_is_rejected():
    with pytest.raises(BriefError) as caught:
        build_snapshot({"fetched_at": "2026-09-27T12:00:00", "hn": []})
    assert caught.value.code == "BAD_SNAPSHOT"


def test_missing_url_is_rejected():
    with pytest.raises(BriefError, match="缺少 http"):
        build_snapshot(
            {
                "fetched_at": "2026-09-27T12:00:00+00:00",
                "hn": [{"title": "no link", "url": "javascript:alert(1)"}],
            }
        )


def test_empty_snapshot_is_rejected():
    with pytest.raises(BriefError) as caught:
        build_snapshot({"fetched_at": "2026-09-27T12:00:00+00:00"})
    assert caught.value.code == "NO_ITEMS"
