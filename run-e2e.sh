#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Hard kill any leftover
fuser -k 3001/tcp 2>/dev/null || true
sleep 1

# Source env in THIS shell so the server inherits it
set -a
source .env
set +a
export NARRATIVE_ALPHA_ROOT=/home/afshin/.narrative_alpha
mkdir -p "$NARRATIVE_ALPHA_ROOT/data/reports"

# Verify env key
echo "BrightData SERP zone: $BRIGHTDATA_SERP_ZONE"

# Start server
rm -f /tmp/narrative-server.log
nohup uvicorn narrative.server:app --host 0.0.0.0 --port 3001 --log-level info > /tmp/narrative-server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 3

# Verify
curl -s --max-time 5 http://localhost:3001/api/config > /dev/null && echo "Server OK" || { echo "Server FAIL"; cat /tmp/narrative-server.log; exit 1; }

KEYWORD="${1:-ai regulation}"
echo ""
echo "=== Pipeline: '$KEYWORD' ==="
echo ""

# Run pipeline in background — write a Python script file to avoid quoting hell
cat > /tmp/pipeline_runner.py << 'PYEOF'
import requests, json, time, sys
keyword = sys.argv[1] if len(sys.argv) > 1 else "ai regulation"
start = time.time()
print(f"[{time.strftime('%H:%M:%S')}] Submitting pipeline...", flush=True)
try:
    r = requests.post('http://localhost:3001/api/pipeline',
        json={'keyword': keyword, 'vertical': 'TECHNOLOGY'},
        timeout=600)
    elapsed = time.time() - start
    data = r.json()
    with open('/tmp/pipeline-result.json', 'w') as f:
        json.dump(data, f, indent=2)
    meta = data.get('event_meta', {})
    cid = meta.get('cluster_id', 'N/A')
    cc = meta.get('corpus_count', 'N/A')
    print(f"Status: {r.status_code} ({elapsed:.0f}s)")
    print(f"cluster_id={cid}, corpus_count={cc}")
    if 'validation_tracking' in str(meta):
        print("FLOOR GATE: INSUFFICIENT_CORPUS")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo "  (press Ctrl+C to stop waiting)"
echo ""

python3 /tmp/pipeline_runner.py "$KEYWORD" > /tmp/pipeline-done.log 2>&1 &
PIPE_PID=$!

# Poll showing STEP progress
PREV_STEP=""
while kill -0 $PIPE_PID 2>/dev/null; do
    sleep 15
    if [ -f /tmp/narrative-server.log ]; then
        # Show new STEP lines
        STEP=$(grep 'STEP' /tmp/narrative-server.log 2>/dev/null | tail -1 || true)
        if [ -n "$STEP" ] && [ "$STEP" != "$PREV_STEP" ]; then
            echo "  [$STEP]"
            PREV_STEP="$STEP"
        fi
        # Check for errors
        if grep -qi 'traceback' /tmp/narrative-server.log 2>/dev/null; then
            echo "  [!] Server error:"
            tail -3 /tmp/narrative-server.log
            break
        fi
    fi
done

echo ""
echo "=== Pipeline Complete ==="
cat /tmp/pipeline-done.log 2>/dev/null
echo ""
echo "--- Server log tail ---"
tail -5 /tmp/narrative-server.log 2>/dev/null
