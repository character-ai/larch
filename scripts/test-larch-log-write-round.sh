#!/usr/bin/env bash
# test-larch-log-write-round.sh — regression harness for larch-log write-round.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LARCH_LOG="$SCRIPT_DIR/larch-log.sh"

TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"
TMP="$(mktemp -d "$TMP_BASE/larch-implement-write-round.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_file() {
    local path="$1" label="$2"
    [[ -f "$path" ]] || fail "$label missing: $path"
}

assert_not_file() {
    local path="$1" label="$2"
    [[ ! -e "$path" ]] || fail "$label should not exist: $path"
}

assert_grep() {
    local pattern="$1" path="$2" label="$3"
    grep -Eq "$pattern" "$path" || fail "$label"
}

assert_not_grep() {
    local pattern="$1" path="$2" label="$3"
    [[ -e "$path" ]] || return 0
    if grep -Eq "$pattern" "$path"; then
        fail "$label"
    fi
}

assert_round_order() {
    python3 - "$LARCH_LOG" <<'PYEOF' || fail "dynamic codex retry deny must precede broad output allow"
import sys

text = open(sys.argv[1], encoding="utf-8").read()
deny = text.index("dyn-*-codex-output-retry*.txt")
allow = text.index("*-output.txt|*-output-*.txt")
if deny > allow:
    raise SystemExit(1)
PYEOF
}

assert_json_result_stripped() {
    local path="$1" label="$2"
    python3 - "$path" <<'PYEOF' || fail "$label"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
if isinstance(data, dict) and "result" in data:
    raise SystemExit(1)
PYEOF
}

log_root="$TMP/larch-logs"
source_dir="$TMP/round-1"
mkdir -p "$source_dir"

cat > "$source_dir/findings.md" <<EOF
### FINDING_1:
path: $TMP/round-1/private-file
token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD
EOF

cat > "$source_dir/codex-specialist-security-output.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","secret argv"]
OUTPUT_FILE=/tmp/source/codex-specialist-security-output.txt
EOF

cat > "$source_dir/dyn-api-contract-codex-output.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","dynamic argv"]
OUTPUT_FILE=/tmp/source/dyn-api-contract-codex-output.txt
EOF
printf 'dynamic codex raw body\n' > "$source_dir/dyn-api-contract-codex-output.txt"
printf 'dynamic codex cap hit\n' > "$source_dir/dyn-api-contract-codex-output.txt.cap-hit"
cat > "$source_dir/dyn-api-contract-codex-output-phase2.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","dynamic phase argv"]
OUTPUT_FILE=/tmp/source/dyn-api-contract-codex-output-phase2.txt
EOF
printf 'dynamic codex phase raw body\n' > "$source_dir/dyn-api-contract-codex-output-phase2.txt"
cat > "$source_dir/dyn-api-contract-codex-output-phase2.txt.json" <<'EOF'
{"result":"dynamic raw phase codex payload","status":"ok"}
EOF
printf 'dynamic codex phase cap hit\n' > "$source_dir/dyn-api-contract-codex-output-phase2.txt.cap-hit"
printf 'dynamic codex named phase raw body\n' > "$source_dir/dyn-api-contract-codex-output-phasealpha.txt"
cat > "$source_dir/dyn-api-contract-codex-output-phasealpha.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","dynamic named phase argv"]
OUTPUT_FILE=/tmp/source/dyn-api-contract-codex-output-phasealpha.txt
EOF
cat > "$source_dir/dyn-api-contract-codex-output-phasealpha.txt.json" <<'EOF'
{"result":"dynamic raw named phase codex payload","status":"ok"}
EOF
printf 'dynamic codex named phase cap hit\n' > "$source_dir/dyn-api-contract-codex-output-phasealpha.txt.cap-hit"
printf 'dynamic codex retry raw body\n' > "$source_dir/dyn-api-contract-codex-output-retry.txt"
printf 'dynamic codex retry meta\n' > "$source_dir/dyn-api-contract-codex-output-retry.txt.meta"
printf '{"result":"dynamic codex retry json"}\n' > "$source_dir/dyn-api-contract-codex-output-retry.txt.json"
printf 'dynamic codex retry cap hit\n' > "$source_dir/dyn-api-contract-codex-output-retry.txt.cap-hit"
printf 'dynamic cursor raw body\n' > "$source_dir/dyn-api-contract-output.txt"
cat > "$source_dir/dyn-api-contract-output.txt.meta" <<'EOF'
TOOL=cursor
TIMEOUT=1200
CMD_JSON=["cursor","agent","dynamic argv"]
OUTPUT_FILE=/tmp/source/dyn-api-contract-output.txt
EOF
cat > "$source_dir/dyn-api-contract-codex-output.txt.json" <<'EOF'
{"result":"dynamic raw codex payload","status":"ok"}
EOF

cat > "$source_dir/cursor-specialist-security-output-phase2.txt.meta" <<'EOF'
TOOL=cursor
  CMD_JSON=["cursor","agent","secret argv"]
OUTPUT_FILE=/tmp/source/cursor-specialist-security-output-phase2.txt
EOF

cat > "$source_dir/cursor-vote-output.txt.json" <<'EOF'
{"result":"large raw cursor payload","usage":{"inputTokens":10},"status":"ok"}
EOF

cat > "$source_dir/codex-vote-output.txt.json" <<'EOF'
{"result":"large raw codex payload","status":"ok"}
EOF

printf '# Round summary\n' > "$source_dir/review-round-summary.md"
printf 'finding_id\treviewer_slots\tvoting_result\n' > "$source_dir/findings-classification.tsv"
# Sidecar files consolidated into round-meta.json
printf 'CODER_STATUS=skipped\nCODER_TOOL=cursor\n' > "$source_dir/coder.env"
printf 'FINDING_1_ACCEPTED=true\nACCEPTED_COUNT=1\n' > "$source_dir/review-tally.env"
printf 'REVIEWER_FILE=<TMPDIR>/r1\nTOOL=cursor\nSTATUS=OK\n' > "$source_dir/collector-results.env"
printf 'REVIEWER_FILE=<TMPDIR>/r1\nTOOL=cursor\nSTATUS=OK\n' > "$source_dir/collect-agent-results.log"
printf '{"schema_version":2,"rounds_completed":1}\n' > "$source_dir/review-summary.json"
printf 'wrapper line\n' > "$source_dir/coder-cursor.wrapper.log"
printf 'excluded\n' > "$source_dir/random-notes.txt"
printf 'excluded\n' > "$source_dir/session-env.sh"
printf 'excluded\n' > "$source_dir/coder-output.log"
printf 'excluded\n' > "$source_dir/coder-codex.log"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt"
printf '{"result":"excluded static codex json"}\n' > "$source_dir/codex-specialist-security-output.txt.json"
printf 'excluded static codex cap hit\n' > "$source_dir/codex-specialist-security-output.txt.cap-hit"
printf 'excluded phased static codex raw body\n' > "$source_dir/codex-specialist-security-output-phase2.txt"
cat > "$source_dir/codex-specialist-security-output-phase2.txt.meta" <<'EOF'
TOOL=codex
TIMEOUT=1200
CMD_JSON=["codex","exec","static phase argv"]
OUTPUT_FILE=/tmp/source/codex-specialist-security-output-phase2.txt
EOF
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.done"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.inner.done"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.diag"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.prompt"
printf 'excluded\n' > "$source_dir/dyn-api-contract-codex-output.txt.prompt"
printf 'excluded\n' > "$source_dir/dyn-api-contract-codex-output-phase2.txt.prompt"
printf 'excluded\n' > "$source_dir/dyn-api-contract-codex-output-vote-prompt.txt"
printf 'excluded\n' > "$source_dir/dyn-api-contract-codex-output.txt.events.jsonl"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.sidecar"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.dirty-tree"
printf 'excluded\n' > "$source_dir/codex-specialist-security-output.txt.untracked-baseline"
printf 'first-pass narrative only\n' > "$source_dir/cursor-specialist-edge-cases-output-first-pass.txt"
printf 'NO_ISSUES_FOUND\n' > "$source_dir/cursor-specialist-security-output.txt"
printf 'NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN\n' > "$source_dir/cursor-specialist-security-output-ns-retry.txt.meta"
printf 'PRUNE_ACTIVE=true\nPRUNE_STATUS=active-kept-all\n' > "$source_dir/prune-decision.env"
printf 'PRUNED_COUNT=0\nSTATUS=skipped\n' > "$source_dir/prune-nit.env"

out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 1 --source-dir "$source_dir")"
[[ "$out" == *"LOG_WRITTEN=true"* ]] || fail "write-round should report write: $out"

round_dir="$log_root/implement/run123/round-1"
assert_not_file "$round_dir/findings.md" "findings excluded (projection of review-findings-full.jsonl)"
assert_not_file "$round_dir/codex-specialist-security-output.txt.meta" "static codex meta sidecar excluded"
assert_not_file "$round_dir/cursor-specialist-security-output-phase2.txt.meta" "phased static cursor meta sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt" "dynamic codex raw body excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt.meta" "dynamic codex meta sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt.json" "dynamic codex json sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt.cap-hit" "dynamic codex cap-hit sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phase2.txt" "dynamic codex phase raw body excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phase2.txt.meta" "dynamic codex phase meta sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phase2.txt.json" "dynamic codex phase json sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phase2.txt.cap-hit" "dynamic codex phase cap-hit sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phasealpha.txt" "dynamic codex named phase raw body excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phasealpha.txt.meta" "dynamic codex named phase meta sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phasealpha.txt.json" "dynamic codex named phase json sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phasealpha.txt.cap-hit" "dynamic codex named phase cap-hit sidecar excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-retry.txt" "unsupported dynamic codex retry raw body excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-retry.txt.meta" "unsupported dynamic codex retry meta excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-retry.txt.json" "unsupported dynamic codex retry json excluded"
assert_not_file "$round_dir/dyn-api-contract-codex-output-retry.txt.cap-hit" "unsupported dynamic codex retry cap-hit excluded"
assert_not_file "$round_dir/dyn-api-contract-output.txt" "dynamic cursor raw body excluded"
assert_not_file "$round_dir/dyn-api-contract-output.txt.meta" "dynamic cursor meta sidecar excluded"
assert_not_file "$round_dir/cursor-vote-output.txt.json" "cursor json sidecar"
assert_not_file "$round_dir/codex-vote-output.txt.json" "codex json sidecar"
assert_file "$round_dir/review-round-summary.md" "summary"
assert_file "$round_dir/findings-classification.tsv" "findings classification TSV"
assert_file "$round_dir/round-meta.json" "round-meta.json composed from sidecar files"
assert_not_file "$round_dir/coder.env" "coder.env must not be committed individually (consolidated into round-meta.json)"
assert_not_file "$round_dir/review-tally.env" "review-tally.env must not be committed individually"
assert_not_file "$round_dir/collector-results.env" "collector-results.env must not be committed individually"
assert_not_file "$round_dir/random-notes.txt" "unregistered file"
assert_not_file "$round_dir/session-env.sh" "session env"
assert_not_file "$round_dir/coder-output.log" "excluded coder transcript"
assert_not_file "$round_dir/coder-codex.log" "excluded coder codex transcript"
assert_not_file "$round_dir/codex-specialist-security-output.txt" "static codex raw transcript excluded"
assert_not_file "$round_dir/codex-specialist-security-output.txt.json" "static codex json sidecar excluded"
assert_not_file "$round_dir/codex-specialist-security-output.txt.cap-hit" "static codex cap-hit sidecar excluded"
assert_not_file "$round_dir/codex-specialist-security-output-phase2.txt" "phased static codex raw transcript excluded"
assert_not_file "$round_dir/codex-specialist-security-output-phase2.txt.meta" "phased static codex meta sidecar excluded"
assert_not_file "$round_dir/codex-specialist-security-output.txt.done" "excluded done sentinel"
assert_not_file "$round_dir/codex-specialist-security-output.txt.inner.done" "excluded inner done sentinel"
assert_not_file "$round_dir/codex-specialist-security-output.txt.diag" "excluded diag sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.prompt" "excluded prompt sidecar"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt.prompt" "excluded dynamic codex prompt sidecar"
assert_not_file "$round_dir/dyn-api-contract-codex-output-phase2.txt.prompt" "excluded dynamic codex phase prompt sidecar"
assert_not_file "$round_dir/dyn-api-contract-codex-output-vote-prompt.txt" "excluded dynamic-shaped vote prompt"
assert_not_file "$round_dir/dyn-api-contract-codex-output.txt.events.jsonl" "excluded dynamic codex events telemetry"
assert_not_file "$round_dir/codex-specialist-security-output.txt.sidecar" "excluded sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.dirty-tree" "excluded dirty tree sidecar"
assert_not_file "$round_dir/codex-specialist-security-output.txt.untracked-baseline" "excluded untracked baseline sidecar"
assert_not_file "$round_dir/cursor-specialist-edge-cases-output-first-pass.txt" "ns-retry first-pass sidecar excluded"

assert_not_grep '^CMD_JSON=' "$round_dir/cursor-specialist-security-output-phase2.txt.meta" "phase CMD_JSON stripped"
assert_not_grep '^CMD_JSON=' "$round_dir/codex-specialist-security-output-phase2.txt.meta" "static codex phase CMD_JSON stripped"
assert_round_order

# Verify round-meta.json has expected sections from sidecar files
python3 - "$round_dir/round-meta.json" <<'PYEOF' || fail "round-meta.json missing expected sidecar sections"
import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

assert 'tally' in data, "missing tally section"
assert 'coder' in data, "missing coder section"
assert data['coder'].get('CODER_TOOL') == 'cursor', f"coder.CODER_TOOL expected 'cursor', got {data['coder'].get('CODER_TOOL')!r}"
assert 'summary' in data, "missing summary section"
assert 'collector' in data, "missing collector section"
assert 'collect_log' not in data, "collect_log should be omitted"
assert 'wrapper_logs' in data, "missing wrapper_logs section"
assert 'cursor' in data['wrapper_logs'], "missing wrapper_logs.cursor"
signals = data.get('reviewer_signals') or []
assert signals, "missing reviewer_signals when reviewer outputs exist"
for key in ('output_basename', 'slot_label', 'result_kind', 'ns_retry_reason', 'first_pass_trailing_content'):
    assert key in signals[0], f"reviewer_signals entry missing {key}"
sec = next((s for s in signals if s.get('output_basename') == 'cursor-specialist-security-output.txt'), None)
assert sec, "cursor-specialist-security-output signal missing"
assert sec.get('ns_retry_reason') == 'NO_ISSUES_FOUND_TOO_THIN', sec.get('ns_retry_reason')
PYEOF
assert_file "$round_dir/prune-decision.env" "prune-decision.env included in concise round"
assert_file "$round_dir/prune-nit.env" "prune-nit.env included in concise round"

debug_source="$TMP/round-debug-cap"
mkdir -p "$debug_source"
python3 - "$debug_source" <<'PYEOF'
import sys
path = sys.argv[1] + "/cursor-vote-output.txt"
with open(path, "wb") as fh:
    fh.write(b"x" * 3000)
PYEOF
LARCH_FLUSH_DEBUG=1 "$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 5 --source-dir "$debug_source" >/dev/null
vote_path="$log_root/implement/run123/round-5/cursor-vote-output.txt"
assert_file "$vote_path" "debug vote output included"
vote_bytes=$(wc -c < "$vote_path" | tr -d '[:space:]')
[[ "$vote_bytes" -lt 3000 ]] || fail "vote output should be truncated below source size (got $vote_bytes)"
grep -Fq '[TRUNCATED: original' "$vote_path" || fail "vote output should carry truncation marker"

reviewer_only_source="$TMP/round-reviewer-only"
mkdir -p "$reviewer_only_source"
printf 'NO_ISSUES_FOUND\n' > "$reviewer_only_source/codex-specialist-correctness-output.txt"
out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 6 --source-dir "$reviewer_only_source")"
[[ "$out" == *"LOG_WRITTEN=true"* ]] || fail "reviewer-only write-round should write round-meta: $out"
assert_file "$log_root/implement/run123/round-6/round-meta.json" "reviewer-only round-meta.json"
python3 - "$log_root/implement/run123/round-6/round-meta.json" <<'PYEOF' || fail "reviewer-only round-meta missing reviewer_signals"
import json, sys
data = json.load(open(sys.argv[1]))
assert data.get("reviewer_signals"), data
PYEOF

out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 1 --source-dir "$source_dir")"
[[ "$out" == *"UNCHANGED=true"* ]] || fail "write-round retry should be unchanged: $out"

python_only_bin="$TMP/python-only-bin"
mkdir -p "$python_only_bin"
cat > "$python_only_bin/jq" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$python_only_bin/jq"
PATH="$python_only_bin:$PATH" "$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 2 --source-dir "$source_dir" >/dev/null
assert_not_file "$log_root/implement/run123/round-2/findings.md" "round-2 findings excluded (projection)"

excluded_only_source="$TMP/round-empty"
mkdir -p "$excluded_only_source"
printf 'excluded\n' > "$excluded_only_source/random-notes.txt"
printf 'excluded\n' > "$excluded_only_source/coder-output.log"
out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 3 --source-dir "$excluded_only_source")"
[[ "$out" == *"LOG_WRITTEN=false"* ]] || fail "excluded-only write-round should not write files: $out"
[[ "$out" == *"UNCHANGED=true"* ]] || fail "excluded-only write-round should be unchanged: $out"
round3_dir="$log_root/implement/run123/round-3"
[[ -d "$round3_dir" ]] || fail "round-3 directory missing"
if find "$round3_dir" -mindepth 1 -maxdepth 1 | grep -q .; then
    fail "round-3 should contain no copied artifacts"
fi

invalid_source="$TMP/round-invalid"
mkdir -p "$invalid_source"
cat > "$invalid_source/cursor-vote-output.txt.json" <<'EOF'
{"result":
EOF
trim_tmpdir="$TMP/write-round-tmp"
mkdir -p "$trim_tmpdir"
TMPDIR="$trim_tmpdir" "$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 4 --source-dir "$invalid_source" >/dev/null
assert_not_file "$log_root/implement/run123/round-4/cursor-vote-output.txt.json" "default-excluded invalid json sidecar should not be copied"
if find "$trim_tmpdir" -maxdepth 1 -name 'larch-log-round-trim.*' | grep -q .; then
    fail "write-round should clean round trim temps after failure"
fi

echo "=== dynamic-archetypes reviewer outputs compose reviewer_signals ==="
dyn_source="$TMP/round-dynamic-archetypes"
mkdir -p "$dyn_source/dynamic-archetypes"
printf 'NO_ISSUES_FOUND\n' > "$dyn_source/dynamic-archetypes/dyn-scope-anchor-output.txt"
out="$("$LARCH_LOG" write-round --log-root "$log_root" --skill implement --run-id run123 --round 7 --source-dir "$dyn_source")"
[[ "$out" == *"LOG_WRITTEN=true"* ]] || fail "dynamic-archetypes write-round should write round-meta: $out"
python3 - "$log_root/implement/run123/round-7/round-meta.json" <<'PYEOF' || fail "dynamic-archetypes reviewer_signals missing"
import json, sys
data = json.load(open(sys.argv[1]))
signals = data.get("reviewer_signals") or []
bases = {s.get("output_basename") for s in signals}
assert "dyn-scope-anchor-output.txt" in bases, bases
PYEOF

echo "=== implement multi-round concise flush stays within byte budget ==="
budget_root="$TMP/budget-log-root"
budget_source="$TMP/budget-source"
mkdir -p "$budget_source"
printf 'NO_ISSUES_FOUND\n' > "$budget_source/codex-specialist-correctness-output.txt"
printf 'PRUNE_ACTIVE=true\nPRUNE_STATUS=active-kept-all\n' > "$budget_source/prune-decision.env"
printf 'PRUNED_COUNT=0\nSTATUS=skipped\n' > "$budget_source/prune-nit.env"
for round in 1 2 3; do
    "$LARCH_LOG" write-round --log-root "$budget_root" --skill implement --run-id budget-run --round "$round" --source-dir "$budget_source" >/dev/null
done
budget_bytes=$(find "$budget_root/implement/budget-run" -type f -print0 | xargs -0 wc -c | awk '{s+=$1} END {print s+0}')
[[ "$budget_bytes" -lt 500000 ]] || fail "implement multi-round concise flush exceeded byte budget ($budget_bytes)"

echo "PASS: test-larch-log-write-round.sh"
