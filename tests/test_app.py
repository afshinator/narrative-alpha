"""Tests for narrative.app — Modal orchestration (Task 8)."""

import os
import sys
import tempfile
import json
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

# ── Mock modal module before any imports ──
# Modal constructors run at import time; must be mocked first.

_mock_module = MagicMock()
_mock_module.Volume.from_name.return_value = MagicMock()
_mock_module.Image.debian_slim.return_value.pip_install.return_value = MagicMock()
_mock_module.Secret.from_dotenv.return_value = MagicMock()

def _fake_decorator(**kwargs):
    """Identity decorator that passes the function through unchanged."""
    def wrapper(fn):
        return fn
    return wrapper

_mock_module.function = _fake_decorator
_mock_module.fastapi_endpoint = _fake_decorator
_mock_module.App.return_value.function = _fake_decorator
_mock_module.App.return_value.fastapi_endpoint = _fake_decorator

sys.modules['modal'] = _mock_module


# ── Slice 1: File exists, parses, imports resolve ──

def test_app_exists_and_parsable():
    """app.py exists and has no SyntaxError."""
    import ast
    with open(os.path.join(os.path.dirname(__file__), "..", "narrative", "app.py")) as f:
        source = f.read()
    ast.parse(source)


def test_app_imports_and_functions_accessible():
    """All expected symbols are importable from narrative.app."""
    import narrative.app

    # Core pipeline function
    assert callable(narrative.app._run_startup_init)

    # Modal endpoints (decorated but callable after mocking)
    assert callable(narrative.app.execute_forensic_pipeline)
    assert callable(narrative.app.update_llm_config)
    assert callable(narrative.app.run_historical_backtest)

    # Modal app object
    assert narrative.app.app is not None


# ── Slice 2: _run_startup_init behavior ──

@pytest.fixture
def temp_narrative_root(tmp_path):
    """Temporary NARRATIVE_ALPHA_ROOT for isolated init testing."""
    root = str(tmp_path / ".narrative_alpha")
    os.makedirs(root, exist_ok=True)
    return root


def test_startup_init_creates_db_and_config(temp_narrative_root):
    """_run_startup_init creates outlet_reputation.db and llm_config.json."""
    import narrative.app

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": temp_narrative_root}, clear=True):
        narrative.app._run_startup_init()

    db_path = os.path.join(temp_narrative_root, "outlet_reputation.db")
    assert os.path.exists(db_path), f"DB not created at {db_path}"

    config_path = os.path.join(temp_narrative_root, "llm_config.json")
    assert os.path.exists(config_path), f"Config not created at {config_path}"

    with open(config_path) as f:
        config = json.load(f)
    assert "call_1_entity_normalization" in config
    assert "call_4_forensic_synthesis" in config


def test_startup_init_idempotent(temp_narrative_root):
    """Calling _run_startup_init twice does not crash."""
    import narrative.app

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": temp_narrative_root}, clear=True):
        narrative.app._run_startup_init()
        narrative.app._run_startup_init()

    assert os.path.exists(os.path.join(temp_narrative_root, "outlet_reputation.db"))


# ── Slice 3: _run_pipeline orchestration ──

def test_run_pipeline_corpus_floor_gate():
    """When build_ingestion_manifest returns floor gate, pipeline returns it."""
    import narrative.app

    floor_response = {"validation_tracking": {"current_state": "INSUFFICIENT_CORPUS_FLOOR"}}

    with patch.object(narrative.app, '_run_startup_init'), \
         patch.object(narrative.app, 'discover_articles', return_value={"organic": []}), \
         patch.object(narrative.app, 'build_ingestion_manifest', return_value=floor_response):
        result = narrative.app._run_pipeline(
            keyword="test",
            vertical="TECHNOLOGY",
            api_key="key",
            unlocker_zone="zone",
            db_path="/tmp/test.db",
        )
    assert result == floor_response


def test_run_pipeline_builds_context_bundle():
    """Pipeline builds context_bundle with per_source entries and passes to synthesis."""
    import narrative.app

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

    with patch.object(narrative.app, '_run_startup_init'), \
         patch.object(narrative.app, 'get_hardened_db_connection') as mock_db, \
         patch.object(narrative.app, 'discover_articles', return_value={"organic": []}), \
         patch.object(narrative.app, 'build_ingestion_manifest', return_value=fake_manifest), \
         patch.object(narrative.app, 'handle_outlet_registration', return_value="RATED_GOOD"), \
         patch.object(narrative.app, 'read_outlet_reputation', return_value={"rating_status": "RATED_GOOD"}), \
         patch.object(narrative.app, 'run_entity_normalization', return_value={}), \
         patch.object(narrative.app, 'run_linguistic_neutralization', return_value=["neutral"]), \
         patch.object(narrative.app, 'extract_all_graphs', return_value=fake_graphs), \
         patch.object(narrative.app, 'compute_framing_volatility', return_value=([0.1], ["LOW"])), \
         patch.object(narrative.app, 'compute_pre_synthesis_context', return_value={
             "narrative_clusters": {}, "fracture_candidates": [], "term_shifts": []
         }), \
         patch.object(narrative.app, 'synthesize_forensic_report', return_value=fake_report), \
         patch.object(narrative.app, 'inject_labels', return_value=fake_report), \
         patch.object(narrative.app, 'write_outlier_signal'), \
         patch.object(narrative.app, 'vol', MagicMock()):
        # _run_pipeline calls get_hardened_db_connection twice (ingestion + outlier write)
        mock_db.return_value = MagicMock()
        result = narrative.app._run_pipeline(
            keyword="test",
            vertical="TECHNOLOGY",
            api_key="key",
            unlocker_zone="zone",
            db_path="/tmp/test.db",
        )

    assert result is fake_report


def test_run_pipeline_sets_corpus_capped():
    """Pipeline sets corpus_capped flag from manifest into event_meta."""
    import narrative.app

    fake_manifest = {
        "cluster_id": "EVT-20260530-TEST",
        "documents": [
            {"source_domain": "a.com", "source_name": "A", "raw_text_content": "t"}
        ],
        "corpus_count": 1,
        "corpus_capped": True,
    }
    fake_report = {"distortion_matrix": [], "event_meta": {}}

    with patch.object(narrative.app, '_run_startup_init'), \
         patch.object(narrative.app, 'get_hardened_db_connection') as mock_db, \
         patch.object(narrative.app, 'discover_articles', return_value={"organic": []}), \
         patch.object(narrative.app, 'build_ingestion_manifest', return_value=fake_manifest), \
         patch.object(narrative.app, 'handle_outlet_registration', return_value="RATED_GOOD"), \
         patch.object(narrative.app, 'read_outlet_reputation', return_value={}), \
         patch.object(narrative.app, 'run_entity_normalization', return_value={}), \
         patch.object(narrative.app, 'run_linguistic_neutralization', return_value=["n"]), \
         patch.object(narrative.app, 'extract_all_graphs', return_value=[
             {"_source_domain": "a.com", "_source_name": "A", "nodes": [], "edges": []}
         ]), \
         patch.object(narrative.app, 'compute_framing_volatility', return_value=([0.0], ["LOW"])), \
         patch.object(narrative.app, 'compute_pre_synthesis_context', return_value={
             "narrative_clusters": {}, "fracture_candidates": [], "term_shifts": []
         }), \
         patch.object(narrative.app, 'synthesize_forensic_report', return_value=fake_report), \
         patch.object(narrative.app, 'inject_labels', return_value=fake_report), \
         patch.object(narrative.app, 'write_outlier_signal'), \
         patch.object(narrative.app, 'vol', MagicMock()):
        mock_db.return_value = MagicMock()
        result = narrative.app._run_pipeline(
            keyword="test", vertical="TECHNOLOGY",
            api_key="key", unlocker_zone="zone",
            db_path="/tmp/test.db",
        )

    assert result["event_meta"]["corpus_capped"] is True


# ── Slice 4: update_llm_config validation ──

def test_settings_rejects_missing_slot():
    """update_llm_config returns error for missing required slot."""
    import narrative.app

    async def _run():
        with patch.object(narrative.app, '_run_startup_init'):
            return await narrative.app.update_llm_config({
                "call_1_entity_normalization": {},
                "call_2_linguistic_neutralization": {},
                "call_3_graph_extraction": {},
                # missing call_4_forensic_synthesis
            })

    result = asyncio.run(_run())
    assert "error" in result
    assert "call_4_forensic_synthesis" in result["error"]


def test_settings_rejects_invalid_slot_structure():
    """update_llm_config returns error for slot with missing required fields."""
    import narrative.app

    async def _run():
        with patch.object(narrative.app, '_run_startup_init'):
            return await narrative.app.update_llm_config({
                "call_1_entity_normalization": {"provider": "openai"},
                "call_2_linguistic_neutralization": {},
                "call_3_graph_extraction": {},
                "call_4_forensic_synthesis": {},
            })

    result = asyncio.run(_run())
    assert "error" in result


def test_settings_accepts_valid_config(temp_narrative_root):
    """update_llm_config writes valid config and returns success."""
    import narrative.app

    valid_config = {
        "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
    }

    async def _run():
        with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": temp_narrative_root}, clear=True), \
             patch.object(narrative.app, '_run_startup_init'), \
             patch.object(narrative.app, 'vol', MagicMock()):
            return await narrative.app.update_llm_config(valid_config)

    result = asyncio.run(_run())
    assert result["status"] == "ok"
    config_path = os.path.join(temp_narrative_root, "llm_config.json")
    assert os.path.exists(config_path)
    with open(config_path) as f:
        written = json.load(f)
    assert written["call_3_graph_extraction"]["provider"] == "openai"
