"""Layer 2: Persistence — SQLite reputation ledger and ingestion log.

Pure sync functions. Orchestrator wraps in asyncio.to_thread if needed.
"""

from __future__ import annotations

import os
import sqlite3
import time

_DEFAULT_DB_PATH = "/root/.narrative_alpha/outlet_reputation.db"


def _db_path() -> str:
    return os.environ.get("NARRATIVE_DB_PATH", _DEFAULT_DB_PATH)


def get_hardened_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _write_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple,
    max_retries: int = 3,
) -> None:
    delay = 0.1
    for attempt in range(max_retries):
        try:
            conn.execute(sql, params)
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            conn.rollback()
            if "locked" not in str(exc).lower() or attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS outlet_reputation (
            domain TEXT NOT NULL,
            industry_vertical TEXT NOT NULL,
            outlet_name TEXT,
            total_outlier_nodes_produced INTEGER DEFAULT 0,
            total_absorbed_nodes INTEGER DEFAULT 0,
            total_decayed_nodes INTEGER DEFAULT 0,
            scatter_shot_anomaly_factor REAL DEFAULT NULL,
            historical_origin_validation_rate REAL DEFAULT NULL,
            back_test_article_count INTEGER DEFAULT 0,
            rating_status TEXT DEFAULT 'UNRATED',
            last_updated TEXT,
            PRIMARY KEY (domain, industry_vertical)
        );

        CREATE TABLE IF NOT EXISTS outlier_tracking (
            signal_id TEXT PRIMARY KEY,
            cluster_id TEXT,
            origin_domain TEXT,
            extracted_claim TEXT,
            timestamp_first_seen TEXT,
            current_state TEXT DEFAULT 'PENDING',
            evaluation_deadline TEXT,
            absorbed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ingestion_manifest_log (
            query_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            discovery_timestamp TEXT NOT NULL,
            source_domain TEXT NOT NULL,
            canonical_url TEXT NOT NULL,
            title TEXT NOT NULL,
            published_at TEXT,
            fetch_status INTEGER,
            body_text TEXT NOT NULL,
            body_length INTEGER NOT NULL,
            passed_validation INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (canonical_url, query_id)
        );
    """)
    conn.commit()


def handle_outlet_registration(
    domain: str,
    vertical: str,
    conn: sqlite3.Connection,
    outlet_name: str = "",
) -> str:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rating_status FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical),
    )
    row = cursor.fetchone()

    if not row:
        _write_with_retry(
            conn,
            "INSERT INTO outlet_reputation (domain, industry_vertical, outlet_name, rating_status, last_updated) "
            "VALUES (?, ?, ?, 'UNRATED', datetime('now'))",
            (domain, vertical, outlet_name),
        )
        return "UNRATED"

    return row[0]


def read_outlet_reputation(
    domain: str,
    vertical: str,
    conn: sqlite3.Connection,
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical),
    )
    row = cursor.fetchone()
    if not row:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def write_outlier_signal(
    signal_id: str,
    cluster_id: str,
    origin_domain: str,
    extracted_claim: str,
    timestamp: str,
    conn: sqlite3.Connection,
) -> None:
    _write_with_retry(
        conn,
        "INSERT OR IGNORE INTO outlier_tracking "
        "(signal_id, cluster_id, origin_domain, extracted_claim, timestamp_first_seen) "
        "VALUES (?, ?, ?, ?, ?)",
        (signal_id, cluster_id, origin_domain, extracted_claim, timestamp),
    )


def write_ingestion_log(
    query_id: str,
    topic: str,
    discovery_timestamp: str,
    docs: list[dict],
    conn: sqlite3.Connection,
) -> None:
    for doc in docs:
        raw_text = doc.get("raw_text_content", "")
        _write_with_retry(
            conn,
            "INSERT OR REPLACE INTO ingestion_manifest_log "
            "(query_id, topic, discovery_timestamp, source_domain, canonical_url, "
            "title, published_at, fetch_status, body_text, body_length, passed_validation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                query_id,
                topic,
                discovery_timestamp,
                doc.get("source_domain", ""),
                doc.get("source_url", ""),
                doc.get("title", ""),
                doc.get("published_at"),
                doc.get("fetch_status"),
                raw_text,
                doc.get("body_length", len(raw_text)),
                doc.get("passed_validation", 0),
            ),
        )
