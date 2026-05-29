# Task 2 Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical and medium issues from adversarial review of `llm_client.py`, grounded in spec v1.4. Rectify one spec divergence (retry count).

**Architecture:** Each issue is a self-contained vertical slice: fix + test. Order: critical first (C1→C2→C3), then medium (M1→M2→M3→M4), then test gaps. M5 and L1-L5 are deferred as spec-compliant or cosmetic.

**Tech Stack:** Python 3.11, pytest, Pydantic (via `contracts.py`)

**Spec references below each issue explain why the fix is correct — no guesses.**

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `llm_client.py` | Modify | All implementation fixes |
| `test_llm_client.py` | Modify | New tests for each fix + gap coverage |

---

### Task H1: Fix C1 — Corrupt JSON Config Crashes Cold Start

**Spec reference:** Section 9.2 defines the config structure. Section 9.3 shows `load_llm_config()` reading and parsing. Section 10 (Failure Modes) covers parse failures for LLM calls but is silent on config file corruption. The fix: treat corrupt config like missing config — write safe defaults, log the error.

**Files:**
- Modify: `llm_client.py:54-64`

- [ ] **Step 1: Write the failing test**

```python
def test_load_llm_config_recovers_from_corrupt_json(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"
    config_path.write_text("this is not valid json {{{")

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "deepseek"
    assert config["call_3_graph_extraction"]["thinking"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py::test_load_llm_config_recovers_from_corrupt_json -v`
Expected: FAIL with `json.JSONDecodeError`

- [ ] **Step 3: Write minimal implementation**

In `load_llm_config()`, expand the `except` clause to catch `json.JSONDecodeError` (and any other read failure like `PermissionError`, `OSError`) in addition to `FileNotFoundError`. On any read failure, write defaults.

Replace lines 57-64:

```python
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(DEFAULT_LLM_CONFIG, f, indent=2)
        return dict(DEFAULT_LLM_CONFIG)
```

With:

```python
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        pass
    except json.JSONDecodeError:
        pass

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(DEFAULT_LLM_CONFIG, f, indent=2)
    return copy.deepcopy(DEFAULT_LLM_CONFIG)
```

Note: `OSError` covers `FileNotFoundError`, `PermissionError`, and other IO failures. `json.JSONDecodeError` covers corrupt content. Both trigger fallback to defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py::test_load_llm_config_recovers_from_corrupt_json -v`
Expected: PASS

- [ ] **Step 5: Also add test for PermissionError**

```python
def test_load_llm_config_recovers_from_permission_error(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"
    config_path.write_text("{}")
    os.chmod(config_path, 0o000)

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "deepseek"

    os.chmod(config_path, 0o644)
```

Run both. Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add llm_client.py test_llm_client.py
git commit -m "fix: load_llm_config recovers from corrupt JSON and IO errors (C1)"
```

---

### Task H2: Fix C2 — Validate Loaded Config Shape

**Spec reference:** Section 9.2 defines the exact 4-slot config schema. Section 9.4's `update_llm_config` validates slot names exist but not internal keys. Pydantic `LLMConfig` model in `contracts.py:207-211` already has `_Strict` base (extra=forbid) and field-level validation on `LLMSlotConfig` (temperature bounds). Use it.

**Files:**
- Modify: `llm_client.py:54-64`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_llm_config_validates_loaded_config_shape(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"

    malformed = {
        "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4o", "thinking": False, "temperature": 0.1},
    }
    config_path.write_text(json.dumps(malformed))

    with pytest.raises(Exception):
        load_llm_config()


def test_load_llm_config_validates_slot_internal_keys(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"

    bad_slot = {
        "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4o", "thinking": False, "temperature": 99.0},
        "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4o", "thinking": False, "temperature": 0.1},
        "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4o", "thinking": False, "temperature": 0.1},
        "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4o", "thinking": False, "temperature": 0.1},
    }
    config_path.write_text(json.dumps(bad_slot))

    with pytest.raises(Exception):
        load_llm_config()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "validates_loaded_config" -v`
Expected: both FAIL (load_llm_config returns dict without error)

- [ ] **Step 3: Write minimal implementation**

After loading config from file (or writing defaults), validate through Pydantic. If validation fails, write defaults (corrupt config recovery) and return defaults.

Modify `load_llm_config` to add validation after the read/write block. The function should now read:

```python
import copy

def load_llm_config() -> dict:
    """Load llm_config.json from volume. Write + return defaults on any failure."""
    path = _config_path()
    loaded = None

    try:
        with open(path) as f:
            loaded = json.load(f)
    except OSError:
        pass
    except json.JSONDecodeError:
        pass

    if loaded is not None:
        try:
            LLMConfig(**loaded)
            return loaded
        except Exception:
            pass

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(DEFAULT_LLM_CONFIG, f, indent=2)
    return copy.deepcopy(DEFAULT_LLM_CONFIG)
```

Note: `copy.deepcopy()` prevents M4 (shared mutable references). `LLMConfig(**loaded)` triggers Pydantic validation: missing slots → `ValidationError`, extra keys → `ValidationError` (from `_Strict` base), temperature out of bounds → `ValidationError`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "validates_loaded_config" -v`
Expected: both PASS

- [ ] **Step 5: Verify existing tests still pass (config lifecycle tests read valid/default configs)**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "load_llm_config" -v`
Expected: all PASS (5 tests total)

- [ ] **Step 6: Commit**

```bash
git add llm_client.py test_llm_client.py
git commit -m "fix: validate llm_config.json shape via Pydantic on load (C2, M4)"
```

---

### Task H3: Fix C3 — Clear Error for Unknown Provider

**Spec reference:** Section 9.2 lists supported providers: `"deepseek"` | `"openai"` | `"google"` | `"groq"`. An unrecognized provider means a config error, not a missing API key. Error message must name the provider and list valid options.

**Files:**
- Modify: `llm_client.py:72-92`

- [ ] **Step 1: Write the failing test**

```python
def test_get_llm_client_raises_clear_error_for_unknown_provider(monkeypatch):
    import llm_client

    llm_client._client_cache.clear()

    with pytest.raises(RuntimeError, match="Unknown provider"):
        llm_client.get_llm_client("nonexistent")

    try:
        llm_client.get_llm_client("nonexistent")
    except RuntimeError as e:
        assert "nonexistent" in str(e)
        assert "deepseek" in str(e) or "openai" in str(e)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py::test_get_llm_client_raises_clear_error_for_unknown_provider -v`
Expected: FAIL (raises RuntimeError with blank env var name, not "Unknown provider")

- [ ] **Step 3: Write minimal implementation**

Add provider validation before API key check in `get_llm_client`:

```python
def get_llm_client(provider: str) -> OpenAI:
    """Return an OpenAI-compatible client for a provider. Thread-safe, cached per provider."""
    if provider not in PROVIDER_API_KEY_ENV:
        raise RuntimeError(
            f"Unknown provider '{provider}'. "
            f"Supported: {', '.join(PROVIDER_API_KEY_ENV.keys())}"
        )

    if provider in _client_cache:
        return _client_cache[provider]

    with _client_cache_lock:
        if provider in _client_cache:
            return _client_cache[provider]

        api_key_env = PROVIDER_API_KEY_ENV[provider]
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"No API key for provider '{provider}'. "
                f"Set the {api_key_env} environment variable."
            )
        base_url = PROVIDER_BASE_URLS[provider]

        client = OpenAI(api_key=api_key, base_url=base_url)
        _client_cache[provider] = client
        return client
```

Key changes:
1. Provider validation first — `PROVIDER_API_KEY_ENV` key check with clear error listing valid providers
2. After validation, `PROVIDER_API_KEY_ENV[provider]` always returns a string (no `.get()`)
3. `PROVIDER_BASE_URLS[provider]` always returns a string (no `.get()` with default)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py::test_get_llm_client_raises_clear_error_for_unknown_provider -v`
Expected: PASS

- [ ] **Step 5: Remove the old weak test (test_get_llm_client_raises_for_unknown_provider at line 361)**

Replace the old test with the new one — the old test only checks that RuntimeError is raised, not the message quality.

- [ ] **Step 6: Verify all get_llm_client tests pass**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "get_llm_client" -v`
Expected: all PASS (5 tests)

- [ ] **Step 7: Commit**

```bash
git add llm_client.py test_llm_client.py
git commit -m "fix: clear error message for unknown provider in get_llm_client (C3)"
```

---

### Task H4: Fix M1 — Retries Must Match Spec (1 Retry = 2 Total)

**Spec reference:** Section 10 (Failure Modes) states explicitly: "Wrap all LLM calls in try/catch with **one retry**. On second failure, mark document as PARSE_ERROR and exclude from corpus." The hardening bump to `retries=2` (3 total) diverges from spec.

**Also fix:** Config errors (`KeyError`, `RuntimeError` from missing API key) should never be retried. They cannot resolve on retry.

**Files:**
- Modify: `llm_client.py:112-157`

- [ ] **Step 1: Revert retries default to 1 (spec-compliant)**

```python
def call_llm(slot_config: dict, messages: list[dict],
             json_mode: bool = True, retries: int = 1) -> str:
```

- [ ] **Step 2: Add non-retriable error discrimination**

Create a set of error types that should NOT be retried:

```python
# Errors that will never resolve on retry — fail fast
_NON_RETRIABLE = (RuntimeError, KeyError, TypeError, AttributeError, ValueError)
```

Modify the retry loop to skip retry for these:

```python
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("LLM returned None content")
            if json_mode:
                json.loads(content)
            return content
        except _NON_RETRIABLE:
            raise
        except BaseException as e:
            if not isinstance(e, Exception):
                raise
            last_error = e
            if attempt < retries:
                continue
            raise

    raise last_error  # type: ignore[misc]
```

Note: `_NON_RETRIABLE` catches `RuntimeError` (None content, missing API key, unknown provider), `KeyError` (missing model/provider key in config), `TypeError`, `AttributeError`, `ValueError`. These all indicate config/code bugs that retries don't fix. API errors (`openai.APIError` and subclasses) remain retriable.

`JSONDecodeError` IS a subclass of `ValueError`, so it would be caught by `_NON_RETRIABLE`. But JSON decode errors from LLMs ARE transient — the model might produce valid JSON on retry. Need to handle this:

```python
        except json.JSONDecodeError:
            last_error = e
            if attempt < retries:
                continue
            raise
        except _NON_RETRIABLE:
            raise
```

Insert the `json.JSONDecodeError` catch BEFORE `_NON_RETRIABLE`.

- [ ] **Step 3: Update tests for retry count**

Update `test_call_llm_retries_2_gives_3_total_attempts` → rename to `test_call_llm_retries_1_gives_2_total_attempts` and change `retries=1`, expect 2 attempts:

```python
def test_call_llm_retries_1_gives_2_total_attempts(monkeypatch):
    from llm_client import call_llm

    mock_client = _setup_mock_client_for_call_llm(
        monkeypatch,
        [
            Exception("fail 1"),
            _mock_chat_response('{"ok": 2}'),
        ],
    )

    result = call_llm(_slot_config_payload(), _messages_payload(), retries=1)
    assert result == '{"ok": 2}'
    assert mock_client.chat.completions.create.call_count == 2
```

Update `test_call_llm_raises_after_exhausting_retries` to use `retries=1`, 2 attempts:

```python
def test_call_llm_raises_after_exhausting_retries(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(
        monkeypatch,
        [
            Exception("fail 1"),
            Exception("fail 2"),
        ],
    )

    with pytest.raises(Exception, match="fail 2"):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)
```

Update `test_call_llm_retries_then_fails_on_invalid_json` to use `retries=1`, 2 attempts:

```python
def test_call_llm_retries_then_fails_on_invalid_json(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(
        monkeypatch,
        [
            _mock_chat_response("not json attempt 1"),
            _mock_chat_response("not json attempt 2"),
        ],
    )

    with pytest.raises(json.JSONDecodeError):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)
```

Delete `test_call_llm_retries_on_api_errors` (duplicate of `test_call_llm_retries_1_gives_2_total_attempts`).

- [ ] **Step 4: Add tests for non-retriable errors**

```python
def test_call_llm_fails_fast_on_key_error(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(monkeypatch, KeyError("model"))

    with pytest.raises(KeyError, match="model"):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)


def test_call_llm_fails_fast_on_missing_api_key(monkeypatch):
    from llm_client import call_llm

    def raise_runtime(*args, **kwargs):
        raise RuntimeError("No API key for provider 'deepseek'")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = raise_runtime
    monkeypatch.setattr("llm_client.get_llm_client", lambda p: mock_client)

    with pytest.raises(RuntimeError, match="No API key"):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)

    assert mock_client.chat.completions.create.call_count == 1
```

- [ ] **Step 5: Add SystemExit passthrough test (T3 from review)**

```python
def test_call_llm_reraises_system_exit(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(monkeypatch, SystemExit(1))

    with pytest.raises(SystemExit):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)
```

- [ ] **Step 6: Verify all call_llm tests pass**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "call_llm" -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add llm_client.py test_llm_client.py
git commit -m "fix: spec-compliant retry count (1), non-retriable error fast-fail, SystemExit test (M1, T3, T10)"
```

---

### Task H5: Fix M2 + M3 — Defensive Access in build_llm_kwargs + Embedding Error Handling

**Spec reference for M2:** Section 9.3 defines `slot_config` access pattern: `slot_config["model"]`, `slot_config["provider"]`. With C2 fix (config validation at load), these keys are guaranteed. But defensive access is cheap insurance against edge cases (e.g., malformed slot from a future code path). Use `.get()` with sentinel defaults.

**Spec reference for M3:** Section 5.2 names `text-embedding-3-small`. Section 5.2 shows `get_embedding` called per-doc in `compute_framing_volatility`. No spec-defined retry for embeddings. Add one retry + clear error message.

**Files:**
- Modify: `llm_client.py:97-109, 185-190`

- [ ] **Step 1: Write defensive access in build_llm_kwargs**

```python
def build_llm_kwargs(slot_config: dict, messages: list[dict],
                     json_mode: bool = True) -> dict:
    """Build kwargs dict for a chat.completions.create call from slot config."""
    model = slot_config.get("model")
    if not model:
        raise KeyError("slot_config missing required key: 'model'")
    provider = slot_config.get("provider", "")
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": slot_config.get("temperature", 0.1),
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if slot_config.get("thinking") and provider == "deepseek":
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    return kwargs
```

Note: `provider` default `""` — the `== "deepseek"` check on line 107 now safely works even if key is missing (won't match, no extra_body). `model` still raises `KeyError` with a clear message if missing — caught by `_NON_RETRIABLE` in `call_llm` (H4 fix).

- [ ] **Step 2: Add test for missing model key in build_llm_kwargs**

```python
def test_build_llm_kwargs_raises_on_missing_model():
    from llm_client import build_llm_kwargs

    slot: dict = {"provider": "deepseek", "thinking": False}
    with pytest.raises(KeyError, match="model"):
        build_llm_kwargs(slot, _messages_payload())
```

- [ ] **Step 3: Add retry + error handling to get_embedding**

```python
def get_embedding(text: str, retries: int = 1) -> list[float]:
    """Generate embedding vector via OpenAI text-embedding-3-small."""
    client = get_llm_client("openai")
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = client.embeddings.create(model=model, input=text)
            return response.data[0].embedding
        except BaseException as e:
            if not isinstance(e, Exception):
                raise
            last_error = e
            if attempt < retries:
                continue
            raise RuntimeError(
                f"Embedding call failed after {retries + 1} attempts. "
                f"Model: {model}. Text length: {len(text)} chars."
            ) from last_error

    raise last_error  # type: ignore[misc]
```

- [ ] **Step 4: Add test for embedding failure**

```python
def test_get_embedding_raises_after_failure(monkeypatch):
    from llm_client import get_embedding

    import llm_client
    llm_client._client_cache.clear()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = [
        Exception("API error 1"),
        Exception("API error 2"),
    ]
    monkeypatch.setattr(llm_client, "get_llm_client", lambda p: mock_client)

    with pytest.raises(RuntimeError, match="Embedding call failed"):
        get_embedding("test text", retries=1)

    assert mock_client.embeddings.create.call_count == 2
```

- [ ] **Step 5: Run all new tests**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "build_llm_kwargs_raises_on_missing_model or get_embedding_raises_after_failure" -v`
Expected: both PASS

- [ ] **Step 6: Verify existing tests still pass**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -k "build_llm_kwargs or get_embedding" -v`
Expected: all PASS (11 tests)

- [ ] **Step 7: Commit**

```bash
git add llm_client.py test_llm_client.py
git commit -m "fix: defensive access in build_llm_kwargs, embedding retry + error context (M2, M3)"
```

---

### Task H6: Fix T4 — Verify Success Path Doesn't Retry Silently

**Files:**
- Modify: `test_llm_client.py:396-404`

- [ ] **Step 1: Add call count assertion to success test**

```python
def test_call_llm_returns_content_on_success(monkeypatch):
    from llm_client import call_llm

    mock_client = _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response('{"key": "value"}')
    )

    result = call_llm(_slot_config_payload(), _messages_payload())
    assert result == '{"key": "value"}'
    assert mock_client.chat.completions.create.call_count == 1
```

- [ ] **Step 2: Run test**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py::test_call_llm_returns_content_on_success -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add test_llm_client.py
git commit -m "test: verify call_llm success path makes exactly 1 API call (T4)"
```

---

### Task H7: Fix T9 — Add Autouse Fixture to Clean _client_cache

**Files:**
- Modify: `test_llm_client.py` (top-level fixture)

- [ ] **Step 1: Add autouse fixture**

At the top of the test file, after imports, add:

```python
import llm_client


@pytest.fixture(autouse=True)
def _clear_client_cache():
    llm_client._client_cache.clear()
    yield
    llm_client._client_cache.clear()
```

- [ ] **Step 2: Remove manual `llm_client._client_cache.clear()` calls from individual tests**

Grep for all `llm_client._client_cache.clear()` in the test file and remove them. The autouse fixture handles this.

- [ ] **Step 3: Run all tests to verify no cache leakage**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -v`
Expected: all PASS (existing 38 + new ones from H1-H5)

- [ ] **Step 4: Commit**

```bash
git add test_llm_client.py
git commit -m "test: autouse fixture to clean _client_cache between tests (T9)"
```

---

### Task H8: Add Tests for Remaining Gaps (T1, T6, T7, T8)

One commit covering 4 small test additions already written in prior tasks (noted here for completeness):

| Gap | Covered by | Status |
|---|---|---|
| T1: Corrupt JSON | Task H1, test_load_llm_config_recovers_from_corrupt_json | Added |
| T6: Embedding error | Task H5, test_get_embedding_raises_after_failure | Added |
| T7: PermissionError | Task H1, test_load_llm_config_recovers_from_permission_error | Added |
| T8: Full config validation | Task H2, test_load_llm_config_validates_* | Added |
| T3: SystemExit | Task H4, test_call_llm_reraises_system_exit | Added |
| T10: Duplicate retry test | Task H4, deleted test_call_llm_retries_on_api_errors | Resolved |

- [ ] **Step 1: Run full suite**

Run: `PYTHONPATH=/tmp/pytest_pkgs python3 -m pytest test_llm_client.py -v`
Expected: all PASS (estimate 44 tests after additions)

- [ ] **Step 2: Commit**

```bash
git add test_llm_client.py
git commit -m "test: full coverage for Task 2 gaps (T1, T3, T6, T7, T8)"
```

---

### Task H9: Update Plan Document — Sync Retry Count

**Files:**
- Modify: `docs/superpowers/plans/2026-05-29-narrative-alpha-full.md` (Task 2 section)

- [ ] **Step 1: Update plan code blocks**

In the plan's Task 2 section, update:
1. `retries: int = 2` → `retries: int = 1` (in call_llm signature)
2. `retries: max retry attempts (default 2 → 3 total attempts)` → `retries: max retry attempts (default 1 → 2 total attempts)`
3. Hardening table H2 row: update to say `retries default: 1 (2 total)` and rationale updated to note spec Section 10 compliance

- [ ] **Step 2: Add non-retriable error hardening note**

Add H7 to the hardening table:
| H7 | Non-retriable error fast-fail | Config errors (KeyError, RuntimeError, ValueError) never retried. JSONDecodeError retried (transient LLM output). |

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-05-29-narrative-alpha-full.md
git commit -m "docs: sync plan Task 2 with spec-compliant retry count + non-retriable hardening"
```

---

## Deferred (No Code Changes)

| # | Reason |
|---|---|
| M5 (double json.loads) | Spec-compliant: call_llm validates parseability; callers parse separately per Sections 6 Call 1-4 |
| L1 (trailing slashes) | URLs match spec Section 9.2 table exactly |
| L2 (reasoning_content "") | Not in spec — helper function for future multi-turn use |
| L3 (getattr default) | Same as L2 |
| L4 (thread safety read) | Double-checked locking is correct under CPython GIL |
| L5 (_config_path DRY) | Cross-module concern — address when reputation.py is written (Task 4) |

---

## Execution Order

1. H1 (C1 fix) → H2 (C2 fix) → H3 (C3 fix) — critical path
2. H4 (M1 fix + spec realignment) — depends on H3 (non-retriable errors use provider validation)
3. H5 (M2 + M3 fix) — independent
4. H6 (T4 fix) → H7 (T9 fix) — independent test cleanups
5. H8 (remaining test gaps) — depends on all prior
6. H9 (plan update) — last, after all fixes confirmed

**Run full test suite after each task. Expected final: ~44 passing tests.**
