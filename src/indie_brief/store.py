from __future__ import annotations

import json
import re
from pathlib import Path

from indie_brief.errors import BriefError
from indie_brief.models import Snapshot
from indie_brief.rank import build_snapshot

_SNAPSHOT_ID = re.compile(r"^\d{8}T\d{6}Z$")


def import_file(data_dir: Path, path: Path) -> Snapshot:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BriefError("BAD_SNAPSHOT", f"无法读取 {path}: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BriefError("BAD_SNAPSHOT", f"{path} 不是合法 JSON: {exc}") from exc
    snapshot = build_snapshot(payload)
    write_snapshot(data_dir, snapshot)
    return snapshot


def import_dir(data_dir: Path, directory: Path) -> list[Snapshot]:
    if not directory.is_dir():
        raise BriefError("BAD_SNAPSHOT", f"不是目录: {directory}")
    files = sorted(path for path in directory.glob("*/*.json") if path.is_file())
    if not files:
        files = sorted(path for path in directory.glob("*.json") if path.is_file())
    if not files:
        raise BriefError("BAD_SNAPSHOT", f"{directory} 里没有 json 快照")
    return [import_file(data_dir, path) for path in files]


def write_snapshot(data_dir: Path, snapshot: Snapshot) -> Path:
    path = snapshot_path(data_dir, snapshot.snapshot_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)
    _update_latest(data_dir, snapshot)
    return path


def read_latest(data_dir: Path) -> Snapshot:
    pointer = data_dir / "latest"
    if not pointer.is_file():
        raise BriefError("NO_SNAPSHOT", "还没有导入简报")
    snapshot_id = pointer.read_text(encoding="utf-8").strip()
    path = snapshot_path(data_dir, snapshot_id)
    if not path.is_file():
        raise BriefError("NO_SNAPSHOT", f"最新快照文件不存在: {snapshot_id}")
    try:
        return Snapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BriefError("BAD_SNAPSHOT", f"快照文件损坏: {path.name}") from exc


def snapshot_path(data_dir: Path, snapshot_id: str) -> Path:
    if not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise BriefError("BAD_ID", "快照编号不合法")
    root = (data_dir / "snapshots").resolve()
    path = (root / f"{snapshot_id}.json").resolve()
    if path.parent != root:
        raise BriefError("BAD_ID", "快照编号不合法")
    return path


def _update_latest(data_dir: Path, snapshot: Snapshot) -> None:
    pointer = data_dir / "latest"
    if pointer.is_file():
        current = read_latest(data_dir)
        if current.fetched_at > snapshot.fetched_at:
            return
    pointer.write_text(snapshot.snapshot_id + "\n", encoding="utf-8")
