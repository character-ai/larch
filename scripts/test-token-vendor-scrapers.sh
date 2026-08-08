#!/usr/bin/env bash
# test-token-vendor-scrapers.sh — offline regression harness for vendor token extraction.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0

# Keep this offline harness independent from a caller's live session state.
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH LARCH_TOKEN_LEDGER
unset LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# scripts/larch.sh is the only approved Rust entrypoint and reads this root.
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
PASS=0
FAIL=0
SKIP=0

# `agent parse-codex-usage` is Rust-owned (#8105). A dev checkout needs an
# explicitly built binary, which the Python-only harness shard does not have.
# Rows that need it skip loudly instead of silently passing; Rust owns their
# parity coverage in crates/larch-core and crates/larch-adapters.
RUST_AVAILABLE=0
for candidate in "${LARCH_BINARY:-}" "$REPO_ROOT/target/release/larch" "$REPO_ROOT/target/debug/larch"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
        export LARCH_BINARY="$candidate"
        RUST_AVAILABLE=1
        break
    fi
done

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }
skip() { echo "SKIP: $1 (no built larch binary; set LARCH_BINARY)" >&2; SKIP=$((SKIP + 1)); }
contains() {
    case "$3" in
        *"$2"*) pass ;;
        *) fail "$1 missing '$2': $3" ;;
    esac
}
eq() {
    if [[ "$2" == "$3" ]]; then pass; else fail "$1 expected '$2' got '$3'"; fi
}

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-vendor.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/codex.events.jsonl" <<'JSONL'
wrapper noise
{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}
{"usage":{"input_tokens":20,"input_tokens_details":{"cached_tokens":5},"output_tokens":7}}
JSONL
if [[ "$RUST_AVAILABLE" == 1 ]]; then
    codex_usage=$("$REPO_ROOT/scripts/larch.sh" agent parse-codex-usage "$TMP/codex.events.jsonl" 2>/dev/null || true)
    eq "codex parse usage" $'INPUT=115\nCACHED_INPUT=905\nOUTPUT=57\nTOTAL=1077' "$codex_usage"
else
    skip "codex parse usage"
fi

cat > "$TMP/codex-bad.events.jsonl" <<'JSONL'
{"msg":{"kind":"started"}}
JSONL
if [[ "$RUST_AVAILABLE" == 1 ]]; then
    set +e
    codex_bad=$("$REPO_ROOT/scripts/larch.sh" agent parse-codex-usage "$TMP/codex-bad.events.jsonl" 2>/dev/null)
    codex_bad_rc=$?
    set -e
    eq "codex no-usage fail-closed rc" "1" "$codex_bad_rc"
    eq "codex no-usage stdout empty" "" "$codex_bad"
else
    skip "codex no-usage fail-closed"
fi

cat > "$TMP/codex-rollup.events.jsonl" <<'JSONL'
{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}
{"type":"token_usage","input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}
{"type":"task.completed","input_tokens":999,"cached_input_tokens":500,"output_tokens":111}
JSONL
if [[ "$RUST_AVAILABLE" == 1 ]]; then
    codex_rollup=$("$REPO_ROOT/scripts/larch.sh" agent parse-codex-usage "$TMP/codex-rollup.events.jsonl" 2>/dev/null || true)
    eq "codex token_usage sums with per-turn usage while ignoring non-token_usage top-level lifecycle fields" $'INPUT=877\nCACHED_INPUT=7900\nOUTPUT=272\nTOTAL=9049' "$codex_rollup"
else
    skip "codex token_usage rollup sums"
fi

cat > "$TMP/cursor.json" <<'JSON'
{"result":"plain reviewer prose","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}
JSON
read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TMP/cursor.json")
eq "cursor input" "1" "$INP"
eq "cursor total" "10" "$((INP + OUT + CR + CW))"

bad=$(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TMP/nope.json" 2>/dev/null || echo "0 0 0 0")
eq "cursor malformed fallback" "0 0 0 0" "$bad"

# claude_sub usage extraction (issue #3637): launch-claude-{subprocess,ci}.sh run
# `claude --print --output-format json` and parse the Claude snake_case .usage
# schema. Pin the exact jq the launchers use so the claude_sub ledger row totals
# stay correct.
cat > "$TMP/claude.json" <<'JSON'
{"type":"result","result":"reviewer prose","usage":{"input_tokens":100,"output_tokens":50,"cache_read_input_tokens":10,"cache_creation_input_tokens":5}}
JSON
read -r CL_IN CL_OUT CL_CR CL_CC < <(jq -r '.usage // {} | "\(.input_tokens // 0) \(.output_tokens // 0) \(.cache_read_input_tokens // 0) \(.cache_creation_input_tokens // 0)"' "$TMP/claude.json")
eq "claude_sub input" "100" "$CL_IN"
eq "claude_sub cache_create folds cache_creation_input_tokens" "5" "$CL_CC"
eq "claude_sub total" "165" "$((CL_IN + CL_OUT + CL_CR + CL_CC))"

claude_bad=$(jq -r '.usage // {} | "\(.input_tokens // 0) \(.output_tokens // 0) \(.cache_read_input_tokens // 0) \(.cache_creation_input_tokens // 0)"' "$TMP/nope.json" 2>/dev/null || echo "0 0 0 0")
eq "claude_sub malformed fallback" "0 0 0 0" "$claude_bad"

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '{"result":"reviewer prose only","usage":{"inputTokens":5,"outputTokens":6,"cacheReadTokens":7,"cacheWriteTokens":8}}\n'
EOF
chmod +x "$STUB_BIN/cursor"

OUT_FILE="$TMP/cursor-review.txt"
# `agent launch-review` is Rust-owned (#8115), so retain this launcher smoke
# only in harness lanes that have an explicitly built binary.
if [[ "$RUST_AVAILABLE" == 1 ]]; then
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    PATH="$STUB_BIN:$PATH" \
    LARCH_CURSOR_MODEL=stub-model \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$REPO_ROOT/scripts/larch.sh" agent launch-review --tool cursor --output "$OUT_FILE" --timeout 30 --prompt "review" >/dev/null

    eq "cursor review prose output" "reviewer prose only" "$(cat "$OUT_FILE")"
    if jq -e '.usage.inputTokens == 5' "${OUT_FILE}.json" >/dev/null; then pass; else fail "cursor review raw JSON sidecar missing usage"; fi
else
    skip "cursor launch-review prose output"
    skip "cursor launch-review raw JSON sidecar"
fi

# agent launch-cursor-implement + agent launch-codex-implement record-vendor smoke
# (issue #1351 Gap 4 — overlaps Gap 1's per-launcher harness coverage). The
# launcher's own scrape path already runs in tests-cursor/codex-implementer.sh;
# this scrapers harness pins that the resulting JSONL row carries
# raw=cursor_implement / raw=codex_implement, which is the contract scraper
# consumers (token-report) depend on for the "vendor:cursor_implement" /
# "vendor:codex_implement" attribution.
if command -v jq >/dev/null 2>&1; then
    LCI_BIN="$TMP/lci-bin"
    mkdir -p "$LCI_BIN"
    cat > "$LCI_BIN/cursor" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '{"result":"stub","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n'
STUB_EOF
    chmod +x "$LCI_BIN/cursor"

    cat > "$LCI_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'stub codex transcript payload\n' > "$output_path"
printf '{"type":"token_usage","usage":{"input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}}\n'
STUB_EOF
    chmod +x "$LCI_BIN/codex"

    LCI_SCRATCH="$TMP/lci-scratch"
    mkdir -p "$LCI_SCRATCH"
    printf 'plan\n' > "$LCI_SCRATCH/plan.md"
    printf 'feature\n' > "$LCI_SCRATCH/feature.txt"

    # Per-launcher invocation, with a unique session id so each ledger is
    # isolated and the dump-and-assert step reads the correct file.
    for variant in cursor codex; do
        if [[ "$RUST_AVAILABLE" != 1 ]]; then
            # Both implement launchers are Rust-owned; without a built binary
            # there is nothing to scrape.
            skip "agent launch-${variant}-implement record-vendor"
            continue
        fi
        LCI_SESSION="lci-${variant}-$$"
        case "$variant" in
            cursor)
                AGENT_PROMPT="$REPO_ROOT/skills/implement/prompts/cursor-implementer.md"
                LAUNCHER_ARGS=("$REPO_ROOT/scripts/larch.sh" agent launch-cursor-implement)
                EXPECTED_RAW="cursor_implement"
                EXPECTED_TOTAL=10
                ;;
            codex)
                AGENT_PROMPT="$REPO_ROOT/skills/implement/prompts/codex-implementer.md"
                LAUNCHER_ARGS=("$REPO_ROOT/scripts/larch.sh" agent launch-codex-implement)
                EXPECTED_RAW="codex_implement"
                EXPECTED_TOTAL=7999
                ;;
        esac

        if [[ ! -f "$AGENT_PROMPT" ]]; then
            fail "$variant agent prompt missing: $AGENT_PROMPT"
            continue
        fi

        TR="$LCI_SCRATCH/$variant-transcript.txt"
        SC="$LCI_SCRATCH/$variant-sidecar.log"
        MF="$LCI_SCRATCH/$variant-manifest.json"
        QA="$LCI_SCRATCH/$variant-qa.json"
        LCI_LEDGER="$TMP/${variant}-token-ledger.jsonl"

        LARCH_TOKEN_SESSION_ID="$LCI_SESSION" \
        LARCH_TOKEN_LEDGER="$LCI_LEDGER" \
        IMPLEMENT_TMPDIR='' \
        PATH="$LCI_BIN:$PATH" \
        CURSOR_API_KEY="test-cursor-api-key" \
        RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
        LARCH_CURSOR_MODEL="stub-model" \
        LARCH_CODEX_MODEL="stub-codex-model" \
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
            "${LAUNCHER_ARGS[@]}" \
                --transcript-path "$TR" \
                --sidecar-log "$SC" \
                --manifest-path "$MF" \
                --scout-manifest-path "$(dirname "$MF")/scout-coder-manifest.json" \
                --qa-pending-path "$QA" \
                --plan-file "$LCI_SCRATCH/plan.md" \
                --feature-file "$LCI_SCRATCH/feature.txt" \
                --agent-prompt "$AGENT_PROMPT" \
                --timeout 30 >/dev/null 2>&1
        if [[ ! -s "$LCI_LEDGER" ]]; then
            case "$variant" in
                cursor)
                    fail "agent launch-cursor-implement produced empty/missing ledger ($LCI_LEDGER); cursor_auth_preflight may have aborted before the launcher could record-vendor (verify CURSOR_API_KEY env, cursor usage stub, and PATH wiring)"
                    ;;
                codex)
                    fail "agent launch-codex-implement produced empty/missing ledger ($LCI_LEDGER); the launcher exited before record-vendor ran (verify codex usage stub on PATH and $LCI_SCRATCH wiring)"
                    ;;
                *)
                    fail "agent launch-${variant}-implement produced empty/missing ledger ($LCI_LEDGER); the launcher exited before record-vendor ran (verify ${variant} usage stub on PATH and scratch dir wiring)"
                    ;;
            esac
            rm -f "$LCI_LEDGER"
            continue
        fi
        if [[ "$variant" == "codex" ]]; then
            if [[ "$RUST_AVAILABLE" != 1 ]]; then
                # Per-bucket codex usage flows through the Rust-owned parser.
                skip "agent launch-${variant}-implement per-bucket codex usage"
            elif [[ -f "$LCI_LEDGER" ]] && jq -e --arg raw "$EXPECTED_RAW" \
                'select(.type=="vendor" and .raw==$raw and .vendor=="codex" and .input==777 and .cache_read==7000 and .output==222 and .total==7999)' "$LCI_LEDGER" >/dev/null 2>&1; then
                pass
            else
                fail "agent launch-${variant}-implement did not record per-bucket codex usage; ledger=$LCI_LEDGER content=$(cat "$LCI_LEDGER" 2>/dev/null)"
            fi
        elif [[ -f "$LCI_LEDGER" ]] && jq -e --arg raw "$EXPECTED_RAW" --argjson total "$EXPECTED_TOTAL" \
            'select(.type=="vendor" and .raw==$raw and .total==$total)' "$LCI_LEDGER" >/dev/null 2>&1; then
            pass
        else
            fail "agent launch-${variant}-implement did not record-vendor raw=$EXPECTED_RAW total=$EXPECTED_TOTAL; ledger=$LCI_LEDGER content=$(cat "$LCI_LEDGER" 2>/dev/null)"
        fi
        rm -f "$LCI_LEDGER"
    done

    # Issue #1427: Codex aggregate-only telemetry must surface in the
    # Total column. Records a vendor row with only total= set because the
    # codex CLI does not split input/output counts.
    TR_LEDGER="$TMP/codex-only-ledger.jsonl"
    TR_TRANSCRIPT="$TMP/codex-only-transcript.jsonl"
    cat > "$TR_LEDGER" <<'JSONL'
{"type":"mark","step":"Step 2 - implement","ts":"2026-05-06T00:00:00Z"}
{"type":"vendor","vendor":"codex","total":192077,"raw":"codex_implement","ts":"2026-05-06T00:00:05Z"}
JSONL
    printf '' > "$TR_TRANSCRIPT"
    codex_md=$(python3 "$REPO_ROOT/python/cli.py" token report --ledger "$TR_LEDGER" --transcript "$TR_TRANSCRIPT" --full --markdown)
    contains "codex-only header" "| Step | Skill | Input | Output | Total |" "$codex_md"
    contains "codex-only step row" "| Step 2 - implement | **step total** | 0 | 0 | 192077 |" "$codex_md"
    contains "codex-only grand total" "| **Grand total** |  | 0 | 0 | 192077 |" "$codex_md"

    PB_LEDGER="$TMP/codex-per-bucket-ledger.jsonl"
    cat > "$PB_LEDGER" <<'JSONL'
{"type":"mark","step":"Step 2 - implement","ts":"2026-05-06T00:00:00Z"}
{"type":"vendor","vendor":"codex","input":100,"output":50,"cache_read":900,"total":1050,"raw":"codex_implement","ts":"2026-05-06T00:00:05Z"}
JSONL
    pb_json=$(python3 "$REPO_ROOT/python/cli.py" token report --ledger "$PB_LEDGER" --transcript "$TR_TRANSCRIPT" --full --format json)
    if printf '%s\n' "$pb_json" | jq -e '.BUCKETS_codex.input == 100 and .BUCKETS_codex.cached_input == 900 and .BUCKETS_codex.output == 50 and .BUCKETS_codex.total == 1050' >/dev/null; then
        pass
    else
        fail "codex per-bucket BUCKETS regression failed: $pb_json"
    fi
    set +e
    python3 "$REPO_ROOT/python/cli.py" token cost --codex-input-tokens 100 --codex-cached-input-tokens 900 --codex-output-tokens 50 >"$TMP/cost.out" 2>"$TMP/cost.err"
    cost_rc=$?
    set -e
    eq "codex per-bucket cost rc" "0" "$cost_rc"
    if grep -Eq 'BLENDED_WARN|blended rate' "$TMP/cost.err"; then
        fail "codex per-bucket cost should not warn: $(cat "$TMP/cost.err")"
    else
        pass
    fi
    set +e
    python3 "$REPO_ROOT/python/cli.py" token render-cost-line \
        --codex-input-tokens 100 \
        --codex-cached-input-tokens 900 \
        --codex-output-tokens 50 >"$TMP/render-cost.out" 2>"$TMP/render-cost.err"
    render_cost_rc=$?
    set -e
    eq "codex per-bucket render-cost-line rc" "0" "$render_cost_rc"
    if grep -Eq 'BLENDED_WARN|blended rate' "$TMP/render-cost.err"; then
        fail "codex per-bucket render-cost-line should not warn: $(cat "$TMP/render-cost.err")"
    else
        pass
    fi
    set +e
    python3 "$REPO_ROOT/python/cli.py" token cost --codex-tokens 1050 >"$TMP/cost-aggregate.out" 2>"$TMP/cost-aggregate.err"
    aggregate_cost_rc=$?
    set -e
    eq "codex aggregate cost rc" "0" "$aggregate_cost_rc"
    contains "codex aggregate warning" "blended rate" "$(cat "$TMP/cost-aggregate.err" 2>/dev/null)"
else
    fail "jq required for codex launcher/token-cost integration assertions"
fi

total=$((PASS + FAIL))
if (( SKIP > 0 )); then
    echo "SKIPPED: test-token-vendor-scrapers.sh — $SKIP Rust-owned assertions (set LARCH_BINARY to run them)" >&2
fi
if (( FAIL == 0 )); then
    echo "PASS: test-token-vendor-scrapers.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-vendor-scrapers.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
