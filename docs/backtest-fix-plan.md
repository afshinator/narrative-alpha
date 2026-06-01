# Backtest Fix Plan

## Status (2026-06-01)
All 63 outlets UNRATED. Two bugs block backtest completion.

## Bug 1: Entity Normalization Schema Mismatch ✅ Fixed
- Prompt says "output JSON matching the schema provided" but no schema included
- LLM returns `{entities: [{canonical, surface_forms}]}`
- Code expects `{normalized_mappings: [{surface_form_variant, canonical_reference_identity}]}`
- **Fix applied:** prompt includes schema, parser accepts both formats

## Bug 2: Backtest Timeout ❌ Needs fix
Graph extraction is the bottleneck:
- Uses `call_3_graph_extraction` (DeepSeek V4 Pro, thinking mode, ~30-60s/doc)
- Processes 10-20 docs sequentially (1 LLM call per doc)
- Pipeline timeout: `BACKTEST_TIMEOUT=120s`
- Actual time: 10-20+ minutes

### Fix Options

**Option A — Fast track (recommended):**
- Use `call_1_entity_normalization` (DeepSeek V4 Flash) for backtest graph extraction instead of V4 Pro thinking
- Reduce article count from 15 to 8 per query
- Parallelize via ThreadPoolExecutor
- Est: 2-3 min total per outlet

**Option B — Parallel + timeout:**
- Keep V4 Pro but parallelize graph extraction with ThreadPoolExecutor(max_workers=4)
- Increase BACKTEST_TIMEOUT from 120s to 300s
- Reduce article count from 15 to 10
- Est: 5-8 min total per outlet

**Option C — Skip graph extraction entirely for backtest:**
- Use entity normalization outputs directly for cross-source persistence check
- Replace graph extraction with simpler claim-overlap analysis
- Fastest but less accurate Sa calculation

### Verification
After fix, run:
```bash
cd /project/narrative-alpha && . .venv/bin/activate && export $(grep -v '^#' .env | xargs)
python -c "from narrative.backtest import execute_historical_backtest; execute_historical_backtest('bbc.com', 'TECHNOLOGY')"
sqlite3 outlet_reputation.db "SELECT domain, rating_status, scatter_shot_anomaly_factor FROM outlet_reputation WHERE domain='bbc.com'"
```
Expected: `bbc.com|RATED|0.xxxx`
