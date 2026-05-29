"""Tests for reputation.py — SQLite persistence layer."""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from reputation import (
    _write_with_retry,
    handle_outlet_registration,
    init_db,
    read_outlet_reputation,
    write_outlier_signal,
    write_ingestion_log,
)


class TestInitDb:
    def test_creates_three_tables(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert tables == [
            "ingestion_manifest_log",
            "outlet_reputation",
            "outlier_tracking",
        ]

    def test_idempotent(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        init_db(conn)

    def test_ingestion_log_has_composite_pk(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ingestion_manifest_log)")
        columns = {row[1]: row for row in cursor.fetchall()}
        assert columns["canonical_url"][5] == 1
        assert columns["query_id"][5] == 2


class TestHandleOutletRegistration:
    def test_new_outlet_returns_unrated(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        status = handle_outlet_registration("example.com", "TECHNOLOGY", conn)
        assert status == "UNRATED"

    def test_existing_outlet_returns_stored_status(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        handle_outlet_registration("example.com", "TECHNOLOGY", conn)
        status = handle_outlet_registration("example.com", "TECHNOLOGY", conn)
        assert status == "UNRATED"

    def test_same_domain_different_vertical_is_new(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        handle_outlet_registration("example.com", "TECHNOLOGY", conn)
        status = handle_outlet_registration("example.com", "FINANCE", conn)
        assert status == "UNRATED"

    def test_stores_outlet_name(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        handle_outlet_registration(
            "example.com", "TECHNOLOGY", conn, outlet_name="Example News"
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT outlet_name FROM outlet_reputation "
            "WHERE domain = ? AND industry_vertical = ?",
            ("example.com", "TECHNOLOGY"),
        )
        assert cursor.fetchone()[0] == "Example News"


class TestReadOutletReputation:
    def test_returns_none_for_unknown(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        assert read_outlet_reputation("unknown.com", "TECHNOLOGY", conn) is None

    def test_returns_full_row_for_known(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        handle_outlet_registration(
            "example.com", "TECHNOLOGY", conn, outlet_name="Example"
        )
        result = read_outlet_reputation("example.com", "TECHNOLOGY", conn)
        assert result is not None
        assert result["domain"] == "example.com"
        assert result["industry_vertical"] == "TECHNOLOGY"
        assert result["rating_status"] == "UNRATED"
        assert result["outlet_name"] == "Example"


class TestWriteOutlierSignal:
    def test_inserts_signal(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        write_outlier_signal(
            "sig1", "cluster1", "example.com", "Some claim", "2026-01-01", conn
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT signal_id, cluster_id, origin_domain FROM outlier_tracking"
        )
        row = cursor.fetchone()
        assert row[0] == "sig1"
        assert row[1] == "cluster1"

    def test_ignore_duplicate_signal(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        write_outlier_signal(
            "sig1", "cluster1", "example.com", "Claim", "2026-01-01", conn
        )
        write_outlier_signal(
            "sig1", "cluster1", "example.com", "Claim", "2026-01-01", conn
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM outlier_tracking")
        assert cursor.fetchone()[0] == 1


class TestWriteIngestionLog:
    def make_doc(self, overrides: dict | None = None) -> dict:
        doc = {
            "source_domain": "example.com",
            "source_url": "https://example.com/article/1",
            "title": "Test Article",
            "published_at": "2026-01-01T00:00:00",
            "raw_text_content": "Body content here.",
            "fetch_status": 200,
            "passed_validation": 1,
        }
        doc.update(overrides or {})
        return doc

    def test_inserts_multiple_docs(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        docs = [
            self.make_doc({"source_url": f"https://example.com/a{i}"})
            for i in range(3)
        ]
        write_ingestion_log("q1", "test-topic", "2026-01-01", docs, conn)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingestion_manifest_log")
        assert cursor.fetchone()[0] == 3

    def test_same_url_different_query_id_both_persist(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        doc = self.make_doc()
        write_ingestion_log("q1", "test", "2026-01-01", [doc], conn)
        write_ingestion_log("q2", "test", "2026-01-02", [doc], conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT query_id FROM ingestion_manifest_log ORDER BY query_id"
        )
        assert [row[0] for row in cursor.fetchall()] == ["q1", "q2"]

    def test_same_url_same_query_id_replaces(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        doc1 = self.make_doc({"fetch_status": 200, "passed_validation": 1})
        write_ingestion_log("q1", "test", "2026-01-01", [doc1], conn)
        doc2 = self.make_doc({"fetch_status": 403, "passed_validation": 0})
        write_ingestion_log("q1", "test", "2026-01-02", [doc2], conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fetch_status, passed_validation FROM ingestion_manifest_log"
        )
        row = cursor.fetchone()
        assert row[0] == 403
        assert row[1] == 0

    def test_stores_body_length_correctly(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        doc = self.make_doc({"raw_text_content": "Hello World"})
        write_ingestion_log("q1", "test", "2026-01-01", [doc], conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT body_length, body_text FROM ingestion_manifest_log"
        )
        row = cursor.fetchone()
        assert row[0] == len("Hello World")
        assert row[1] == "Hello World"

    def test_handles_missing_optional_fields(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        doc = {
            "source_domain": "example.com",
            "source_url": "https://example.com/article/1",
            "title": "No extra fields",
        }
        write_ingestion_log("q1", "test", "2026-01-01", [doc], conn)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingestion_manifest_log")
        assert cursor.fetchone()[0] == 1


class TestWriteWithRetry:
    def test_raises_after_max_retries(self):
        conn = MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError("database is locked")
        with pytest.raises(sqlite3.OperationalError):
            _write_with_retry(conn, "INSERT INTO t VALUES (?)", (1,), max_retries=3)
        assert conn.execute.call_count == 3
        assert conn.rollback.call_count == 3

    def test_calls_rollback_on_failure(self):
        conn = MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError("database is locked")
        with pytest.raises(sqlite3.OperationalError):
            _write_with_retry(conn, "INSERT INTO t VALUES (?)", (1,), max_retries=1)
        conn.rollback.assert_called_once()

    def test_succeeds_after_retry(self):
        conn = MagicMock()
        conn.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            MagicMock(),
        ]
        _write_with_retry(conn, "INSERT INTO t VALUES (?)", (1,), max_retries=3)
        assert conn.execute.call_count == 3
        conn.commit.assert_called_once()

    def test_non_locked_error_does_not_retry(self):
        conn = MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError("database is corrupt")
        with pytest.raises(sqlite3.OperationalError):
            _write_with_retry(conn, "INSERT INTO t VALUES (?)", (1,), max_retries=3)
        assert conn.execute.call_count == 1
        conn.rollback.assert_called_once()

