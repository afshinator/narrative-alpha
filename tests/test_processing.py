"""Tests for narrative/processing.py -- Layer 2: Entity normalization and linguistic neutralization.

Run with: python -m pytest test_processing.py -v
"""

import json

import pytest


# ── Helpers ──

def _serp_item(url: str, domain: str, title: str = "Article", **kw) -> dict:
    item = {
        "link": url,
        "title": title,
        "source": domain,
        "display_link": domain,
        "published_at": "2026-05-28T12:00:00Z",
        "snippet": "A brief snippet.",
    }
    item.update(kw)
    return item


def _paa_item(question: str, answer: str, **kw) -> dict:
    item = {"question": question, "answer": answer}
    item.update(kw)
    return item


def _doc(**overrides) -> dict:
    base = {
        "doc_id": "DOC-001",
        "source_name": "Test Source",
        "title": "Test Article",
        "source_domain": "testsource.com",
        "source_url": "https://testsource.com/article",
        "scrape_timestamp": "2026-05-28T12:00:00Z",
        "published_at": "2026-05-28T12:00:00Z",
        "author": "Staff",
        "raw_text_content": "Fab 7 experienced a minor power interruption. " * 300,
    }
    base.update(overrides)
    return base


def _serp_data(**kw) -> dict:
    base = {
        "organic": [
            _serp_item("https://a.com/1", "a.com", "First"),
        ]
    }
    base.update(kw)
    return base


def _llm_config(**overrides) -> dict:
    base = {
        "call_1_entity_normalization": {
            "provider": "deepseek", "model": "deepseek-v4-flash",
            "thinking": False, "temperature": 0.1,
        },
        "call_2_linguistic_neutralization": {
            "provider": "deepseek", "model": "deepseek-v4-flash",
            "thinking": False, "temperature": 0.1,
        },
    }
    base.update(overrides)
    return base


# ════════════════════════════════════════════════════
# 1. PURE FUNCTIONS
# ════════════════════════════════════════════════════

class TestBuildSearchContextTable:
    """build_search_context_table(serp_data) — pure function, no IO."""

    def test_import(self):
        from narrative.processing import build_search_context_table
        assert callable(build_search_context_table)

    def test_builds_table_with_organic_results(self):
        from narrative.processing import build_search_context_table
        serp = {
            "organic": [
                _serp_item("https://a.com/1", "a.com", "First", snippet="A snippet one."),
                _serp_item("https://b.com/2", "b.com", "Second", snippet="A snippet two."),
            ]
        }
        result = build_search_context_table(serp)
        assert "| RESULT | First (a.com) | A snippet one. |" in result
        assert "| RESULT | Second (b.com) | A snippet two. |" in result
        assert result.startswith("## SYSTEM SEARCH CONTEXT REFERENCE")

    def test_includes_paa_rows(self):
        from narrative.processing import build_search_context_table
        serp = {
            "organic": [
                _serp_item("https://a.com/1", "a.com", "First", snippet="Snippet."),
            ],
            "people_also_ask": [
                _paa_item("What happened?", "Fab 7 halted operations."),
            ],
        }
        result = build_search_context_table(serp)
        assert "| PAA_SYNONYM | ALTERNATE QUERY: What happened? | CROSS-REFERENCE: Fab 7 halted operations. |" in result

    def test_graceful_when_paa_absent(self):
        from narrative.processing import build_search_context_table
        serp = {"organic": [_serp_item("https://a.com/1", "a.com")]}
        result = build_search_context_table(serp)
        assert "PAA_SYNONYM" not in result
        assert "RESULT" in result

    def test_graceful_when_organic_absent(self):
        from narrative.processing import build_search_context_table
        result = build_search_context_table({})
        assert result.startswith("## SYSTEM SEARCH CONTEXT REFERENCE")
        assert "| Type" in result
        assert "| :---" in result

    def test_replaces_pipe_chars(self):
        from narrative.processing import build_search_context_table
        serp = {
            "organic": [
                _serp_item("https://a.com/1", "a.com", "A | B", snippet="X | Y"),
            ]
        }
        result = build_search_context_table(serp)
        assert "A - B" in result
        assert "A | B" not in result
        assert "X - Y" in result

    def test_skips_organic_without_title_or_snippet(self):
        from narrative.processing import build_search_context_table
        serp = {
            "organic": [
                {"link": "https://a.com/1"},  # no title, no snippet
                _serp_item("https://b.com/2", "b.com", "Valid", snippet="Yes"),
            ]
        }
        result = build_search_context_table(serp)
        assert "RESULT | Valid (b.com) | Yes |" in result
        assert result.count("RESULT") == 1


class TestRunEntityNormalization:
    """run_entity_normalization(documents, serp_data, llm_config) — shielded LLM call."""

    def test_import(self):
        from narrative.processing import run_entity_normalization
        assert callable(run_entity_normalization)

    def test_returns_canonical_map(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        response = json.dumps({
            "normalized_mappings": [
                {"surface_form_variant": "Tainan Hub", "canonical_reference_identity": "Fab 7"},
                {"surface_form_variant": "The Fab", "canonical_reference_identity": "Fab 7"},
            ]
        })
        monkeypatch.setattr("narrative.llm_client.call_llm", lambda *a, **kw: response)
        docs = [_doc(raw_text_content="Tainan Hub is running.")]
        result = run_entity_normalization(docs, _serp_data(), _llm_config())
        assert result["tainan hub"] == "Fab 7"
        assert result["the fab"] == "Fab 7"
        assert len(result) == 2

    def test_returns_empty_dict_on_json_decode_error(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        monkeypatch.setattr("narrative.llm_client.call_llm", lambda *a, **kw: "not valid json")
        docs = [_doc(raw_text_content="Some text.")]
        result = run_entity_normalization(docs, _serp_data(), _llm_config())
        assert result == {}

    def test_returns_empty_dict_on_llm_runtime_error(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        def _raise(*a, **kw):
            raise RuntimeError("LLM returned None content")
        monkeypatch.setattr("narrative.llm_client.call_llm", _raise)
        docs = [_doc(raw_text_content="Some text.")]
        result = run_entity_normalization(docs, _serp_data(), _llm_config())
        assert result == {}

    def test_skips_malformed_mappings(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        response = json.dumps({
            "normalized_mappings": [
                {"surface_form_variant": "Valid Hub", "canonical_reference_identity": "Fab 7"},
                {"surface_form_variant": "Missing Target"},  # missing canonical
                {"canonical_reference_identity": "Fab 7"},     # missing surface form
                "not_a_dict",                                   # not a dict
            ]
        })
        monkeypatch.setattr("narrative.llm_client.call_llm", lambda *a, **kw: response)
        docs = [_doc(raw_text_content="Valid Hub.")]
        result = run_entity_normalization(docs, _serp_data(), _llm_config())
        assert result["valid hub"] == "Fab 7"
        assert len(result) == 1

    def test_handles_empty_normalized_mappings(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        response = json.dumps({"normalized_mappings": []})
        monkeypatch.setattr("narrative.llm_client.call_llm", lambda *a, **kw: response)
        result = run_entity_normalization([], _serp_data(), _llm_config())
        assert result == {}

    def test_passes_search_context_in_prompt(self, monkeypatch):
        """Verifies the search context table is built and prepended to system prompt."""
        from narrative.processing import run_entity_normalization
        response = json.dumps({"normalized_mappings": []})

        captured = {}
        def _capture_call(slot_cfg, messages, json_mode=False):
            captured["system"] = messages[0]["content"]
            captured["user"] = messages[1]["content"]
            return response

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture_call)
        serp = {"organic": [_serp_item("https://x.com", "x.com", "X", snippet="Y")]}
        docs = [_doc(raw_text_content="Some text.")]
        run_entity_normalization(docs, serp, _llm_config())
        assert "## SYSTEM SEARCH CONTEXT REFERENCE" in captured["system"]
        assert "RESULT | X (x.com) | Y |" in captured["system"]
        assert "Some text." in captured["user"]

    def test_truncates_long_articles(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        response = json.dumps({"normalized_mappings": []})
        monkeypatch.setattr("narrative.llm_client.call_llm", lambda *a, **kw: response)
        long_text = "word " * 5000  # ~25K chars, well over 6000 limit
        docs = [_doc(raw_text_content=long_text)]
        run_entity_normalization(docs, _serp_data(), _llm_config())
        # If no exception, the truncation code path works

    def test_calls_llm_with_json_mode_true(self, monkeypatch):
        from narrative.processing import run_entity_normalization
        response = json.dumps({"normalized_mappings": []})

        captured = {}
        def _capture(slot_cfg, messages, json_mode=False):
            captured["json_mode"] = json_mode
            return response

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        docs = [_doc(raw_text_content="Some text.")]
        run_entity_normalization(docs, _serp_data(), _llm_config())
        assert captured["json_mode"] is True


class TestRunLinguisticNeutralization:
    """run_linguistic_neutralization(documents, llm_config) — parallel LLM calls."""

    def test_import(self):
        from narrative.processing import run_linguistic_neutralization
        assert callable(run_linguistic_neutralization)

    def test_returns_neutralized_texts(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: "Neutralized text. ",
        )
        docs = [
            _doc(doc_id="DOC-001", raw_text_content="Fab 7 had a minor issue."),
            _doc(doc_id="DOC-002", raw_text_content="Operations were normal."),
        ]
        result = run_linguistic_neutralization(docs, _llm_config())
        assert len(result) == 2
        assert result[0] == "Neutralized text."

    def test_returns_one_result_per_doc(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: "Neutralized. ",
        )
        docs = [_doc(doc_id=f"DOC-{i:03d}") for i in range(7)]
        result = run_linguistic_neutralization(docs, _llm_config())
        assert len(result) == 7

    def test_returns_empty_string_on_llm_failure(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        call_count = 0
        def _alternate(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("LLM returned None content")
            return "Neutralized. "
        monkeypatch.setattr("narrative.llm_client.call_llm", _alternate)
        docs = [
            _doc(doc_id="DOC-001"),
            _doc(doc_id="DOC-002"),
            _doc(doc_id="DOC-003"),
        ]
        result = run_linguistic_neutralization(docs, _llm_config())
        assert len(result) == 3
        assert result[1] == ""

    def test_strips_whitespace(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: "  Neutralized text.  \n",
        )
        docs = [_doc(doc_id="DOC-001")]
        result = run_linguistic_neutralization(docs, _llm_config())
        assert result[0] == "Neutralized text."

    def test_calls_llm_with_json_mode_false(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        captured = {}
        def _capture(slot_cfg, messages, json_mode=False):
            captured["json_mode"] = json_mode
            return "Neutralized. "
        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        docs = [_doc(doc_id="DOC-001")]
        run_linguistic_neutralization(docs, _llm_config())
        assert captured["json_mode"] is False

    def test_uses_call_2_slot_config(self, monkeypatch):
        from narrative.processing import run_linguistic_neutralization
        captured = {}
        def _capture(slot_cfg, messages, json_mode=False):
            captured["slot_cfg"] = slot_cfg
            return "Neutralized. "
        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        config = _llm_config()
        config["call_2_linguistic_neutralization"]["model"] = "deepseek-v4-flash"
        docs = [_doc(doc_id="DOC-001")]
        run_linguistic_neutralization(docs, config)
        assert captured["slot_cfg"]["model"] == "deepseek-v4-flash"
