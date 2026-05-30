"""Tests for narrative.server — FastAPI local backend (Task 9)."""

import json
import os
from unittest.mock import patch, MagicMock
import warnings
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    """TestClient with clean state."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        return TestClient(app)


def test_get_config_returns_defaults(client):
    """GET /api/config returns valid LLMConfig when no file exists."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "call_1_entity_normalization" in data
    assert data["call_1_entity_normalization"]["provider"] == "deepseek"
    assert data["call_1_entity_normalization"]["model"] == "deepseek-v4-flash"


def test_post_config_saves_and_returns(client, tmp_path):
    """POST /api/config writes valid config and returns ok."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        payload = {
            "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
            "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        }
        resp = tc.post("/api/config", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        config_path = os.path.join(str(tmp_path), "llm_config.json")
        assert os.path.exists(config_path)
        with open(config_path) as f:
            written = json.load(f)
        assert written["call_3_graph_extraction"]["model"] == "gpt-4"


def test_post_config_rejects_missing_slot(client):
    """POST /api/config returns 422 for missing required slot."""
    resp = client.post("/api/config", json={
        "call_1_entity_normalization": {},
        "call_2_linguistic_neutralization": {},
        "call_3_graph_extraction": {},
    })
    assert resp.status_code == 422


def test_get_reports_empty(client):
    """GET /api/reports returns empty list when no reports exist."""
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_reports_with_file(client, tmp_path):
    """GET /api/reports lists reports from data/reports/."""
    reports_dir = os.path.join(str(tmp_path), "data", "reports")
    os.makedirs(reports_dir)
    with open(os.path.join(reports_dir, "EVT-001.json"), "w") as f:
        json.dump({
            "event_meta": {
                "cluster_id": "EVT-001", "search_query": "test",
                "industry_vertical": "TECH", "timestamp_utc": "now",
                "corpus_count": 5, "corpus_capped": False,
            }
        }, f)

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cluster_id"] == "EVT-001"


def test_get_report_by_id(client, tmp_path):
    """GET /api/reports/{cluster_id} returns full ForensicReport."""
    reports_dir = os.path.join(str(tmp_path), "data", "reports")
    os.makedirs(reports_dir)
    report = {
        "event_meta": {
            "cluster_id": "EVT-001", "search_query": "test",
            "industry_vertical": "TECH", "timestamp_utc": "now",
            "corpus_count": 5, "corpus_capped": False,
        },
        "consensus_reality_graph": {"consensus_summary": "none", "verified_anchor_nodes": [], "primary_verifications": []},
        "distortion_matrix": [], "outlier_signals": [], "reputation_warnings": [],
        "reality_divergence_zones": [], "reality_fractures": [], "narrative_regime_shifts": [],
    }
    with open(os.path.join(reports_dir, "EVT-001.json"), "w") as f:
        json.dump(report, f)

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/reports/EVT-001")
        assert resp.status_code == 200
        assert resp.json()["event_meta"]["cluster_id"] == "EVT-001"


def test_get_report_missing_returns_404(client):
    """GET /api/reports/nonexistent returns 404."""
    resp = client.get("/api/reports/NONEXISTENT")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert "error" in data["detail"]


# ── Pipeline unit tests (migrated from test_app.py) ──


def test_startup_init_creates_db_and_config(tmp_path):
    """_run_startup_init creates outlet_reputation.db and llm_config.json."""
    from narrative.pipeline import _run_startup_init

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        _run_startup_init()

    db_path = os.path.join(str(tmp_path), "outlet_reputation.db")
    assert os.path.exists(db_path), f"DB not created at {db_path}"

    config_path = os.path.join(str(tmp_path), "llm_config.json")
    assert os.path.exists(config_path), f"Config not created at {config_path}"

    with open(config_path) as f:
        config = json.load(f)
    assert "call_1_entity_normalization" in config
    assert "call_4_forensic_synthesis" in config


def test_startup_init_idempotent(tmp_path):
    """Calling _run_startup_init twice does not crash."""
    from narrative.pipeline import _run_startup_init

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        _run_startup_init()
        _run_startup_init()

    assert os.path.exists(os.path.join(str(tmp_path), "outlet_reputation.db"))


def test_run_pipeline_corpus_floor_gate():
    """When build_ingestion_manifest returns floor gate, pipeline returns it."""
    import narrative.pipeline as mod

    floor_response = {"validation_tracking": {"current_state": "INSUFFICIENT_CORPUS_FLOOR"}}

    with patch.object(mod, 'discover_articles', return_value={"organic": []}), \
         patch.object(mod, 'build_ingestion_manifest', return_value=floor_response):
        result = mod._run_pipeline(
            keyword="test",
            vertical="TECHNOLOGY",
            api_key="key",
            unlocker_zone="zone",
            db_path="/tmp/test.db",
        )
    assert result == floor_response


def test_run_pipeline_builds_context_bundle():
    """Pipeline builds context_bundle with per_source entries and passes to synthesis."""
    import narrative.pipeline as mod

    fake_manifest = {
        "cluster_id": "EVT-20260530-TEST",
        "documents": [
            {
                "source_domain": "example.com",
                "source_name": "Example News",
                "raw_text_content": "raw text here",
            }
        ],
        "corpus_count": 1,
    }
    fake_graphs = [
        {
            "_source_domain": "example.com",
            "_source_name": "Example News",
            "nodes": ["node_a"],
            "edges": [],
        }
    ]
    fake_report = {"distortion_matrix": [], "event_meta": {}}

    with patch.object(mod, 'get_hardened_db_connection') as mock_db, \
         patch.object(mod, 'discover_articles', return_value={"organic": []}), \
         patch.object(mod, 'build_ingestion_manifest', return_value=fake_manifest), \
         patch.object(mod, 'handle_outlet_registration', return_value="RATED_GOOD"), \
         patch.object(mod, 'read_outlet_reputation', return_value={"rating_status": "RATED_GOOD"}), \
         patch.object(mod, 'run_entity_normalization', return_value={}), \
         patch.object(mod, 'run_linguistic_neutralization', return_value=["neutral"]), \
         patch.object(mod, 'extract_all_graphs', return_value=fake_graphs), \
         patch.object(mod, 'compute_framing_volatility', return_value=([0.1], ["LOW"])), \
         patch.object(mod, 'compute_pre_synthesis_context', return_value={
             "narrative_clusters": {}, "fracture_candidates": [], "term_shifts": []
         }), \
         patch.object(mod, 'synthesize_forensic_report', return_value=fake_report), \
         patch.object(mod, 'inject_labels', return_value=fake_report), \
         patch.object(mod, 'write_outlier_signal'):
        mock_db.return_value = MagicMock()
        result = mod._run_pipeline(
            keyword="test",
            vertical="TECHNOLOGY",
            api_key="key",
            unlocker_zone="zone",
            db_path="/tmp/test.db",
        )

    assert result is fake_report


def test_run_pipeline_sets_corpus_capped():
    """Pipeline sets corpus_capped flag from manifest into event_meta."""
    import narrative.pipeline as mod

    fake_manifest = {
        "cluster_id": "EVT-20260530-TEST",
        "documents": [
            {"source_domain": "a.com", "source_name": "A", "raw_text_content": "t"}
        ],
        "corpus_count": 1,
        "corpus_capped": True,
    }
    fake_report = {"distortion_matrix": [], "event_meta": {}}

    with patch.object(mod, 'get_hardened_db_connection') as mock_db, \
         patch.object(mod, 'discover_articles', return_value={"organic": []}), \
         patch.object(mod, 'build_ingestion_manifest', return_value=fake_manifest), \
         patch.object(mod, 'handle_outlet_registration', return_value="RATED_GOOD"), \
         patch.object(mod, 'read_outlet_reputation', return_value={}), \
         patch.object(mod, 'run_entity_normalization', return_value={}), \
         patch.object(mod, 'run_linguistic_neutralization', return_value=["n"]), \
         patch.object(mod, 'extract_all_graphs', return_value=[
             {"_source_domain": "a.com", "_source_name": "A", "nodes": [], "edges": []}
         ]), \
         patch.object(mod, 'compute_framing_volatility', return_value=([0.0], ["LOW"])), \
         patch.object(mod, 'compute_pre_synthesis_context', return_value={
             "narrative_clusters": {}, "fracture_candidates": [], "term_shifts": []
         }), \
         patch.object(mod, 'synthesize_forensic_report', return_value=fake_report), \
         patch.object(mod, 'inject_labels', return_value=fake_report), \
         patch.object(mod, 'write_outlier_signal'):
        mock_db.return_value = MagicMock()
        result = mod._run_pipeline(
            keyword="test", vertical="TECHNOLOGY",
            api_key="key", unlocker_zone="zone",
            db_path="/tmp/test.db",
        )

    assert result["event_meta"]["corpus_capped"] is True


# ── Settings endpoint tests (migrated from test_app.py) ──


def test_settings_rejects_invalid_slot_structure(client):
    """POST /api/config returns 422 for slot with missing required fields."""
    resp = client.post("/api/config", json={
        "call_1_entity_normalization": {"provider": "openai"},
        "call_2_linguistic_neutralization": {},
        "call_3_graph_extraction": {},
        "call_4_forensic_synthesis": {},
    })
    assert resp.status_code == 422


def test_settings_accepts_valid_config(tmp_path):
    """POST /api/config writes valid config and returns success."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        valid_config = {
            "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
            "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        }
        resp = tc.post("/api/config", json=valid_config)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        config_path = os.path.join(str(tmp_path), "llm_config.json")
        assert os.path.exists(config_path)
        with open(config_path) as f:
            written = json.load(f)
        assert written["call_3_graph_extraction"]["provider"] == "openai"


def test_post_config_rejects_unknown_fields(client):
    """POST /api/config returns 422 for extra fields not in LLMConfig."""
    payload = {
        "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        "extra_field": "should_not_be_allowed",
    }
    resp = client.post("/api/config", json=payload)
    assert resp.status_code == 422


def test_get_report_rejects_path_traversal(client):
    """GET /api/reports with .. in cluster_id returns 400."""
    # Double-encoding preserves %2e as a single path segment that httpx
    # doesn't normalize. FastAPI decodes it to ".." inside the handler
    # where our guard catches it.
    resp = client.get("/api/reports/%252e%252e")
    assert resp.status_code == 400
    assert "Invalid cluster_id" in resp.json()["detail"]


def test_pipeline_rejects_missing_env_vars(client):
    """POST /api/pipeline returns 503 when env vars are missing."""
    from narrative.server import app as _
    resp = client.post("/api/pipeline", json={"keyword": "test", "vertical": "TECHNOLOGY"})
    assert resp.status_code == 503
    data = resp.json()
    assert "detail" in data
    assert "BRIGHTDATA_API_KEY" in data["detail"]


def test_pipeline_returns_500_on_crash():
    """POST /api/pipeline returns 500 when _run_pipeline raises."""
    with patch.dict(os.environ, {
        "NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative",
        "BRIGHTDATA_API_KEY": "test_key",
        "BRIGHTDATA_UNLOCKER_ZONE": "test_zone",
    }, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        import narrative.server as srv
        original = srv._run_pipeline

        def crashing_run(*args, **kwargs):
            raise RuntimeError("BrightData timeout")

        srv._run_pipeline = crashing_run
        try:
            resp = tc.post("/api/pipeline", json={"keyword": "test", "vertical": "TECHNOLOGY"})
            assert resp.status_code == 500
            assert "error" in resp.json()
        finally:
            srv._run_pipeline = original
