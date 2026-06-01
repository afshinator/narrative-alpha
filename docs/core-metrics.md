# Core Metrics

Narrative Alpha produces four metrics that work together to quantify how each news outlet
deviated from the institutional consensus. Three are per-outlet scores; one is the
cross-source baseline they're all measured against.

---

## 1. Consensus Baseline (Gc)

**Source:** `narrative/analysis.py` → `compute_consensus_baseline()`

**What it is:** A set of anchor entities and events that appear in more than 60% of
outlets' knowledge graphs. This is the mathematical foundation — not a score displayed
in the UI, but the substrate everything else is calculated from.

**Formula (simplified):**

```
For each unique entity/event node across all outlet graphs:
  Count how many distinct outlets include it in their graph
  If count ≥ (0.60 × valid_outlet_count) + 1 → it's a consensus node
```

**Floor gate:** Fewer than 5 valid graphs returns an empty set (consensus is meaningless
with too few sources). The pipeline degrades gracefully with `INSUFFICIENT_CONSENSUS`.

**Configurable:** The `consensus_ratio` parameter defaults to 0.60. Lower = looser
consensus (more nodes pass through). Higher = stricter (fewer nodes, higher bar).

**Where it appears in the UI:**

| UI element | Location | How it's shown |
|---|---|---|
| `verified_anchor_nodes` | Zone 1 | Rendered as pills (e.g. "Fab 7", "Operations Halted") |
| `consensus_summary` | Zone 1 | Prose paragraph summarizing the consensus narrative |
| `primary_verifications` | Zone 1 | Checkmark badges for authoritative sources that back the consensus |

There is no "Gc = 0.83" number shown — the baseline is *implicitly* represented by the
anchor nodes and summary text.

---

## 2. Omission Index (Oi)

**Source:** `narrative/analysis.py` → `compute_omission_index()`, `omission_label()`

**What it measures:** Of everything the consensus agrees happened, what fraction did
*this specific outlet* leave out? Pure set subtraction — no LLM judgment involved.

**Formula:**

```
Oi = |consensus_nodes - outlet_nodes| / |consensus_nodes|
```

**Labels:**

| Range | Label |
|-------|-------|
| < 0.25 | LOW | 
| < 0.50 | MED |
| ≥ 0.50 | HIGH |

Where interpretation: 0.00 = outlet included everything the consensus agreed on. 0.65 =
outlet omitted 65% of what everyone else covered.

**Where it appears in the UI:** Zone 2 — *Media Distortion Matrix* table, column
"Omission (Oi)". Each cell shows the value and a color-coded badge.

---

## 3. Framing Volatility (Vf)

**Source:** `narrative/analysis.py` → `compute_framing_volatility()`,
`framing_volatility_label()`

**What it measures:** How much linguistic spin did this outlet apply? Instead of
dictionary-based keyword matching, it works adversarially:

1. **Neutralization pass** — LLM strips adjectives, emotional framing, euphemisms from
   the article, reducing it to flat declarative statements.
2. **Distance calculation** — Both the raw and neutralized texts are embedded via
   OpenAI `text-embedding-3-small`. Cosine distance between the two vectors is the
   Framing Volatility score.

**Formula:**

```
raw_embedding  = embed(article_raw_text)
neut_embedding = embed(article_neutralized_text)
cos_sim        = dot(raw_embedding, neut_embedding) / (|raw| × |neut|)
Vf             = 1 - cos_sim
```

**Labels:**

| Range | Label |
|-------|-------|
| < 0.25 | LOW |
| < 0.55 | MED |
| ≥ 0.55 | HIGH |

Where interpretation: 0.00 = article used no spin (raw = neutralized). 0.78 = heavy
linguistic camouflage.

**Where it appears in the UI:** Zone 2 — *Media Distortion Matrix* table, column
"Volatility (Vf)". Each cell shows the value and a color-coded badge.

---

## 4. Scatter-Shot Anomaly (Sa)

**Source:** `narrative/analysis.py` → `compute_sa_for_outlet()`, `scatter_shot_label()`

**What it measures:** Does this outlet pump out high volumes of speculative claims,
hoping some stick? Tracks every outlier claim an outlet has historically generated and
checks whether each was eventually absorbed by the consensus or decayed into noise.

**Formula:**

```
Sa = decayed_outlier_nodes / total_outlier_nodes_produced
```

**Labels:**

| Range | Label |
|-------|-------|
| < 0.35 | LOW |
| < 0.60 | MED |
| ≥ 0.60 | HIGH |

Where interpretation: 0.21 = outlet generates few false alarms. 0.72 = outlet fires
off many unsubstantiated claims, most of which never get validated.

**Unlike Oi and Vf**, Sa comes from the **outlet reputation database** (SQLite), not the
current pipeline run. It accumulates across runs — the more you use the system, the more
reliable Sa becomes.

**Where it appears in the UI:** Zone 3 — inside **Reputation Warning** cards. Each card
shows:

| Field | Display |
|---|---|
| `scatter_shot_anomaly_factor` | Percentage (e.g. "72%") |
| `scatter_shot_label` | Color-coded badge (LOW / MED / HIGH) |
| `historical_origin_validation_rate` | Percentage of outlier claims that *were* eventually validated |

> **⚠️ Visibility note:** Reputation warning cards only render when
> `warning_triggered === true`. If no outlet in the current report has a bad enough
> reputation to trigger a warning, the entire Zone 3 reputation section is empty and
> Sa values are hidden.

Sa is also carried on individual `outlier_signals` (per-claim provenance), shown in the
signal cards just below the reputation warnings.

---

## How They Relate

```
                    ┌──────────────────────┐
                    │  Consensus Baseline   │  ← What outlets agree on (set math)
                    │  (Gc)                 │
                    └──────┬───────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌──────────────┐
     │Omission (Oi)│ │Framing (Vf)│ │Scatter-Shot  │
     │ set math   │ │ embeddings │ │(Sa)          │
     │ per outlet │ │ per outlet │ │ reputation DB │
     └────────────┘ └────────────┘ └──────────────┘
```

- **Oi and Vf** are computed fresh every pipeline run, per outlet, from what the LLM
  extracted in this batch.
- **Gc** is also computed fresh every run — it's the thresholded intersection of all
  current outlet graphs.
- **Sa** is historical — accumulated in SQLite across runs. A single run only *updates*
  it if enough new data arrives.

All four feed into the LLM's Call 4 (Forensic Synthesis) prompt as context, so the
final report text is informed by all of them.
