from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["argument", "product", "context"]


class Item(BaseModel):
    title: str
    url: str
    source: str
    kind: Kind
    points: int | None
    comments: int | None
    note: str | None
    why: str


class Snapshot(BaseModel):
    fetched_at: datetime
    snapshot_id: str
    arguments: list[Item]
    products: list[Item]
    context: list[Item]
    source_errors: dict[str, str] = Field(default_factory=dict)
    warning: str | None = None


class Feed(Snapshot):
    focus: list[str]
    focus_matched: bool
    message: str | None = None
