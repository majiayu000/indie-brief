from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

import uvicorn

from indie_brief.api import create_app
from indie_brief.config import load_settings
from indie_brief.errors import BriefError
from indie_brief.store import import_dir, import_file, read_latest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="indie-brief")
    sub = parser.add_subparsers(dest="command", required=True)

    key = sub.add_parser("key", help="生成一把 API key 并写入 data/keys")
    key.set_defaults(func=_cmd_key)

    serve = sub.add_parser("serve", help="启动只读简报接口")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.set_defaults(func=_cmd_serve)

    import_one = sub.add_parser("import", help="导入一份 TrendHunter 快照 JSON")
    import_one.add_argument("path")
    import_one.set_defaults(func=_cmd_import)

    import_many = sub.add_parser("import-dir", help="导入目录里的全部快照")
    import_many.add_argument("path")
    import_many.set_defaults(func=_cmd_import_dir)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except BriefError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        raise SystemExit(1) from exc


def _cmd_key(_args: argparse.Namespace) -> None:
    settings = load_settings()
    path = settings.data_dir / "keys"
    path.parent.mkdir(parents=True, exist_ok=True)
    token = "ib_" + secrets.token_urlsafe(32)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(token + "\n")
    os.chmod(path, 0o600)
    print(token)
    print(f"已写入 {path}", file=sys.stderr)


def _cmd_serve(args: argparse.Namespace) -> None:
    settings = load_settings()
    if not settings.api_keys:
        raise BriefError(
            "NO_KEYS",
            "没有 API key。先运行 indie-brief key，或设置 INDIE_BRIEF_API_KEYS。",
        )
    host = args.host or settings.host
    port = settings.port if args.port is None else args.port
    uvicorn.run(create_app(settings), host=host, port=port)


def _cmd_import(args: argparse.Namespace) -> None:
    settings = load_settings()
    snapshot = import_file(settings.data_dir, Path(args.path))
    print(snapshot.snapshot_id)


def _cmd_import_dir(args: argparse.Namespace) -> None:
    settings = load_settings()
    imported = import_dir(settings.data_dir, Path(args.path))
    latest = read_latest(settings.data_dir)
    print(f"imported {len(imported)}")
    print(latest.snapshot_id)
