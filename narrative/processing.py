"""Layer 2: Processing — entity normalization and linguistic neutralization.

Vf (framing volatility) computation is Layer 3 concern — see analysis.py.
"""

import json


# ── Constants ──

ARTICLE_CHAR_LIMIT = 6000


# ── Search Context Reference Table (Section 14.2C) ──

def build_search_context_table(serp_data: dict) -> str:
    """
    Build a markdown table from SERP response for Call 1 prompt injection.
    Extracts titles, snippets, and People Also Ask (PAA) data.
    Gracefully degrades if PAA key absent.
    """
    lines = ["## SYSTEM SEARCH CONTEXT REFERENCE\n"]
    lines.append("| Type | Content Source / Query Variant | Contextual Text Snippet |")
    lines.append("| :--- | :--- | :--- |")

    for item in serp_data.get("organic", []):
        title = item.get("title", "").replace("|", "-")
        domain = item.get("display_link", "")
        snippet = item.get("snippet", "").replace("|", "-")
        if title and snippet:
            lines.append(f"| RESULT | {title} ({domain}) | {snippet} |")

    for paa in serp_data.get("people_also_ask", []):
        question = paa.get("question", "").replace("|", "-")
        answer = paa.get("answer", "").replace("|", "-")
        if question and answer:
            lines.append(
                f"| PAA_SYNONYM | ALTERNATE QUERY: {question} | CROSS-REFERENCE: {answer} |"
            )

    return "\n".join(lines)


# ── Call 1: Entity Normalization (Fast LLM, non-thinking) ──

ENTITY_NORMALIZATION_SYSTEM_PROMPT = (
    "You are an entity normalization engine. Given a set of raw article text fragments, "
    "identify all named entities and map every surface-form variant to a single canonical "
    "reference identity. Output only valid JSON matching the schema provided. "
    "Do not include preamble, explanation, or markdown fences."
)


def run_entity_normalization(
    documents: list[dict],
    serp_data: dict,
    llm_config: dict,
) -> dict[str, str]:
    """
    Resolve naming variants across articles to canonical identities.

    Returns: canonical_map = {lowercased_surface_form: canonical_reference_identity}
    Returns empty dict if LLM returns unparseable JSON — pipeline continues degraded.

    Uses search context table from SERP data to seed the prompt with
    Google's pre-computed synonym resolution.
    """
    from narrative.llm_client import call_llm

    search_context = build_search_context_table(serp_data)

    article_texts = "\n\n---\n\n".join(
        f"[{doc['source_domain']}] {doc['title']}: {doc['raw_text_content'][:ARTICLE_CHAR_LIMIT]}"
        for doc in documents
    )

    system_prompt = (
        f"{search_context}\n\n---\n\n{ENTITY_NORMALIZATION_SYSTEM_PROMPT}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": article_texts},
    ]

    slot_cfg = llm_config["call_1_entity_normalization"]

    try:
        raw = call_llm(slot_cfg, messages, json_mode=True)
        data = json.loads(raw)
    except (json.JSONDecodeError, RuntimeError):
        return {}

    mappings = data.get("normalized_mappings", [])
    if not isinstance(mappings, list):
        return {}

    canonical_map: dict[str, str] = {}
    for m in mappings:
        try:
            key = m["surface_form_variant"].strip().lower()
            canonical_map[key] = m["canonical_reference_identity"]
        except (KeyError, TypeError):
            continue

    return canonical_map


# ── Call 2: Linguistic Neutralization (Fast LLM, non-thinking) ──

LINGUISTIC_NEUTRALIZATION_SYSTEM_PROMPT = (
    "You are a linguistic neutralization engine. Transform the input text into a flat, "
    "clinical sequence of declarative active-verb statements. Strip all qualifying "
    "adjectives, descriptive idioms, adverbial padding, and corporate designations. "
    "Preserve only: named entities, actions, timestamps, quantities, and locations. "
    "Output plain text only. No JSON. No markdown."
)


def run_linguistic_neutralization(
    documents: list[dict],
    llm_config: dict,
) -> list[str]:
    """
    Strip emotional framing, adjectives, euphemisms from each article.
    Uses ThreadPoolExecutor for parallel LLM calls (max 5 concurrent).
    Returns list of neutralized text strings (one per doc).
    Failed articles return empty string — filtered downstream.
    """
    from concurrent.futures import ThreadPoolExecutor
    from narrative.llm_client import call_llm

    slot_cfg = llm_config["call_2_linguistic_neutralization"]

    def _neutralize_one(doc: dict) -> str:
        messages = [
            {"role": "system", "content": LINGUISTIC_NEUTRALIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": doc["raw_text_content"]},
        ]
        try:
            return call_llm(slot_cfg, messages, json_mode=False).strip()
        except RuntimeError:
            return ""

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_neutralize_one, documents))

    return results
