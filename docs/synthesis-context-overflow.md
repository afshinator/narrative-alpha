# Synthesis Context Overflow — Analysis & Solutions

## Problem

The forensic synthesis step (LLM call 4/4) sends a `context_bundle` as the user message
to DeepSeek V4 Pro. This bundle includes the full `raw_text` and `neutralized_text` for
every article with **zero truncation**. When combined across 8+ articles of long-form news
content, the total token count can exceed the model's context window:

- **Model:** DeepSeek V4 Pro, `thinking=True`
- **Context limit:** 1,048,565 tokens
- **Observed failure:** 1,138,805 tokens requested (90,240 over)

The error:
```
This model's maximum context length is 1048565 tokens. However, you requested
1138805 tokens (1138805 in the messages, 0 in the completion).
```

The entity normalization step (`processing.py`) already applies a hard truncation
(`ARTICLE_CHAR_LIMIT = 6000` chars), but the synthesis step was sending full-length
texts with no limit.

## Current Fix

**Applied in `pipeline.py`:**

```python
SYNTHESIS_TEXT_CHAR_LIMIT = 5000  # chars per text
```

Applied to both `raw_text` and `neutralized_text` in the `per_source` entries:

```python
"raw_text": (raw_texts[i][:SYNTHESIS_TEXT_CHAR_LIMIT] if i < len(raw_texts) else ""),
"neutralized_text": (neutralized[i][:SYNTHESIS_TEXT_CHAR_LIMIT] if i < len(neutralized) else ""),
```

### Why it works

- 5000 chars ≈ 1250 tokens per text
- Per article: ~2500 tokens for both texts
- Worst case (20 articles): ~50,000 tokens for all texts
- Rest of payload: ~20,000–30,000 tokens
- Total: ~80,000 tokens, well under the 1M limit

### What it gets wrong

Head-only truncation biases toward the lede. News articles often bury their framing
language in the middle or conclusion — the opening paragraphs are typically the most
neutral. The LLM may miss the most telling instances of linguistic camouflage.

---

## Better Approaches

### 1. Remove both texts entirely

The synthesis LLM already receives structured data that encodes the full analysis:

- **Graphs** (nodes + edges) — extracted from neutralized text
- **Omission indices** — computed via set subtraction against consensus
- **Framing volatility scores** — computed via embedding distance
- **Narrative clusters** — topic → claim → outlet mappings
- **Fracture candidates** — contradictory claims with supporting outlets
- **Reputation records** — historical scatter-shot and validation rates

The raw/neutralized text only serves one purpose in the prompt: populating
`linguistic_camouflage` entries like `"minor power interruption" → "grid line severance"`.
The LLM can fabricate plausible examples from the graph and omission context, but they
would be synthesized, not extracted.

**Pros:** Zero text bloat. Safest against overflow. Simple to implement — drop two keys
from `per_source`.

**Cons:** The camouflage examples lose grounding in actual article text. Might produce
hallucinated quotes. Harder to verify correctness of the output.

**Implementation sketch:**
```python
# In pipeline.py, per_source construction — simply remove raw_text and neutralized_text
"per_source": [
    {
        "domain": g.get("_source_domain", ""),
        "name": g.get("_source_name", ""),
        "graph": g,
        "omission_index": ...,
        # ... no raw_text or neutralized_text
    }
    ...
]
```

---

### 2. Inject short excerpts instead of full texts

Instead of shipping full articles, pre-extract ~500 chars per article of the most
heavily-loaded sentences — high adjective density, euphemisms, corporate spin, hedging
language. This gives the LLM real material for camouflage detection at a fraction of
the text cost.

This requires a preprocessing step that scans each article for spin-loaded sentences.
Heuristics could include:
- Adjective-to-token ratio above a threshold
- Presence of known spin/camouflage keywords
- Sentences that changed most between raw and neutralized text (using text diff)

**Pros:** Preserves authentic camouflage detection. Tiny footprint (~10% of current fix).
Provides defensible, quotable examples.

**Cons:** Requires implementing the spin-detection heuristic. Adds a preprocessing pass
before synthesis. Heuristic may miss subtle camouflage or flag false positives.

**Implementation sketch:**
```python
# New utility in analysis.py or a separate module
def extract_camouflage_excerpts(raw_text: str, neutralized_text: str, max_chars: int = 500) -> str:
    """
    Extract sentences from raw_text where the most linguistic spin is concentrated.
    Uses diff-based approach: compare raw vs neutralized, score each raw sentence
    by edit-distance ratio, return highest-scoring sentences up to max_chars.
    """
    # Split into sentences
    raw_sentences = sent_tokenize(raw_text)
    neut_sentences = sent_tokenize(neutralized_text)
    # Score each raw sentence by how much it differs from its counterpart
    scored = []
    for rs, ns in zip(raw_sentences, neut_sentences):
        ratio = len(ndiff(rs, ns)) / max(len(rs), 1)  # approximate
        scored.append((ratio, rs))
    scored.sort(reverse=True)
    # Return top sentences up to limit
    result = []
    total = 0
    for _, sent in scored:
        if total + len(sent) > max_chars:
            break
        result.append(sent)
        total += len(sent)
    return " ".join(result)
```

---

### 3. Head + tail truncation

Instead of taking the first N chars, take first ~1K chars (lede context) + last ~3K chars
(editorial framing). This covers both the factual setup in the opening and the
spin-heavy analysis in the conclusion, while dropping the middle filler.

**Pros:** More informative than head-only. Still simple to implement. Catches the most
common locations of framing language.

**Cons:** More code than simple head truncation. Could miss spin that runs throughout
the full article (a common pattern in opinion pieces). Mid-article detail is lost.

**Implementation sketch:**
```python
def synthesis_truncate(text: str, head: int = 1000, tail: int = 3000) -> str:
    """Keep first `head` chars + last `tail` chars of text."""
    if len(text) <= head + tail:
        return text
    return text[:head] + "\n[...]\n" + text[-tail:]
```

---

### 4. Remove indent from JSON serialization

In `synthesize_forensic_report()` (`analysis.py`):

```python
user_content = json.dumps(context_bundle, indent=2, default=str)
```

Using `indent=2` adds ~40% whitespace overhead to the serialized payload. Switching to
`indent=None` produces a compact single-line JSON, reducing tokens for free.

**Pros:** Zero trade-offs. Trivial change. No functionality impact. Compound savings —
reduces not just text tokens but also the serialized size of graphs, clusters, fractures,
and metadata.

**Cons:** Makes the serialized payload unreadable in logs. (Mitigation: log separately
with indent for debugging.)

**Implementation sketch:**
```python
# Before
user_content = json.dumps(context_bundle, indent=2, default=str)
# After
user_content = json.dumps(context_bundle, default=str)
```

---

### 5. Combined approach

Apply approaches 1–4 together for maximum safety margin:

1. Remove `raw_text` and `neutralized_text` from `per_source`
2. Inject short spin-loaded excerpts per article (optional — only if camouflage
   detection quality matters)
3. Remove `indent=2` from JSON serialization
4. (Optional) Cap `fracture_candidates` to prevent O(n²) explosion on high-edge topics

This drops the serialized payload from ~1.1M tokens to well under 100K even with
20 articles.

---

## Appendix: Payload Size Breakdown

Estimated token counts for each component at 20 articles (worst case):

| Component | Raw Size (chars) | Est. Tokens |
|-----------|------------------|-------------|
| System prompt | ~1,500 | ~400 |
| Consensus nodes | ~500 | ~125 |
| `per_source` (no texts) | ~20,000 | ~5,000 |
| `raw_text` (full, 20× 5K chars) | ~100,000 | ~25,000 |
| `neutralized_text` (full, 20× 5K chars) | ~100,000 | ~25,000 |
| Fracture candidates | ~10,000 | ~2,500 |
| Narrative clusters | ~5,000 | ~1,250 |
| Reputation records | ~5,000 | ~1,250 |
| Term shifts | ~2,000 | ~500 |
| JSON overhead (indent=2) | +40% on all above | ~25,000 |
| **Total with texts + indent** | **~344,000** | **~86,000** |
| **Total without texts, no indent** | **~44,000** | **~11,000** |

The DeepSeek V4 Pro limit is 1,048,565 tokens. Even the worst-case is only ~8% of the limit.
The observed failure (1,138,805 tokens) suggests some article texts were much longer than
5000 chars — likely 15–20K chars per article from long-form sources.

## Index

- `narrative/pipeline.py` — SYNTHESIS_TEXT_CHAR_LIMIT, per_source construction
- `narrative/analysis.py` — `synthesize_forensic_report()` (json.dumps call)
- `narrative/processing.py` — `ARTICLE_CHAR_LIMIT` (precedent for truncation)
