from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

from indie_brief.errors import BriefError


class Settings(BaseModel):
    data_dir: Path
    api_keys: set[str]
    host: str = "127.0.0.1"
    port: int = 8787


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("INDIE_BRIEF_DATA_DIR", "data")).expanduser()
    keys = _keys_from_env()
    keys.update(_keys_from_file(data_dir / "keys"))
    host = os.environ.get("INDIE_BRIEF_HOST", "127.0.0.1").strip() or "127.0.0.1"
    raw_port = os.environ.get("INDIE_BRIEF_PORT", "8787")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise BriefError("BAD_CONFIG", f"INDIE_BRIEF_PORT 不是整数: {raw_port}") from exc
    if port < 1 or port > 65535:
        raise BriefError("BAD_CONFIG", f"INDIE_BRIEF_PORT 超出范围: {port}")
    return Settings(data_dir=data_dir, api_keys=keys, host=host, port=port)


def _keys_from_env() -> set[str]:
    raw = os.environ.get("INDIE_BRIEF_API_KEYS", "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _keys_from_file(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if item and not item.startswith("#"):
            keys.add(item)
    return keys
