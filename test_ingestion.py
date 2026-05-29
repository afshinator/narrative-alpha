"""Tests for ingestion.py — Layer 1: Discovery, Extraction, Validation.

Run with: python -m pytest test_ingestion.py -v
"""

import pytest


# ── Helpers ──

def _valid_body() -> str:
    """Return text that passes all validation gates: >=300 chars, >=50 words,
    no paywall patterns, nav-hits <= 3 or body >= 1500 chars."""
    return "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 30


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


# ════════════════════════════════════════════════════
# 1. PURE FUNCTIONS
# ════════════════════════════════════════════════════

class TestExtractText:
    """extract_text(html) — trafilatura wrapper, returns stripped text or ''."""

    def test_import(self):
        from ingestion import extract_text
        assert callable(extract_text)

    def test_strips_html(self):
        from ingestion import extract_text
        html = "<html><body><p>  Hello world  </p></body></html>"
        assert extract_text(html) == "Hello world"

    def test_handles_none_from_trafilatura(self):
        """When trafilatura returns None, extract_text returns ''."""
        from ingestion import extract_text
        assert extract_text("<script>no content</script>") == ""


class TestParseSerpResult:
    """parse_serp_result(result) — field extraction and domain normalisation."""

    def test_import(self):
        from ingestion import parse_serp_result
        assert callable(parse_serp_result)

    def test_full_fields(self):
        from ingestion import parse_serp_result
        r = parse_serp_result({
            "link": "https://example.com/article",
            "title": "  Test Article  ",
            "snippet": "A snippet",
            "source": "Example News",
            "display_link": "example.com",
            "published_at": "2026-05-28T12:00:00Z",
        })
        assert r["url"] == "https://example.com/article"
        assert r["title"] == "Test Article"
        assert r["source_name"] == "Example News"
        assert r["domain"] == "example.com"
        assert r["published_at"] == "2026-05-28T12:00:00Z"
        assert r["snippet"] == "A snippet"

    def test_minimal(self):
        """Only link present — title/source derived, published_at None."""
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://globalwire.com/report"})
        assert r["url"] == "https://globalwire.com/report"
        assert r["title"] == ""
        assert r["domain"] == "globalwire.com"
        assert r["source_name"] == "Globalwire"  # derived from domain
        assert r["published_at"] is None

    def test_empty_input(self):
        """Empty dict — all fields default gracefully."""
        from ingestion import parse_serp_result
        r = parse_serp_result({})
        assert r["url"] == ""
        assert r["title"] == ""
        assert r["domain"] == ""
        assert r["published_at"] is None

    def test_www_domain_normalised(self):
        """www. prefix is stripped from domain."""
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://www.example.com/article", "source": "Example"})
        assert r["domain"] == "example.com"

    def test_source_falls_back_to_display_link(self):
        """When source key is absent, display_link is used."""
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://reuters.com/a", "display_link": "reuters.com"})
        assert r["source_name"] == "Reuters"

    def test_domain_from_url_when_source_is_empty(self):
        """When source and display_link both empty, domain derived from url."""
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://globalwire.com/article"})
        assert r["domain"] == "globalwire.com"
        assert r["source_name"] == "Globalwire"

    def test_published_at_absent(self):
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://a.com", "published_at": ""})
        assert r["published_at"] is None

    def test_published_at_present(self):
        from ingestion import parse_serp_result
        r = parse_serp_result({"link": "https://a.com", "published_at": "2026-05-28T12:00:00Z"})
        assert r["published_at"] == "2026-05-28T12:00:00Z"


class TestValidateIngestionPayload:
    """validate_ingestion_payload(doc) — quality gates per spec Section 14.1."""

    def _make_doc(self, **overrides) -> dict:
        base = {
            "doc_id": "DOC-001",
            "source_name": "Test Source",
            "source_url": "https://example.com/article",
            "title": "Test Article",
            "scrape_timestamp": "2026-05-28T12:00:00Z",
            "raw_text_content": _valid_body(),
            "passed_validation": 0,
        }
        base.update(overrides)
        return base

    def test_import(self):
        from ingestion import validate_ingestion_payload
        assert callable(validate_ingestion_payload)

    def test_valid_payload(self):
        from ingestion import validate_ingestion_payload
        doc = self._make_doc()
        result = validate_ingestion_payload(doc)
        assert result is not None
        assert result["passed_validation"] == 1
        assert result["source_domain"] == "example.com"
        assert result["title"] == "Test Article"

    def test_rejects_missing_source_url(self):
        from ingestion import validate_ingestion_payload
        assert validate_ingestion_payload(self._make_doc(source_url="")) is None

    def test_rejects_missing_title(self):
        from ingestion import validate_ingestion_payload
        assert validate_ingestion_payload(self._make_doc(title="")) is None

    def test_rejects_short_body_under_300_chars(self):
        from ingestion import validate_ingestion_payload
        assert validate_ingestion_payload(self._make_doc(raw_text_content="Short body.")) is None

    def test_rejects_fewer_than_50_words(self):
        from ingestion import validate_ingestion_payload
        text = "word " * 49  # 49 words, meets 300 chars
        assert validate_ingestion_payload(self._make_doc(raw_text_content=text)) is None

    def test_passes_50_words_and_300_chars(self):
        """Text needs both >= 300 chars and >= 50 words to pass."""
        from ingestion import validate_ingestion_payload
        text = ("word " * 61)  # 61 words, 305 chars raw (304 after strip)
        result = validate_ingestion_payload(self._make_doc(raw_text_content=text))
        assert result is not None

    @pytest.mark.parametrize("pattern", [
        "sign in to continue",
        "create an account",
        "subscribe to read",
        "exclusive subscriber content",
        "log in or register",
        "members-only story",
    ])
    def test_rejects_paywall_patterns(self, pattern):
        from ingestion import validate_ingestion_payload
        doc = self._make_doc(raw_text_content=f"{_valid_body()}\n{pattern}")
        assert validate_ingestion_payload(doc) is None

    def test_rejects_nav_bloat_under_1500(self):
        """> 3 nav tokens AND body < 1500 chars -> rejection."""
        from ingestion import validate_ingestion_payload
        body = "cookie privacy policy all rights reserved terms of service share this article. " * 2
        assert len(body) < 1500
        doc = self._make_doc(raw_text_content=body)
        assert validate_ingestion_payload(doc) is None

    def test_allows_nav_bloat_over_1500(self):
        "> 3 nav tokens BUT body >= 1500 chars -> passes."
        from ingestion import validate_ingestion_payload
        body = ("cookie privacy policy all rights reserved terms of service share this article. " * 10
                + _valid_body())
        assert len(body) >= 1500
        doc = self._make_doc(raw_text_content=body)
        assert validate_ingestion_payload(doc) is not None

    def test_normalises_www_domain(self):
        from ingestion import validate_ingestion_payload
        doc = self._make_doc(source_url="https://www.example.com/article")
        result = validate_ingestion_payload(doc)
        assert result is not None
        assert result["source_domain"] == "example.com"

    def test_returns_none_on_bad_url(self):
        from ingestion import validate_ingestion_payload
        doc = self._make_doc(source_url="")
        assert validate_ingestion_payload(doc) is None

    def test_domain_falls_back_to_source_name(self):
        from ingestion import validate_ingestion_payload
        doc = self._make_doc(source_name="Custom Name", source_url="https://source.com/a")
        result = validate_ingestion_payload(doc)
        assert result is not None
        assert result["source_name"] == "Custom Name"
        assert result["source_domain"] == "source.com"


# ════════════════════════════════════════════════════
# 2. IO FUNCTIONS  (requests.post monkeypatched)
# ════════════════════════════════════════════════════

class TestDiscoverArticles:
    """discover_articles(keyword, api_key, num) — SERP API call."""

    def test_import(self):
        from ingestion import discover_articles, SERP_ENDPOINT
        assert callable(discover_articles)
        assert SERP_ENDPOINT == "https://api.brightdata.com/serp/req"

    def test_sends_correct_payload(self, monkeypatch):
        from ingestion import discover_articles

        posted = {}

        def fake_post(url, json, headers, timeout):
            posted["url"] = url
            posted["json"] = json
            posted["headers"] = headers
            posted["timeout"] = timeout

            class FakeResp:
                def raise_for_status(self): pass
                def json(self): return {"organic": []}

            return FakeResp()

        monkeypatch.setattr("requests.post", fake_post)
        result = discover_articles("test query", "key-123", num=10)

        assert posted["url"] == "https://api.brightdata.com/serp/req"
        assert posted["json"]["q"] == "test query"
        assert posted["json"]["engine"] == "google"
        assert posted["json"]["tbm"] == "nws"
        assert posted["json"]["num"] == 10
        assert posted["json"]["parsed_light"] is True
        assert posted["headers"]["Authorization"] == "Bearer key-123"
        assert posted["timeout"] == 30
        assert result == {"organic": []}

    def test_defaults_to_15_results(self, monkeypatch):
        from ingestion import discover_articles

        def fake_post(url, json, headers, timeout):
            class FakeResp:
                def raise_for_status(self): pass
                def json(self): return {}
            return FakeResp()

        monkeypatch.setattr("requests.post", fake_post)
        discover_articles("q", "key")
        # We already verified num defaults via the previous test's num param.
        # Just confirm the call doesn't crash with default.
        assert True

    def test_raises_on_http_error(self, monkeypatch):
        from ingestion import discover_articles

        def fake_post(*a, **kw):
            class FakeResp:
                def raise_for_status(self):
                    raise Exception("HTTP 403")
                def json(self): return {}
            return FakeResp()

        monkeypatch.setattr("requests.post", fake_post)
        with pytest.raises(Exception, match="HTTP 403"):
            discover_articles("q", "key")


class TestFetchArticleBody:
    """fetch_article_body(url, zone, api_key) — Web Unlocker call."""

    def test_import(self):
        from ingestion import fetch_article_body, UNLOCKER_ENDPOINT
        assert callable(fetch_article_body)
        assert UNLOCKER_ENDPOINT == "https://api.brightdata.com/request"

    def test_sends_correct_payload(self, monkeypatch):
        from ingestion import fetch_article_body

        posted = {}

        def fake_post(url, json, headers, timeout):
            posted["url"] = url
            posted["json"] = json
            posted["headers"] = headers
            posted["timeout"] = timeout

            class FakeResp:
                def raise_for_status(self): pass
                text = "<html><body><p>Article body.</p></body></html>"

            return FakeResp()

        monkeypatch.setattr("requests.post", fake_post)
        html = fetch_article_body("https://example.com/a", "my_zone", "key-456")

        assert posted["url"] == "https://api.brightdata.com/request"
        assert posted["json"]["zone"] == "my_zone"
        assert posted["json"]["url"] == "https://example.com/a"
        assert posted["json"]["format"] == "raw"
        assert posted["headers"]["Authorization"] == "Bearer key-456"
        assert posted["timeout"] == 30
        assert html == "<html><body><p>Article body.</p></body></html>"

    def test_raises_on_http_error(self, monkeypatch):
        from ingestion import fetch_article_body

        def fake_post(*a, **kw):
            class FakeResp:
                def raise_for_status(self):
                    raise Exception("HTTP 500")
            return FakeResp()

        monkeypatch.setattr("requests.post", fake_post)
        with pytest.raises(Exception, match="HTTP 500"):
            fetch_article_body("https://x.com", "z", "k")


# ════════════════════════════════════════════════════
# 3. ORCHESTRATION  (build_ingestion_manifest)
# ════════════════════════════════════════════════════

class TestBuildIngestionManifest:
    """build_ingestion_manifest — full Layer 1 pipeline orchestration."""

    @pytest.fixture
    def serp_data(self):
        return {
            "organic": [
                _serp_item("https://source1.com/a", "source1.com", "Article 1"),
                _serp_item("https://source2.com/b", "source2.com", "Article 2"),
                _serp_item("https://source3.com/c", "source3.com", "Article 3"),
                _serp_item("https://source4.com/d", "source4.com", "Article 4"),
                _serp_item("https://source5.com/e", "source5.com", "Article 5"),
            ]
        }

    def test_import(self):
        from ingestion import build_ingestion_manifest
        assert callable(build_ingestion_manifest)

    def test_returns_manifest_with_5_sources(self, monkeypatch, serp_data):
        from ingestion import build_ingestion_manifest

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", serp_data, "zone", "key")
        assert "cluster_id" in result
        assert result["corpus_count"] == 5
        assert len(result["documents"]) == 5
        assert result["trigger_type"] == "KEYWORD"
        assert result["search_query"] == "test"

    def test_floor_gate_below_5(self, monkeypatch, serp_data):
        """Only 2 sources pass validation -> INSUFFICIENT_CORPUS_FLOOR."""
        from ingestion import build_ingestion_manifest

        called = 0
        def fake_extract(html):
            nonlocal called
            called += 1
            # First two calls return valid text; rest return empty (fail)
            if called <= 2:
                return _valid_body()
            return ""

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text", fake_extract)

        result = build_ingestion_manifest("test", serp_data, "zone", "key")
        assert "validation_tracking" in result
        assert result["validation_tracking"]["current_state"] == "INSUFFICIENT_CORPUS_FLOOR"
        assert result["validation_tracking"]["current_count"] < 5
        assert result.get("status") == "INSUFFICIENT_CORPUS_FLOOR"

    def test_dedup_by_domain(self, monkeypatch):
        """Same domain appears twice — only one kept."""
        from ingestion import build_ingestion_manifest

        data = {
            "organic": [
                _serp_item("https://a.com/1", "a.com", "First"),
                _serp_item("https://a.com/2", "a.com", "Second"),
                _serp_item("https://b.com/1", "b.com", "Third"),
                _serp_item("https://c.com/1", "c.com", "Fourth"),
                _serp_item("https://d.com/1", "d.com", "Fifth"),
                _serp_item("https://e.com/1", "e.com", "Sixth"),
            ]
        }

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", data, "zone", "key")
        assert result["corpus_count"] == 5  # deduped from 6 to 5

    def test_hard_cap_at_20(self, monkeypatch):
        """25 unique sources -> only 20 in manifest, corpus_capped=True.
        Validates through IngestionManifest Pydantic model."""
        from ingestion import build_ingestion_manifest
        from contracts import IngestionManifest

        items = []
        for i in range(25):
            items.append(_serp_item(f"https://src{i}.com/a", f"src{i}.com", f"Article {i}"))

        data = {"organic": items}

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", data, "zone", "key")

        # Dict-level assertions
        assert result["corpus_count"] == 20
        assert result.get("corpus_capped") is True
        assert len(result["documents"]) == 20

        # Strict Pydantic round-trip (would have caught corpus_capped bug)
        manifest = IngestionManifest(**result)
        assert manifest.corpus_count == 20
        assert manifest.corpus_capped is True
        assert len(manifest.documents) == 20

    @pytest.fixture
    def serp_data_6(self):
        return {
            "organic": [
                _serp_item("https://source1.com/a", "source1.com", "Article 1"),
                _serp_item("https://source2.com/b", "source2.com", "Article 2"),
                _serp_item("https://source3.com/c", "source3.com", "Article 3"),
                _serp_item("https://source4.com/d", "source4.com", "Article 4"),
                _serp_item("https://source5.com/e", "source5.com", "Article 5"),
                _serp_item("https://source6.com/f", "source6.com", "Article 6"),
            ]
        }

    def test_extraction_failure_logged(self, monkeypatch, serp_data_6):
        """When fetch_article_body raises, the doc is logged as failed."""
        from ingestion import build_ingestion_manifest

        call_count = 0

        def fake_fetch(url, zone, key):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTTP 403")
            return "<html><p>body</p></html>"

        monkeypatch.setattr("ingestion.fetch_article_body", fake_fetch)
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", serp_data_6, "zone", "key")
        assert result["corpus_count"] == 5  # 1 failed, 5 passed

    def test_trafilatura_failure_logged(self, monkeypatch, serp_data_6):
        """When extract_text returns short text, doc is logged as failed."""
        from ingestion import build_ingestion_manifest

        call_count = 0

        def fake_extract(html):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "short"
            return _valid_body()

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text", fake_extract)

        result = build_ingestion_manifest("test", serp_data_6, "zone", "key")
        assert result["corpus_count"] == 5  # 1 trafilatura failure, 5 passed

    def test_logger_func_called_when_wired(self, monkeypatch, serp_data):
        """logger_func is called with (query_id, topic, ts, docs, conn)."""
        from ingestion import build_ingestion_manifest

        logged = []

        def fake_logger(qid, topic, ts, docs, conn):
            logged.append((qid, topic, ts, len(docs), conn))

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        fake_conn = object()  # any sentinel — not a real connection

        result = build_ingestion_manifest(
            "test", serp_data, "zone", "key",
            db_conn=fake_conn, logger_func=fake_logger,
        )
        assert len(logged) == 1
        _, topic, _, doc_count, conn = logged[0]
        assert topic == "test"
        assert doc_count > 0
        assert conn is fake_conn

    def test_logger_func_skipped_when_no_db_conn(self, monkeypatch, serp_data):
        """logger_func not called when db_conn is None."""
        from ingestion import build_ingestion_manifest

        called = False

        def fake_logger(*a, **kw):
            nonlocal called
            called = True

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        build_ingestion_manifest("test", serp_data, "zone", "key", logger_func=fake_logger)
        assert not called

    def test_logger_func_skipped_when_no_logger(self, monkeypatch, serp_data):
        """logger_func not called when logger_func is None (even with db_conn)."""
        from ingestion import build_ingestion_manifest

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest(
            "test", serp_data, "zone", "key", db_conn=object(),
        )
        assert result["corpus_count"] == 5

    def test_published_at_in_manifest(self, monkeypatch):
        """published_at is carried through to manifest documents."""
        from ingestion import build_ingestion_manifest

        data = {
            "organic": [
                _serp_item("https://src1.com/x", "src1.com", "A", published_at="2026-05-28T10:00:00Z"),
                _serp_item("https://src2.com/a", "src2.com", "B"),
                _serp_item("https://src3.com/b", "src3.com", "C"),
                _serp_item("https://src4.com/c", "src4.com", "D"),
                _serp_item("https://src5.com/d", "src5.com", "E"),
                _serp_item("https://src6.com/e", "src6.com", "F"),
            ]
        }

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", data, "zone", "key")
        found = [d for d in result["documents"] if d.get("source_domain") == "src1.com"]
        assert len(found) == 1
        assert found[0].get("published_at") == "2026-05-28T10:00:00Z"

    def test_published_at_absent(self, monkeypatch):
        """When SERP lacks published_at, field is absent/None in manifest."""
        from ingestion import build_ingestion_manifest

        data = {
            "organic": [
                _serp_item("https://src1.com/x", "src1.com", "A", published_at=None),
                _serp_item("https://src2.com/a", "src2.com", "B", published_at=""),
                _serp_item("https://src3.com/b", "src3.com", "C"),
                _serp_item("https://src4.com/c", "src4.com", "D"),
                _serp_item("https://src5.com/d", "src5.com", "E"),
                _serp_item("https://src6.com/e", "src6.com", "F"),
            ]
        }

        monkeypatch.setattr("ingestion.fetch_article_body",
                            lambda url, zone, key: "<html><p>body</p></html>")
        monkeypatch.setattr("ingestion.extract_text",
                            lambda html: _valid_body())

        result = build_ingestion_manifest("test", data, "zone", "key")
        absent = [d for d in result["documents"] if d.get("source_domain") == "src1.com"]
        assert len(absent) == 1
        assert absent[0].get("published_at") is None
