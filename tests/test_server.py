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


def test_get_reports_empty():
    """GET /api/reports returns empty list when no reports exist."""
    unique = f"/tmp/test_narrative_{os.getpid()}"
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": unique}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/reports")
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
            serp_zone="serp_api1",
            db_path="/tmp/test.db",
        )
    assert result == floor_response


def test_run_pipeline_builds_context_bundle():
    """Pipeline builds context_bundle with per_source entries and passes to synthesis."""
    import narrative.pipeline as mod

    fake_manifest = {
        "cluster_id": "EVT-20260530-TEST",
        "search_query": "test",
        "industry_vertical": "TECHNOLOGY",
        "timestamp_utc": "2026-05-30T00:00:00Z",
        "corpus_count": 1,
        "corpus_capped": False,
        "documents": [
            {
                "source_domain": "example.com",
                "source_name": "Example News",
                "raw_text_content": "raw text here",
            }
        ],
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
            serp_zone="serp_api1",
            db_path="/tmp/test.db",
        )

    assert result is fake_report


def test_run_pipeline_sets_corpus_capped():
    """Pipeline sets corpus_capped flag from manifest into event_meta."""
    import narrative.pipeline as mod

    fake_manifest = {
        "cluster_id": "EVT-20260530-TEST",
        "search_query": "test",
        "industry_vertical": "TECHNOLOGY",
        "timestamp_utc": "2026-05-30T00:00:00Z",
        "corpus_count": 1,
        "corpus_capped": True,
        "documents": [
            {"source_domain": "a.com", "source_name": "A", "raw_text_content": "t"}
        ],
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
            serp_zone="serp_api1", db_path="/tmp/test.db",
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


# ── Health endpoint tests ──


def test_health_returns_ok(client):
    """GET /api/health returns 200 with status ok."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_health_env_lists_variables(client):
    """GET /api/health/env lists env var statuses without LLM calls."""
    resp = client.get("/api/health/env")
    assert resp.status_code == 200
    data = resp.json()
    assert "present" in data
    assert "missing" in data
    assert "status" in data
    assert "detail" in data
    assert data["status"] in ("ok", "degraded")


_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def test_health_env_shows_present_when_set():
    """GET /api/health/env marks set vars as present."""
    env = {v: f"test_{v}" for v in _ENV_VARS}
    env["NARRATIVE_ALPHA_ROOT"] = "/tmp/test_narrative"
    with patch.dict(os.environ, env, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["present"]) == sorted(_ENV_VARS)
        assert data["missing"] == []
        assert data["status"] == "ok"


def test_health_env_shows_all_missing_when_unset():
    """GET /api/health/env marks all vars missing when none set."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert data["present"] == []
        assert sorted(data["missing"]) == sorted(_ENV_VARS)
        assert data["status"] == "degraded"


_TEST_ENV = {
    "NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative",
    "DEEPSEEK_API_KEY": "sk-test-deepseek",
    "OPENAI_API_KEY": "sk-test-openai",
    "BRIGHTDATA_API_KEY": "sk-test-brightdata",
    "BRIGHTDATA_SERP_ZONE": "serp_test",
    "BRIGHTDATA_UNLOCKER_ZONE": "unlocker_test",
}


def test_health_deep_returns_probe_results():
    """GET /api/health/deep returns structured probe results with mocked LLM."""
    with patch.dict(os.environ, _TEST_ENV, clear=True):
        from narrative.server import app
        with patch("narrative.server.call_llm", return_value='{"status": "ok"}'), \
             patch("narrative.server.get_embedding", return_value=[0.1, 0.2]):
            tc = TestClient(app)
            resp = tc.get("/api/health/deep")
            assert resp.status_code == 200
            data = resp.json()
            assert "checks" in data
            assert "status" in data
            assert "total_latency_ms" in data
            assert isinstance(data["total_latency_ms"], (int, float))


def test_health_deep_per_probe_status():
    """GET /api/health/deep reports per-probe status ok/error."""
    with patch.dict(os.environ, _TEST_ENV, clear=True):
        from narrative.server import app
        with patch("narrative.server.call_llm", return_value='{"status": "ok"}'), \
             patch("narrative.server.get_embedding", return_value=[0.1, 0.2]):
            tc = TestClient(app)
            resp = tc.get("/api/health/deep")
            data = resp.json()
            assert data["checks"]["deepseek_flash"]["status"] == "ok"
            assert data["checks"]["deepseek_pro_thinking"]["status"] == "ok"
            assert data["checks"]["openai_embedding"]["status"] == "ok"
            assert data["checks"]["config"]["status"] == "ok"
            assert data["status"] == "ok"


def test_health_deep_reports_errors():
    """GET /api/health/deep reports probe failures without crashing."""
    with patch.dict(os.environ, _TEST_ENV, clear=True):
        from narrative.server import app
        with patch("narrative.server.call_llm", side_effect=RuntimeError("API timeout")), \
             patch("narrative.server.get_embedding", side_effect=RuntimeError("Embedding failed")):
            tc = TestClient(app)
            resp = tc.get("/api/health/deep")
            assert resp.status_code == 200
            data = resp.json()
            assert data["checks"]["deepseek_flash"]["status"] == "error"
            assert data["checks"]["deepseek_pro_thinking"]["status"] == "error"
            assert data["checks"]["openai_embedding"]["status"] == "error"
            assert data["status"] == "degraded"


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


def test_pipeline_timeout_returns_504():
    """POST /api/pipeline returns 504 when pipeline exceeds timeout."""
    with patch.dict(os.environ, _TEST_ENV, clear=True):
        from narrative.server import app
        import narrative.server as srv

        def hanging_run(*a, **kw):
            import time
            time.sleep(5)

        original_run = srv._run_pipeline
        os.environ["NARRATIVE_PIPELINE_TIMEOUT"] = "1"
        srv._run_pipeline = hanging_run
        try:
            tc = TestClient(app)
            resp = tc.post("/api/pipeline", json={"keyword": "test", "vertical": "TECHNOLOGY"})
            assert resp.status_code == 504
            assert "timed out" in resp.json()["detail"].lower()
        finally:
            srv._run_pipeline = original_run
            del os.environ["NARRATIVE_PIPELINE_TIMEOUT"]


def test_pipeline_returns_500_on_crash():
    """POST /api/pipeline returns 500 when _run_pipeline raises."""
    with patch.dict(os.environ, {
        "NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative",
        "BRIGHTDATA_API_KEY": "test_key",
        "BRIGHTDATA_UNLOCKER_ZONE": "test_zone",
        "BRIGHTDATA_SERP_ZONE": "serp_api1",
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


# ── progress_cb forwarding tests ──


def test_run_pipeline_forwards_progress_cb_to_ingestion():
    """_run_pipeline passes progress_cb to build_ingestion_manifest."""
    import narrative.pipeline as mod

    ingestion_cb_calls = []

    def fake_manifest(keyword, serp_data, zone, api_key,
                      db_conn=None, logger_func=None, progress_cb=None):
        if progress_cb:
            progress_cb("ingesting", "Fetching test.com (1/5)")
            ingestion_cb_calls.append(True)
        return {"validation_tracking": {"current_state": "INSUFFICIENT_CORPUS_FLOOR"}}

    with patch.object(mod, "discover_articles", return_value={"organic": []}), \
         patch.object(mod, "build_ingestion_manifest", side_effect=fake_manifest), \
         patch.object(mod, "get_hardened_db_connection") as mock_db:
        mock_db.return_value = MagicMock()
        cb_received = []
        mod._run_pipeline(
            "test", "TECHNOLOGY", "key", "zone", "serp", "/tmp/test.db",
            progress_cb=lambda step, msg: cb_received.append((step, msg)),
        )

    assert any(step == "ingesting" for step, _ in cb_received)


def test_run_pipeline_forwards_progress_cb_to_analysis():
    """_run_pipeline passes progress_cb to extract_all_graphs."""
    import narrative.pipeline as mod

    analysis_cb_calls = []

    fake_manifest = {
        "cluster_id": "EVT-TEST",
        "search_query": "test",
        "industry_vertical": "TECHNOLOGY",
        "timestamp_utc": "2026-05-30T00:00:00Z",
        "corpus_count": 1,
        "corpus_capped": False,
        "documents": [{"source_domain": "a.com", "source_name": "A", "raw_text_content": "x"}],
    }

    def fake_graphs(docs, neutralized, canon, llm_config, progress_cb=None):
        if progress_cb:
            progress_cb("analyzing", "Graph extraction — A (1/1)")
            analysis_cb_calls.append(True)
        return [{"_source_domain": "a.com", "_source_name": "A", "nodes": [], "edges": []}]

    fake_report = {"distortion_matrix": [], "event_meta": {}}

    with patch.object(mod, "discover_articles", return_value={"organic": []}), \
         patch.object(mod, "build_ingestion_manifest", return_value=fake_manifest), \
         patch.object(mod, "handle_outlet_registration", return_value="RATED_GOOD"), \
         patch.object(mod, "read_outlet_reputation", return_value={}), \
         patch.object(mod, "run_entity_normalization", return_value={}), \
         patch.object(mod, "run_linguistic_neutralization", return_value=["neut"]), \
         patch.object(mod, "extract_all_graphs", side_effect=fake_graphs), \
         patch.object(mod, "compute_framing_volatility", return_value=([0.0], ["LOW"])), \
         patch.object(mod, "compute_pre_synthesis_context", return_value={
             "narrative_clusters": {}, "fracture_candidates": [], "term_shifts": []
         }), \
         patch.object(mod, "synthesize_forensic_report", return_value=fake_report), \
         patch.object(mod, "inject_labels", return_value=fake_report), \
         patch.object(mod, "write_outlier_signal"), \
         patch.object(mod, "get_hardened_db_connection") as mock_db:
        mock_db.return_value = MagicMock()
        cb_received = []
        mod._run_pipeline(
            "test", "TECHNOLOGY", "key", "zone", "serp", "/tmp/test.db",
            progress_cb=lambda step, msg: cb_received.append((step, msg)),
        )

    assert any(step == "analyzing" for step, _ in cb_received)


# ── SSE streaming endpoint tests ──


def test_stream_pipeline_missing_env_returns_error_event():
    """GET /api/pipeline/stream yields error SSE event when env vars missing."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = resp.read().decode()
    assert "error" in body


def test_stream_pipeline_yields_progress_and_complete(tmp_path):
    """GET /api/pipeline/stream yields all progress events and complete from mocked pipeline."""
    import narrative.server as srv

    fake_report = {
        "event_meta": {
            "cluster_id": "EVT-SSE-001", "search_query": "test",
            "industry_vertical": "TECHNOLOGY", "timestamp_utc": "now",
            "corpus_count": 3, "corpus_capped": False,
        },
        "distortion_matrix": [], "outlier_signals": [],
        "consensus_reality_graph": {"consensus_summary": "", "verified_anchor_nodes": [], "primary_verifications": []},
        "reputation_warnings": [], "reality_divergence_zones": [],
        "reality_fractures": [], "narrative_regime_shifts": [],
    }

    def fake_pipeline(keyword, vertical, api_key, unlocker_zone, serp_zone, db_path, progress_cb=None):
        if progress_cb:
            progress_cb("discovering", "Searching...")
            progress_cb("ingesting", "Fetching...")
            progress_cb("analyzing", "Analyzing...")
            progress_cb("synthesizing", "Synthesizing...")
        return fake_report

    env = {
        "NARRATIVE_ALPHA_ROOT": str(tmp_path),
        "BRIGHTDATA_API_KEY": "key",
        "BRIGHTDATA_UNLOCKER_ZONE": "zone",
        "BRIGHTDATA_SERP_ZONE": "serp",
    }
    original = srv._run_pipeline
    srv._run_pipeline = fake_pipeline
    try:
        with patch.dict(os.environ, env, clear=True):
            from narrative.server import app
            tc = TestClient(app)
            with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
                assert resp.status_code == 200
                body = resp.read().decode()
        for expected in ("discovering", "ingesting", "analyzing", "synthesizing", "complete", "EVT-SSE-001"):
            assert expected in body, f"Expected '{expected}' in SSE body"
    finally:
        srv._run_pipeline = original


def test_stream_pipeline_yields_error_on_crash(tmp_path):
    """GET /api/pipeline/stream yields error SSE event when pipeline raises."""
    import narrative.server as srv

    def crashing_pipeline(*args, **kwargs):
        raise RuntimeError("BrightData timeout")

    env = {
        "NARRATIVE_ALPHA_ROOT": str(tmp_path),
        "BRIGHTDATA_API_KEY": "key",
        "BRIGHTDATA_UNLOCKER_ZONE": "zone",
        "BRIGHTDATA_SERP_ZONE": "serp",
    }
    original = srv._run_pipeline
    srv._run_pipeline = crashing_pipeline
    try:
        with patch.dict(os.environ, env, clear=True):
            from narrative.server import app
            tc = TestClient(app)
            with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
                assert resp.status_code == 200
                body = resp.read().decode()
        assert "error" in body
    finally:
        srv._run_pipeline = original
