import json
from pathlib import Path

from fastapi.testclient import TestClient

from indie_brief.api import create_app
from indie_brief.cli import main
from indie_brief.config import Settings
from indie_brief.store import import_file

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot.json"


def _client(tmp_path: Path, keys: set[str] | None = None) -> TestClient:
    import_file(tmp_path, FIXTURE)
    app = create_app(Settings(data_dir=tmp_path, api_keys={"secret"} if keys is None else keys))
    return TestClient(app)


def test_health_is_public(tmp_path: Path):
    response = _client(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_today_requires_bearer(tmp_path: Path):
    client = _client(tmp_path)
    missing = client.get("/v1/today")
    assert missing.status_code == 401
    wrong = client.get("/v1/today", headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == 401


def test_today_returns_imported_brief(tmp_path: Path):
    response = _client(tmp_path).get(
        "/v1/today",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["arguments"][0]["url"] == "https://news.ycombinator.com/item?id=2"
    assert body["focus_matched"] is True


def test_missing_snapshot_is_404(tmp_path: Path):
    app = create_app(Settings(data_dir=tmp_path, api_keys={"secret"}))
    response = TestClient(app).get("/v1/today", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 404
    assert response.json()["code"] == "NO_SNAPSHOT"


def test_empty_key_set_rejects_everyone(tmp_path: Path):
    response = _client(tmp_path, keys=set()).get(
        "/v1/today",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 401


def test_cli_import_dir_keeps_newest(tmp_path, monkeypatch, capsys):
    older = tmp_path / "briefs" / "2026-09-26"
    newer = tmp_path / "briefs" / "2026-09-27"
    older.mkdir(parents=True)
    newer.mkdir()
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["fetched_at"] = "2026-09-26T12:00:00+08:00"
    (older / "120000.json").write_text(json.dumps(payload), encoding="utf-8")
    payload["fetched_at"] = "2026-09-27T12:00:00+08:00"
    (newer / "120000.json").write_text(json.dumps(payload), encoding="utf-8")
    data = tmp_path / "data"
    monkeypatch.setenv("INDIE_BRIEF_DATA_DIR", str(data))
    monkeypatch.delenv("INDIE_BRIEF_API_KEYS", raising=False)
    main(["import-dir", str(tmp_path / "briefs")])
    output = capsys.readouterr().out.strip().splitlines()
    assert output[0] == "imported 2"
    assert output[1] == "20260927T040000Z"

    main(["key"])
    printed = capsys.readouterr().out.strip()
    assert printed.startswith("ib_")
    stored = (data / "keys").read_text(encoding="utf-8").strip().splitlines()
    assert stored == [printed]
