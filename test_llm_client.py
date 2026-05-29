"""Tests for llm_client.py — LLM client factory, config loader, and call executor.

Run with: python -m pytest test_llm_client.py -v
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ── Autouse fixture: prevent _client_cache leakage between tests ──

@pytest.fixture(autouse=True)
def _clear_client_cache():
    import llm_client
    llm_client._client_cache.clear()
    yield
    llm_client._client_cache.clear()


# ── Helpers: minimal valid payloads ──

def _slot_config_payload(**overrides):
    base = {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "thinking": False,
        "temperature": 0.1,
    }
    base.update(overrides)
    return base


def _messages_payload():
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize this."},
    ]


def _mock_chat_response(content):
    """Create a mock chat completion whose .choices[0].message.content is the given value."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response.choices = [mock_choice]
    return mock_response


def _mock_embedding_response(embedding):
    mock_response = MagicMock()
    mock_data = MagicMock()
    mock_data.embedding = embedding
    mock_response.data = [mock_data]
    return mock_response


# ── Pure function: build_llm_kwargs ──

def test_build_llm_kwargs_includes_model_and_messages():
    from llm_client import build_llm_kwargs

    slot = _slot_config_payload(model="gpt-4o")
    msgs = _messages_payload()
    kwargs = build_llm_kwargs(slot, msgs)

    assert kwargs["model"] == "gpt-4o"
    assert kwargs["messages"] is msgs


def test_build_llm_kwargs_json_mode_adds_response_format():
    from llm_client import build_llm_kwargs

    kwargs = build_llm_kwargs(_slot_config_payload(), _messages_payload(), json_mode=True)
    assert kwargs["response_format"] == {"type": "json_object"}


def test_build_llm_kwargs_json_mode_false_omits_response_format():
    from llm_client import build_llm_kwargs

    kwargs = build_llm_kwargs(_slot_config_payload(), _messages_payload(), json_mode=False)
    assert "response_format" not in kwargs


def test_build_llm_kwargs_thinking_deepseek_adds_extra_body():
    from llm_client import build_llm_kwargs

    slot = _slot_config_payload(provider="deepseek", thinking=True)
    kwargs = build_llm_kwargs(slot, _messages_payload())

    assert "extra_body" in kwargs
    assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


def test_build_llm_kwargs_thinking_other_provider_omits_extra_body():
    from llm_client import build_llm_kwargs

    for provider in ("openai", "google", "groq"):
        slot = _slot_config_payload(provider=provider, thinking=True)
        kwargs = build_llm_kwargs(slot, _messages_payload())
        assert "extra_body" not in kwargs, f"extra_body should be absent for {provider}"


def test_build_llm_kwargs_temperature_defaults_to_0_1():
    from llm_client import build_llm_kwargs

    slot: dict = {"provider": "openai", "model": "gpt-4o"}
    kwargs = build_llm_kwargs(slot, _messages_payload())
    assert kwargs["temperature"] == 0.1


def test_build_llm_kwargs_temperature_uses_provided_value():
    from llm_client import build_llm_kwargs

    slot = _slot_config_payload(temperature=0.7)
    kwargs = build_llm_kwargs(slot, _messages_payload())
    assert kwargs["temperature"] == 0.7


def test_build_llm_kwargs_thinking_false_deepseek_omits_extra_body():
    from llm_client import build_llm_kwargs

    slot = _slot_config_payload(provider="deepseek", thinking=False)
    kwargs = build_llm_kwargs(slot, _messages_payload())
    assert "extra_body" not in kwargs


def test_build_llm_kwargs_thinking_missing_deepseek_omits_extra_body():
    from llm_client import build_llm_kwargs

    slot: dict = {"provider": "deepseek", "model": "deepseek-v4-flash"}
    kwargs = build_llm_kwargs(slot, _messages_payload())
    assert "extra_body" not in kwargs


def test_build_llm_kwargs_raises_on_missing_model():
    from llm_client import build_llm_kwargs

    slot: dict = {"provider": "deepseek", "thinking": False}
    with pytest.raises(KeyError, match="model"):
        build_llm_kwargs(slot, _messages_payload())


# ── Pure function: extract_assistant_message ──

def test_extract_assistant_message_returns_role_and_content():
    from llm_client import extract_assistant_message

    class SimpleMessage:
        content = "Response text."

    result = extract_assistant_message(SimpleMessage())
    assert result["role"] == "assistant"
    assert result["content"] == "Response text."


def test_extract_assistant_message_includes_reasoning_when_present():
    from llm_client import extract_assistant_message

    class ReasoningMessage:
        content = "Final answer."
        reasoning_content = "Step-by-step reasoning..."

    result = extract_assistant_message(ReasoningMessage())
    assert result["reasoning_content"] == "Step-by-step reasoning..."


def test_extract_assistant_message_omits_reasoning_when_absent():
    from llm_client import extract_assistant_message

    class PlainMessage:
        content = "Final answer."

    result = extract_assistant_message(PlainMessage())
    assert "reasoning_content" not in result
    assert result["content"] == "Final answer."


def test_extract_assistant_message_reasoning_none_omitted():
    from llm_client import extract_assistant_message

    class NoneReasoningMessage:
        content = "Final answer."
        reasoning_content = None

    result = extract_assistant_message(NoneReasoningMessage())
    assert "reasoning_content" not in result


def test_extract_assistant_message_reasoning_empty_string_included():
    from llm_client import extract_assistant_message

    class EmptyReasoningMessage:
        content = "Final answer."
        reasoning_content = ""

    result = extract_assistant_message(EmptyReasoningMessage())
    assert result["reasoning_content"] == ""


# ── IO function: load_llm_config ──

def test_load_llm_config_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))

    config = load_llm_config()

    assert config["call_1_entity_normalization"]["provider"] == "deepseek"
    assert config["call_1_entity_normalization"]["model"] == "deepseek-v4-flash"
    assert config["call_2_linguistic_neutralization"]["provider"] == "deepseek"
    assert config["call_3_graph_extraction"]["provider"] == "deepseek"
    assert config["call_4_forensic_synthesis"]["provider"] == "deepseek"


def test_load_llm_config_creates_config_file(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))

    load_llm_config()

    config_path = tmp_path / "llm_config.json"
    assert config_path.exists()
    with open(config_path) as f:
        data = json.load(f)
    assert data["call_1_entity_normalization"]["provider"] == "deepseek"


def test_load_llm_config_reads_existing_file_correctly(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))

    custom_config = {
        "call_1_entity_normalization": {
            "provider": "openai",
            "model": "gpt-4o",
            "thinking": False,
            "temperature": 0.2,
        },
        "call_2_linguistic_neutralization": {
            "provider": "openai",
            "model": "gpt-4o",
            "thinking": False,
            "temperature": 0.2,
        },
        "call_3_graph_extraction": {
            "provider": "openai",
            "model": "gpt-4o",
            "thinking": False,
            "temperature": 0.2,
        },
        "call_4_forensic_synthesis": {
            "provider": "openai",
            "model": "gpt-4o",
            "thinking": False,
            "temperature": 0.2,
        },
    }
    config_path = tmp_path / "llm_config.json"
    config_path.write_text(json.dumps(custom_config))

    config = load_llm_config()

    assert config["call_1_entity_normalization"]["provider"] == "openai"
    assert config["call_1_entity_normalization"]["model"] == "gpt-4o"
    assert config["call_1_entity_normalization"]["temperature"] == 0.2


def test_load_llm_config_respects_custom_root(tmp_path, monkeypatch):
    from llm_client import load_llm_config

    other_root = tmp_path / "custom_location"
    os.makedirs(other_root, exist_ok=True)

    custom_config = {
        "call_1_entity_normalization": {
            "provider": "groq",
            "model": "llama",
            "thinking": False,
            "temperature": 0.5,
        },
        "call_2_linguistic_neutralization": {
            "provider": "groq",
            "model": "llama",
            "thinking": False,
            "temperature": 0.5,
        },
        "call_3_graph_extraction": {
            "provider": "groq",
            "model": "llama",
            "thinking": False,
            "temperature": 0.5,
        },
        "call_4_forensic_synthesis": {
            "provider": "groq",
            "model": "llama",
            "thinking": False,
            "temperature": 0.5,
        },
    }
    config_path = other_root / "llm_config.json"
    config_path.write_text(json.dumps(custom_config))

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(other_root))

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "groq"


def test_load_llm_config_recovers_from_corrupt_json(tmp_path, monkeypatch):
    """load_llm_config must not crash on corrupt JSON — return defaults instead."""
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"
    config_path.write_text("this is not valid json {{{")

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "deepseek"
    assert config["call_3_graph_extraction"]["thinking"] is True


def test_load_llm_config_recovers_from_unreadable_file(tmp_path, monkeypatch):
    """load_llm_config must return defaults when file exists but cannot be read."""
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"
    config_path.write_text("{}")
    config_path.chmod(0o000)

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "deepseek"

    config_path.chmod(0o644)


def test_load_llm_config_recovers_from_missing_slots(tmp_path, monkeypatch):
    """Config with missing required slots → fall back to defaults."""
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"

    malformed = {
        "call_1_entity_normalization": {
            "provider": "openai", "model": "gpt-4o",
            "thinking": False, "temperature": 0.1,
        },
    }
    config_path.write_text(json.dumps(malformed))

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["provider"] == "deepseek"
    assert config["call_3_graph_extraction"]["thinking"] is True


def test_load_llm_config_recovers_from_bad_temperature(tmp_path, monkeypatch):
    """Config with out-of-range temperature → fall back to defaults."""
    from llm_client import load_llm_config

    monkeypatch.setenv("NARRATIVE_ALPHA_ROOT", str(tmp_path))
    config_path = tmp_path / "llm_config.json"

    bad_temp = {
        "call_1_entity_normalization": {
            "provider": "openai", "model": "gpt-4o",
            "thinking": False, "temperature": 99.0,
        },
        "call_2_linguistic_neutralization": {
            "provider": "openai", "model": "gpt-4o",
            "thinking": False, "temperature": 0.1,
        },
        "call_3_graph_extraction": {
            "provider": "openai", "model": "gpt-4o",
            "thinking": False, "temperature": 0.1,
        },
        "call_4_forensic_synthesis": {
            "provider": "openai", "model": "gpt-4o",
            "thinking": False, "temperature": 0.1,
        },
    }
    config_path.write_text(json.dumps(bad_temp))

    config = load_llm_config()
    assert config["call_1_entity_normalization"]["temperature"] == 0.1


# ── IO function: get_llm_client ──

def test_get_llm_client_raises_when_api_key_missing(monkeypatch):
    import llm_client

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        llm_client.get_llm_client("deepseek")


def test_get_llm_client_returns_cached_client_on_second_call(monkeypatch):
    import llm_client

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")

    client1 = llm_client.get_llm_client("deepseek")
    client2 = llm_client.get_llm_client("deepseek")

    assert client1 is client2


def test_get_llm_client_creates_client_with_correct_params(monkeypatch):
    from unittest.mock import patch

    import llm_client

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")

    with patch("llm_client.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        result = llm_client.get_llm_client("deepseek")

        mock_openai_cls.assert_called_once_with(
            api_key="sk-test-deepseek",
            base_url="https://api.deepseek.com",
        )
        assert result is mock_client


def test_get_llm_client_uses_provider_specific_base_url(monkeypatch):
    from unittest.mock import patch

    import llm_client

    monkeypatch.setenv("GROQ_API_KEY", "sk-test-groq")

    with patch("llm_client.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value = MagicMock()

        llm_client.get_llm_client("groq")

        mock_openai_cls.assert_called_once_with(
            api_key="sk-test-groq",
            base_url="https://api.groq.com/openai/v1",
        )


def test_get_llm_client_raises_clear_error_for_unknown_provider(monkeypatch):
    """Unknown provider must produce error listing valid options, not blank env var."""
    import llm_client


    with pytest.raises(RuntimeError, match="Unknown provider"):
        llm_client.get_llm_client("nonexistent")

    try:
        llm_client.get_llm_client("nonexistent")
    except RuntimeError as e:
        msg = str(e)
        assert "nonexistent" in msg
        assert "deepseek" in msg
        assert "openai" in msg


# ── Behavior: call_llm (mocked OpenAI) ──

def _setup_mock_client_for_call_llm(monkeypatch, side_effect_or_return):
    """Wire a mock OpenAI client into get_llm_client.

    If *side_effect_or_return* is a list, it is used as the side_effect of
    ``chat.completions.create`` (each element returned on successive calls).
    If it is an Exception (or BaseException), it is used as the side_effect
    so that calling .create() raises it.
    Otherwise it is set as .create()'s return_value.
    """
    import llm_client

    mock_client = MagicMock()
    if isinstance(side_effect_or_return, list):
        mock_client.chat.completions.create.side_effect = side_effect_or_return
    elif isinstance(side_effect_or_return, BaseException):
        mock_client.chat.completions.create.side_effect = side_effect_or_return
    else:
        mock_client.chat.completions.create.return_value = side_effect_or_return

    monkeypatch.setattr(llm_client, "get_llm_client", lambda p: mock_client)
    return mock_client


def test_call_llm_returns_content_on_success(monkeypatch):
    from llm_client import call_llm

    mock_client = _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response('{"key": "value"}')
    )

    result = call_llm(_slot_config_payload(), _messages_payload())
    assert result == '{"key": "value"}'
    assert mock_client.chat.completions.create.call_count == 1


def test_call_llm_fails_fast_on_key_error(monkeypatch):
    """Config errors must not be retried — they can never fix themselves."""
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(monkeypatch, KeyError("model"))

    with pytest.raises(KeyError, match="model"):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)


def test_call_llm_fails_fast_on_missing_api_key(monkeypatch):
    """RuntimeError from missing API key must not be retried."""
    from llm_client import call_llm

    def raise_runtime(*args, **kwargs):
        raise RuntimeError("No API key for provider 'deepseek'")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = raise_runtime
    monkeypatch.setattr("llm_client.get_llm_client", lambda p: mock_client)

    with pytest.raises(RuntimeError, match="No API key"):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)

    assert mock_client.chat.completions.create.call_count == 1


def test_call_llm_reraises_system_exit(monkeypatch):
    """SystemExit (BaseException non-Exception) must pass through immediately."""
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(monkeypatch, SystemExit(1))

    with pytest.raises(SystemExit):
        call_llm(_slot_config_payload(), _messages_payload(), retries=1)


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


def test_call_llm_retries_0_gives_1_attempt(monkeypatch):
    from llm_client import call_llm

    mock_client = _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response('{"ok": 1}')
    )

    result = call_llm(_slot_config_payload(), _messages_payload(), retries=0)
    assert result == '{"ok": 1}'
    assert mock_client.chat.completions.create.call_count == 1


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


def test_call_llm_raises_on_none_content(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response(None)
    )

    with pytest.raises(RuntimeError, match="None content"):
        call_llm(
            _slot_config_payload(), _messages_payload(), json_mode=False, retries=0
        )


def test_call_llm_reraises_keyboard_interrupt(monkeypatch):
    from llm_client import call_llm

    _setup_mock_client_for_call_llm(
        monkeypatch, KeyboardInterrupt()
    )

    with pytest.raises(KeyboardInterrupt):
        call_llm(_slot_config_payload(), _messages_payload(), retries=2)


def test_call_llm_reraises_cancelled_error(monkeypatch):
    from llm_client import call_llm

    try:
        from asyncio import CancelledError
    except ImportError:
        from concurrent.futures import CancelledError

    _setup_mock_client_for_call_llm(monkeypatch, CancelledError())

    with pytest.raises(CancelledError):
        call_llm(_slot_config_payload(), _messages_payload(), retries=2)


def test_call_llm_validates_json_in_json_mode(monkeypatch):
    from llm_client import call_llm

    valid_json = '{"entities": [{"name": "OpenAI", "type": "ORG"}]}'
    _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response(valid_json)
    )

    result = call_llm(
        _slot_config_payload(), _messages_payload(), json_mode=True, retries=0
    )
    assert result == valid_json


def test_call_llm_raises_on_invalid_json_in_json_mode(monkeypatch):
    from llm_client import call_llm

    invalid_json = "Not a JSON response at all."
    _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response(invalid_json)
    )

    with pytest.raises(json.JSONDecodeError):
        call_llm(
            _slot_config_payload(), _messages_payload(), json_mode=True, retries=0
        )


def test_call_llm_skips_json_validation_in_non_json_mode(monkeypatch):
    from llm_client import call_llm

    non_json_content = "Here is a plain text response."
    _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response(non_json_content)
    )

    result = call_llm(
        _slot_config_payload(), _messages_payload(), json_mode=False, retries=0
    )
    assert result == non_json_content


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


def test_call_llm_passes_built_kwargs_to_chat_completions(monkeypatch):
    from llm_client import call_llm

    msg = _messages_payload()
    slot = _slot_config_payload(provider="deepseek", thinking=True, temperature=0.3)

    mock_client = _setup_mock_client_for_call_llm(
        monkeypatch, _mock_chat_response('{"ok": true}')
    )

    call_llm(slot, msg, json_mode=True, retries=0)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-v4-flash"
    assert call_kwargs["messages"] is msg
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


# ── Behavior: get_embedding ──

def test_get_embedding_returns_embedding_vector(monkeypatch):
    from llm_client import get_embedding

    import llm_client

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-embedding")

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _mock_embedding_response(
        [0.1, 0.2, 0.3, 0.4]
    )
    monkeypatch.setattr(llm_client, "get_llm_client", lambda p: mock_client)

    result = get_embedding("test text")
    assert result == [0.1, 0.2, 0.3, 0.4]
    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input="test text"
    )


def test_get_embedding_uses_env_model_override(monkeypatch):
    from llm_client import get_embedding

    import llm_client

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-embedding")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "custom-embedder")

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = _mock_embedding_response([0.5])
    monkeypatch.setattr(llm_client, "get_llm_client", lambda p: mock_client)

    get_embedding("test")

    mock_client.embeddings.create.assert_called_once_with(
        model="custom-embedder", input="test"
    )


def test_get_embedding_raises_after_failure(monkeypatch):
    from llm_client import get_embedding

    import llm_client

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
