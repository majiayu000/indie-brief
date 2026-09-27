from __future__ import annotations

import re
from datetime import UTC, datetime

from indie_brief.errors import BriefError
from indie_brief.models import Feed, Item, Kind, Snapshot

# 全站热度、HN 评论和 GitHub star 不是同一个尺度，按来源配额取，不跨来源比原始分数。
FIELD_KIND: dict[str, tuple[Kind, str]] = {
    "sitewide": ("context", "sitewide"),
    "ai_today": ("argument", "ai_today"),
    "ai_week": ("context", "ai_week"),
    "ai_month": ("context", "ai_month"),
    "hn": ("argument", "hn"),
    "hn_rss": ("argument", "hn"),
    "v2ex": ("argument", "v2ex"),
    "product_hunt": ("product", "product_hunt"),
    "github": ("product", "github"),
    "reddit_subs": ("argument", "reddit_subs"),
}

QUOTAS: dict[Kind, dict[str, int]] = {
    "argument": {"hn": 4, "v2ex": 3, "ai_today": 3, "reddit_subs": 2},
    "product": {"product_hunt": 5, "github": 5},
    "context": {"sitewide": 3, "ai_week": 2, "ai_month": 1},
}
CATALOG_LIMIT = 3
NOTE_LIMIT = 120

SOURCE_LABEL = {
    "hn": "HN",
    "v2ex": "V2EX",
    "ai_today": "Reddit AI 今日",
    "ai_week": "Reddit AI 本周",
    "ai_month": "Reddit AI 本月",
    "sitewide": "Reddit 全站",
    "reddit_subs": "Reddit",
    "product_hunt": "Product Hunt",
    "github": "GitHub",
}

_CATALOG_NAME = re.compile(r"[a-z0-9-]{1,40}")


def split_focus(raw: str) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,，]", raw):
        word = part.strip()
        key = word.casefold()
        if word and key not in seen:
            seen.add(key)
            words.append(word)
    return words


def apply_focus(snapshot: Snapshot, words: list[str]) -> Feed:
    if not words:
        return Feed(
            fetched_at=snapshot.fetched_at,
            snapshot_id=snapshot.snapshot_id,
            arguments=snapshot.arguments,
            products=snapshot.products,
            context=snapshot.context,
            source_errors=snapshot.source_errors,
            warning=snapshot.warning,
            focus=[],
            focus_matched=True,
            message=None,
        )

    def keep(item: Item) -> bool:
        haystack = " ".join(
            part for part in (item.title, item.note or "", item.source, item.why) if part
        ).casefold()
        return any(word.casefold() in haystack for word in words)

    arguments = [item for item in snapshot.arguments if keep(item)]
    products = [item for item in snapshot.products if keep(item)]
    context = [item for item in snapshot.context if keep(item)]
    matched = bool(arguments or products or context)
    return Feed(
        fetched_at=snapshot.fetched_at,
        snapshot_id=snapshot.snapshot_id,
        arguments=arguments,
        products=products,
        context=context,
        source_errors=snapshot.source_errors,
        warning=snapshot.warning,
        focus=words,
        focus_matched=matched,
        message=None if matched else "这份快照里没有匹配到这些关键词。",
    )


def build_snapshot(payload: object) -> Snapshot:
    if not isinstance(payload, dict):
        raise BriefError("BAD_SNAPSHOT", "快照顶层必须是对象")
    when = _fetched_at(payload.get("fetched_at"))
    grouped: dict[tuple[Kind, str], list[Item]] = {}
    for field, (kind, source) in FIELD_KIND.items():
        rows = _parse_list(payload.get(field), field, kind, source)
        grouped.setdefault((kind, source), []).extend(rows)

    arguments = _quota(grouped, "argument")
    products = _quota(grouped, "product")
    context = _quota(grouped, "context")
    context.extend(_catalog(payload.get("catalog_items")))

    if not arguments and not products and not context:
        raise BriefError("NO_ITEMS", "快照里没有可用的标题和链接")

    return Snapshot(
        fetched_at=when,
        snapshot_id=when.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"),
        arguments=arguments,
        products=products,
        context=context,
        source_errors=_source_errors(payload.get("source_errors")),
        warning=_warning(payload.get("warning")),
    )


def _fetched_at(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise BriefError("BAD_SNAPSHOT", "缺少 fetched_at")
    try:
        when = datetime.fromisoformat(value)
    except ValueError as exc:
        raise BriefError("BAD_SNAPSHOT", f"fetched_at 无法解析: {value}") from exc
    if when.tzinfo is None:
        raise BriefError("BAD_SNAPSHOT", "fetched_at 缺少时区")
    return when


def _source_errors(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BriefError("BAD_SNAPSHOT", "source_errors 必须是对象")
    errors: dict[str, str] = {}
    for key, message in value.items():
        if not isinstance(key, str) or not isinstance(message, str):
            raise BriefError("BAD_SNAPSHOT", "source_errors 的键和值必须是字符串")
        errors[key] = message
    return errors


def _warning(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise BriefError("BAD_SNAPSHOT", "warning 必须是字符串")
    text = value.strip()
    return text or None


def _catalog(value: object) -> list[Item]:
    if value is None:
        return []
    if not isinstance(value, dict):
        raise BriefError("BAD_SNAPSHOT", "catalog_items 必须是对象")
    items: list[Item] = []
    for key, rows in value.items():
        if not isinstance(key, str) or not _CATALOG_NAME.fullmatch(key):
            raise BriefError("BAD_SNAPSHOT", f"catalog 来源名不合法: {key!r}")
        items.extend(_parse_list(rows, f"catalog_items.{key}", "context", key))
    deduped = _dedupe(items)
    return _sorted(deduped)[:CATALOG_LIMIT]


def _quota(grouped: dict[tuple[Kind, str], list[Item]], kind: Kind) -> list[Item]:
    chosen: list[Item] = []
    for source, limit in QUOTAS[kind].items():
        chosen.extend(_sorted(_dedupe(grouped.get((kind, source), [])))[:limit])
    return chosen


def _parse_list(value: object, field: str, kind: Kind, source: str) -> list[Item]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise BriefError("BAD_SNAPSHOT", f"{field} 必须是数组")
    items: list[Item] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise BriefError("BAD_SNAPSHOT", f"{field}[{index}] 不是对象")
        items.append(_parse_row(row, f"{field}[{index}]", kind, source))
    return items


def _parse_row(row: dict[str, object], field: str, kind: Kind, source: str) -> Item:
    title = row.get("title")
    url = row.get("url")
    if not isinstance(title, str) or not title.strip():
        raise BriefError("BAD_SNAPSHOT", f"{field} 缺少标题")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise BriefError("BAD_SNAPSHOT", f"{field} 缺少 http(s) 链接")
    points = _as_int(row.get("score"), f"{field}.score")
    comments = _as_int(row.get("comments"), f"{field}.comments")
    subreddit = _text(row.get("subreddit"))
    note = _note(row.get("category"), subreddit)
    return Item(
        title=title.strip(),
        url=url.strip(),
        source=source,
        kind=kind,
        points=points,
        comments=comments,
        note=note,
        why=_why(source, points, comments, note, subreddit),
    )


def _as_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise BriefError("BAD_SNAPSHOT", f"{field} 必须是整数")
    return value


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _note(category: object, subreddit: str | None) -> str | None:
    text = _text(category)
    if text is not None and text.lower().startswith(("http://", "https://")):
        text = None
    if text is None:
        text = subreddit
    if text is None:
        return None
    if len(text) > NOTE_LIMIT:
        return text[: NOTE_LIMIT - 1] + "…"
    return text


def _why(
    source: str,
    points: int | None,
    comments: int | None,
    note: str | None,
    subreddit: str | None,
) -> str:
    label = SOURCE_LABEL.get(source, source)
    if source == "reddit_subs" and subreddit:
        label = f"Reddit r/{subreddit}"
    elif source == "v2ex" and subreddit:
        label = f"V2EX {subreddit}"
    parts = [label]
    if comments is not None:
        parts.append(f"{comments} 条评论")
    if points:
        unit = "今日 star" if source == "github" else "分"
        parts.append(f"{points} {unit}")
    if note and note != subreddit:
        parts.append(note)
    return "，".join(parts)


def _dedupe(items: list[Item]) -> list[Item]:
    chosen: dict[str, Item] = {}
    for item in items:
        key = _title_key(item.title)
        current = chosen.get(key)
        chosen[key] = item if current is None else _prefer(current, item)
    return list(chosen.values())


def _prefer(current: Item, candidate: Item) -> Item:
    return candidate if _discussion_key(candidate) > _discussion_key(current) else current


def _discussion_key(item: Item) -> tuple[int, int, int]:
    comments = item.comments if item.comments is not None else -1
    points = item.points if item.points is not None else -1
    discussion = 1 if "news.ycombinator.com" in item.url else 0
    return (comments, points, discussion)


def _sorted(items: list[Item]) -> list[Item]:
    return sorted(items, key=_discussion_key, reverse=True)


def _title_key(title: str) -> str:
    collapsed = re.sub(r"\s+", " ", title).casefold().strip()
    return collapsed.strip("\"'“”")
