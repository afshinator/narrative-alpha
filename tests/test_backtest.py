"""Tests for narrative/backtest.py — historical back-test worker."""

import os
import pytest
from unittest.mock import MagicMock

from narrative.backtest import execute_historical_backtest


def _serp_result(title="Article", link="https://example.com/a", source="Example"):
    return {
        "title": title,
        "link": link,
        "source": source,
        "display_link": link,
        "snippet": "A snippet.",
        "published_at": "2026-05-28T12:00:00Z",
    }


def _serp_response(count=10):
    results = [_serp_result(f"Article {i}", f"https://src{i}.com/a") for i in range(count)]
    return {"organic": results, "news": results}


def _valid_body():
    return "Article body with sufficient content for validation purposes. " * 30


class TestExecuteHistoricalBacktest:

    def test_importable_and_callable(self):
        assert callable(execute_historical_backtest)

    def test_accepts_domain_and_vertical(self):
        result = execute_historical_backtest("example.com", "TECHNOLOGY")
        assert result is None

    def test_accepts_empty_strings(self):
        result = execute_historical_backtest("", "")
        assert result is None

    def test_has_docstring(self):
        doc = execute_historical_backtest.__doc__
        assert doc is not None
        assert "historical" in doc
        assert "consensus-supported" in doc
        assert "consensus-isolated" in doc

    # ── Floor gate tests ──

    def test_target_floor_gate_skips_db_write(self, monkeypatch):
        """Target URL returns < 5 valid SERP results — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")

        def fake_discover(kw, zone, api_key, num=15, time_range=""):
            if "site:" in kw:
                return _serp_response(3)
            return _serp_response(10)

        monkeypatch.setattr("narrative.backtest.discover_articles", fake_discover)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    def test_baseline_floor_gate_skips_db_write(self, monkeypatch):
        """Baseline returns < 5 valid SERP results — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")

        def fake_discover(kw, zone, api_key, num=15, time_range=""):
            if "site:" in kw:
                return _serp_response(10)
            return _serp_response(3)

        monkeypatch.setattr("narrative.backtest.discover_articles", fake_discover)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    def test_target_fetch_floor_gate_skips_db_write(self, monkeypatch):
        """< 5 target articles survive fetch/extract — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))

        fetch_count = [0]

        def fake_fetch(url, zone, key):
            fetch_count[0] += 1
            return "<html><p>body</p></html>"

        def fake_extract(html):
            if fetch_count[0] <= 3:
                return _valid_body()
            return ""

        monkeypatch.setattr("narrative.backtest.fetch_article_body", fake_fetch)
        monkeypatch.setattr("narrative.backtest.extract_text", fake_extract)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    def test_baseline_fetch_floor_gate_skips_db_write(self, monkeypatch):
        """< 5 baseline articles survive fetch/extract — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))

        fetch_count = [0]
        target_fetch_limit = 10

        def fake_fetch(url, zone, key):
            fetch_count[0] += 1
            return "<html><p>body</p></html>"

        def fake_extract(html):
            if fetch_count[0] <= target_fetch_limit:
                return _valid_body()
            if fetch_count[0] <= target_fetch_limit + 3:
                return _valid_body()
            return ""

        monkeypatch.setattr("narrative.backtest.fetch_article_body", fake_fetch)
        monkeypatch.setattr("narrative.backtest.extract_text", fake_extract)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    # ── Consensus / classification tests ──

    def test_no_consensus_skips_db_write(self, monkeypatch):
        """Baseline graphs produce no consensus nodes — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {f"node_{i}": f"Node{i}" for i in range(100)})

        graph_index = [0]

        def fake_extract_graph(text, entity_dict, llm_config):
            idx = graph_index[0]
            graph_index[0] += 1
            if idx < 10:
                return {"nodes": ["entity_a", "entity_b"], "edges": []}
            return {"nodes": [f"node_{idx}"], "edges": []}

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    def test_zero_claims_skips_db_write(self, monkeypatch):
        """Target articles produce no nodes — no DB write."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {"entity_a": "EntityA"})

        graph_list = []

        def fake_extract_graph(text, entity_dict, llm_config):
            g = {"nodes": [], "edges": []}
            graph_list.append(g)
            return g

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_not_called()

    # ── Happy path metrics computation ──

    def test_happy_path_writes_correct_metrics(self, monkeypatch):
        """10 target + 10 baseline articles: SA and validation_rate computed correctly."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {"entity_a": "EntityA", "entity_b": "EntityB"})

        graph_index = [0]

        def fake_extract_graph(text, entity_dict, llm_config):
            idx = graph_index[0]
            graph_index[0] += 1
            if idx < 10:
                return {"nodes": ["entity_a", "entity_b"], "edges": []}
            return {"nodes": ["entity_a"], "edges": []}

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

        sql, params = mock_conn.execute.call_args[0]
        assert "UPDATE" in sql.upper()
        sa, validation_rate, article_count, domain, vert = params[:5]

        assert 0.0 <= sa <= 1.0
        assert 0.0 <= validation_rate <= 1.0
        assert article_count >= 5
        assert domain == "example.com"
        assert vert == "TECHNOLOGY"

    def test_happy_path_all_isolated(self, monkeypatch):
        """All target claims are isolated (baseline has no common nodes)."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {"entity_a": "EntityA", "entity_b": "EntityB"})

        graph_index = [0]

        def fake_extract_graph(text, entity_dict, llm_config):
            idx = graph_index[0]
            graph_index[0] += 1
            if idx < 10:
                return {"nodes": ["entity_b"], "edges": []}
            return {"nodes": ["entity_a"], "edges": []}

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_called_once()
        sql, params = mock_conn.execute.call_args[0]
        sa = params[0]
        validation_rate = params[1]

        assert sa == 1.0
        assert validation_rate == 0.0

    def test_happy_path_all_supported(self, monkeypatch):
        """All target claims appear in baseline consensus."""
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {"entity_a": "EntityA"})

        graph_index = [0]

        def fake_extract_graph(text, entity_dict, llm_config):
            idx = graph_index[0]
            graph_index[0] += 1
            return {"nodes": ["entity_a"], "edges": []}

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        mock_conn = MagicMock()
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection", lambda *a: mock_conn)
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        mock_conn.execute.assert_called_once()
        sql, params = mock_conn.execute.call_args[0]
        sa = params[0]
        validation_rate = params[1]

        assert sa == 0.0
        assert validation_rate == 1.0

    # ── DB write integration ──

    def test_cache_file_updated_on_success(self, monkeypatch, tmp_path):
        """On success, the backtest updates the outlet_reputation SQLite DB."""
        db_dir = tmp_path / "narrative_test"
        db_dir.mkdir()
        db_path = str(db_dir / "outlet_reputation.db")
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "key")
        monkeypatch.setenv("BRIGHTDATA_UNLOCKER_ZONE", "zone")
        monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(db_dir.parent))

        from narrative.reputation import get_hardened_db_connection, init_db
        conn = get_hardened_db_connection(db_path)
        init_db(conn)
        conn.execute("INSERT INTO outlet_reputation (domain, industry_vertical, rating_status) VALUES (?, ?, 'UNRATED')",
                     ("example.com", "TECHNOLOGY"))
        conn.commit()
        conn.close()

        monkeypatch.setattr("narrative.backtest.discover_articles",
                            lambda kw, z, k, num=15, time_range="": _serp_response(10))
        monkeypatch.setattr("narrative.backtest.fetch_article_body",
                            lambda *a: "<html><p>body</p></html>")
        monkeypatch.setattr("narrative.backtest.extract_text", lambda html: _valid_body())
        monkeypatch.setattr("narrative.backtest.run_entity_normalization",
                            lambda *a, **kw: {"entity_a": "EntityA", "entity_b": "EntityB"})

        graph_index = [0]

        def fake_extract_graph(text, entity_dict, llm_config):
            idx = graph_index[0]
            graph_index[0] += 1
            if idx < 10:
                return {"nodes": ["entity_a", "entity_b"], "edges": []}
            return {"nodes": ["entity_a"], "edges": []}

        monkeypatch.setattr("narrative.backtest.extract_graph", fake_extract_graph)
        monkeypatch.setattr("narrative.backtest.get_hardened_db_connection",
                            lambda *a: get_hardened_db_connection(db_path))
        monkeypatch.setattr("narrative.backtest.load_llm_config", lambda: {})

        execute_historical_backtest("example.com", "TECHNOLOGY")

        conn = get_hardened_db_connection(db_path)
        row = conn.execute(
            "SELECT scatter_shot_anomaly_factor, historical_origin_validation_rate, rating_status, back_test_article_count "
            "FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
            ("example.com", "TECHNOLOGY"),
        ).fetchone()
        conn.close()

        assert row is not None
        sa, validation_rate, rating, article_count = row
        assert rating == "RATED"
        assert article_count >= 5
        assert sa is not None
        assert validation_rate is not None
        assert 0.0 <= sa <= 1.0
        assert 0.0 <= validation_rate <= 1.0

    # ── discover_articles time_range parameter ──

    def test_discover_articles_passes_time_range(self):
        """discover_articles accepts time_range parameter for tbs=qdr:y."""
        from narrative.ingestion import discover_articles
        import inspect
        sig = inspect.signature(discover_articles)
        assert "time_range" in sig.parameters
        assert sig.parameters["time_range"].default == ""
