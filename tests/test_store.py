import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from indie_brief.api import create_app
from indie_brief.cli import main
from indie_brief.config import Settings
from indie_brief.errors import BriefError
from indie_brief.store import import_dir, import_file, read_latest, snapshot_path


class SnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"

    def source(self, title, when, name="incoming.json"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "fetched_at": when,
                    "hn": [{"title": title, "url": "https://example.test/story"}],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_older_timestamp_in_same_second_keeps_newer_snapshot(self):
        newer = import_file(
            self.data, self.source("newer", "2026-10-09T12:00:00.900000+00:00")
        )
        older = import_file(
            self.data, self.source("older", "2026-10-09T12:00:00.100000+00:00")
        )
        self.assertEqual(newer.snapshot_id, older.snapshot_id)
        self.assertEqual(older, newer)
        self.assertEqual(read_latest(self.data), newer)

    def test_newer_timestamp_in_same_second_replaces_snapshot(self):
        import_file(self.data, self.source("older", "2026-10-09T12:00:00.100000+00:00"))
        newer = import_file(
            self.data, self.source("newer", "2026-10-09T12:00:00.900000+00:00")
        )
        self.assertEqual(read_latest(self.data), newer)

    def test_equal_timestamp_keeps_last_import(self):
        import_file(self.data, self.source("first", "2026-10-09T12:00:00+00:00"))
        last = import_file(self.data, self.source("last", "2026-10-09T12:00:00+00:00"))
        self.assertEqual(read_latest(self.data), last)

    def test_older_timestamp_in_other_second_keeps_latest(self):
        newer = import_file(self.data, self.source("newer", "2026-10-09T12:00:01+00:00"))
        import_file(self.data, self.source("older", "2026-10-09T12:00:00+00:00"))
        self.assertEqual(read_latest(self.data), newer)

    def test_directory_order_does_not_override_newer_same_second(self):
        self.source("newer", "2026-10-09T12:00:00.900000+00:00", "incoming/a.json")
        self.source("older", "2026-10-09T12:00:00.100000+00:00", "incoming/z.json")
        snapshots = import_dir(self.data, self.root / "incoming")
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[1], snapshots[0])
        self.assertEqual(read_latest(self.data), snapshots[0])

    def test_api_returns_newer_snapshot_for_both_import_orders(self):
        older = self.source("older", "2026-10-09T12:00:00.100000+00:00", "older.json")
        newer = self.source("newer", "2026-10-09T12:00:00.900000+00:00", "newer.json")
        for index, order in enumerate(((older, newer), (newer, older))):
            with self.subTest(order=index):
                data = self.root / f"api-{index}"
                for source in order:
                    result = import_file(data, source)
                settings = Settings(data_dir=data, api_keys={"synthetic-test-key"})
                response = TestClient(create_app(settings)).get(
                    "/v1/today", headers={"Authorization": "Bearer synthetic-test-key"}
                )
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["arguments"][0]["title"], "newer")
                self.assertEqual(body["fetched_at"], "2026-10-09T12:00:00.900000Z")
                self.assertEqual(body["snapshot_id"], result.snapshot_id)
                self.assertEqual(result.arguments[0].title, "newer")

    def test_cli_reports_processed_count_and_retained_id(self):
        self.source("newer", "2026-10-09T12:00:00.900000+00:00", "incoming/a.json")
        self.source("older", "2026-10-09T12:00:00.100000+00:00", "incoming/z.json")
        output = io.StringIO()
        settings = Settings(data_dir=self.data, api_keys=set())
        with patch("indie_brief.cli.load_settings", return_value=settings):
            with redirect_stdout(output):
                main(["import-dir", str(self.root / "incoming")])
        self.assertEqual(output.getvalue().splitlines(), ["imported 2", "20261009T120000Z"])
        self.assertEqual(read_latest(self.data).arguments[0].title, "newer")

    def test_invalid_import_leaves_previous_files_unchanged(self):
        import_file(self.data, self.source("original", "2026-10-09T12:00:00+00:00"))
        before = {path: path.read_bytes() for path in self.data.rglob("*") if path.is_file()}
        invalid = self.root / "invalid.json"
        for text in (
            "{",
            '{"fetched_at": "invalid"}',
            '{"fetched_at": "2026-10-09T12:00:00+00:00"}',
        ):
            with self.subTest(text=text):
                invalid.write_text(text, encoding="utf-8")
                with self.assertRaises(BriefError):
                    import_file(self.data, invalid)
                after = {
                    path: path.read_bytes() for path in self.data.rglob("*") if path.is_file()
                }
                self.assertEqual(after, before)

    def test_valid_import_can_replace_corrupted_snapshot(self):
        original = import_file(
            self.data, self.source("original", "2026-10-09T12:00:00+00:00")
        )
        snapshot_path(self.data, original.snapshot_id).write_text("{", encoding="utf-8")
        replacement = import_file(
            self.data, self.source("replacement", "2026-10-09T12:00:00+00:00")
        )
        self.assertEqual(read_latest(self.data), replacement)

    def test_temporary_file_is_not_exposed_to_reader(self):
        original = import_file(
            self.data, self.source("original", "2026-10-09T12:00:00+00:00")
        )
        snapshot_path(self.data, original.snapshot_id).with_suffix(".json.tmp").write_text(
            "{", encoding="utf-8"
        )
        self.assertEqual(read_latest(self.data), original)
