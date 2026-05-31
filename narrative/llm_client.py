"""Runtime LLM provider configuration and client factory."""

import copy
import json
import os
import threading
from typing import Optional

from openai import OpenAI

from narrative.contracts import LLMConfig, LLMSlotConfig


# ── Provider resolution maps ──

PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com",
    "openai":   "https://api.openai.com/v1",
    "google":   "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq":     "https://api.groq.com/openai/v1",
}

PROVIDER_API_KEY_ENV: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai":   "OPENAI_API_KEY",
    "google":   "GOOGLE_API_KEY",
    "groq":     "GROQ_API_KEY",
}

# ── Default in-code config (written to volume on first run if file missing) ──

DEFAULT_LLM_CONFIG = LLMConfig(
    call_1_entity_normalization=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-flash", thinking=False, temperature=0.1
    ),
    call_2_linguistic_neutralization=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-flash", thinking=False, temperature=0.1
    ),
    call_3_graph_extraction=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-flash", thinking=False, temperature=0.1
    ),
    call_4_forensic_synthesis=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-pro", thinking=True, temperature=0.1
    ),
).model_dump()


# ── Config lifecycle ──

def _config_path() -> str:
    root = os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha")
    return os.path.join(root, "llm_config.json")


def load_llm_config() -> dict:
    """Load llm_config.json from volume. Write + return defaults on any failure."""
    path = _config_path()
    try:
        with open(path) as f:
            loaded = json.load(f)
        LLMConfig(**loaded)
        return loaded
    except OSError:
        pass
    except json.JSONDecodeError:
        pass
    except Exception:
        pass

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(DEFAULT_LLM_CONFIG, f, indent=2)
    except OSError:
        pass
    return copy.deepcopy(DEFAULT_LLM_CONFIG)


# ── Client factory (thread-safe — H1) ──

_client_cache: dict[str, OpenAI] = {}
_client_cache_lock = threading.Lock()

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


# ── Call executor ──

# Errors that cannot resolve on retry — fail immediately
_NON_RETRIABLE = (RuntimeError, KeyError, TypeError, AttributeError)


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


def call_llm(slot_config: dict, messages: list[dict],
             json_mode: bool = True, retries: int = 1) -> str:
    """
    Execute a single LLM call. Returns response content as string.

    Args:
        slot_config: e.g. llm_config["call_1_entity_normalization"]
        messages: chat messages list
        json_mode: if True, request JSON response format and validate parse
        retries: max retry attempts (default 1 → 2 total attempts, per spec Section 10)

    Returns:
        response.choices[0].message.content as a string.

    Raises:
        RuntimeError: if LLM returns None content (empty response)
        BaseException: re-raised immediately (KeyboardInterrupt, CancelledError, etc.)

    Note: All current calls are single-turn. If multi-turn history is ever needed,
    use extract_assistant_message() to append the assistant turn — do NOT reconstruct
    the dict manually. DeepSeek returns reasoning_content on thinking-mode responses
    and will reject the next request with a 400 if it is missing from the history.
    """
    provider = slot_config["provider"]
    client = get_llm_client(provider)
    kwargs = build_llm_kwargs(slot_config, messages, json_mode)

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
        except json.JSONDecodeError as e:                               # retry — transient LLM output
            last_error = e
            if attempt < retries:
                continue
            raise
        except _NON_RETRIABLE:                                     # config / code bug — never retry
            raise
        except BaseException as e:                                 # network / API errors
            if not isinstance(e, Exception):
                raise
            last_error = e
            if attempt < retries:
                continue
            raise

    raise last_error  # type: ignore[misc]


# ── DeepSeek multi-turn helper ──

def extract_assistant_message(response_message) -> dict:
    """
    Build a correctly-shaped assistant message dict from a DeepSeek response object
    for appending to messages history in multi-turn calls.

    DeepSeek's API rejects multi-turn requests with a 400 error if reasoning_content
    is present in the previous assistant turn but not echoed back in the messages list.
    Using the SDK object (not a manually reconstructed dict) is the safe approach.

    Usage:
        response = client.chat.completions.create(...)
        messages.append(extract_assistant_message(response.choices[0].message))
        # then add next user turn and call again
    """
    msg: dict = {"role": "assistant", "content": response_message.content}
    reasoning = getattr(response_message, "reasoning_content", None)
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    return msg


# ── Standalone embedding call (not slot-configured — fixed to OpenAI) ──

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
