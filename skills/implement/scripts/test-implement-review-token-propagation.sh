#!/usr/bin/env bash
# Offline harness for /implement -> /review token telemetry propagation.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
cd "$REPO_ROOT"
# review-and-fix CLI honors CLAUDE_PLUGIN_ROOT; a dev shell may point it at a
# cached plugin tree, which breaks sourcing and fails before the stub runs.
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
# Inherit no half-open quiet-stream session from the operator shell (e.g. a
# parent /implement sets LARCH_QUIET_BREADCRUMB_FD without a valid FD in this
# process); review-and-fix would then die in larch_err before review-core.
unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_BREADCRUMBS 2>/dev/null || true
SESSION_SETUP=(python3 "$REPO_ROOT/python/cli.py" session setup)
READ_KEY=(python3 "$REPO_ROOT/python/cli.py" session read-key)
REVIEW_AND_FIX=(python3 "$REPO_ROOT/python/cli.py" review-and-fix step5)

fail() { echo "FAIL: $1" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/larch-implement-review-token.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

IMPLEMENT_ENV="$TMP/implement-session-env.sh"
REVIEW_ENV="$TMP/review-session-env.sh"
TIMING_LEDGER="$TMP/timing-ledger.tsv"
cat > "$IMPLEMENT_ENV" <<EOF_ENV
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_TIMING_LEDGER=$TIMING_LEDGER
LARCH_TOKEN_SESSION_ID=parent-implement-session
LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env
EOF_ENV
printf 'SOURCE_FILE=/tmp/mock-transcript.jsonl\n' > "$TMP/claude-source.env"

OUT=$("${SESSION_SETUP[@]}" \
    --prefix claude-review-token-test \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$IMPLEMENT_ENV" \
    --write-session-env "$REVIEW_ENV")

case "$OUT" in
    *"LARCH_TOKEN_SESSION_ID=parent-implement-session"*) ;;
    *) fail "session-setup stdout did not forward LARCH_TOKEN_SESSION_ID: $OUT" ;;
esac
case "$OUT" in
    *"LARCH_TIMING_LEDGER="*) fail "session-setup stdout unexpectedly emitted LARCH_TIMING_LEDGER: $OUT" ;;
    *) ;;
esac

token_session_id=$("${READ_KEY[@]}" --file "$REVIEW_ENV" --key LARCH_TOKEN_SESSION_ID --default "")
claude_source_file=$("${READ_KEY[@]}" --file "$REVIEW_ENV" --key LARCH_CLAUDE_SOURCE_FILE --default "")
timing_ledger=$("${READ_KEY[@]}" --file "$REVIEW_ENV" --key LARCH_TIMING_LEDGER --default "")
[[ "$token_session_id" == "parent-implement-session" ]] || fail "review session-env lost LARCH_TOKEN_SESSION_ID"
[[ "$claude_source_file" == "$TMP/claude-source.env" ]] || fail "review session-env lost LARCH_CLAUDE_SOURCE_FILE"
[[ "$timing_ledger" == "$TIMING_LEDGER" ]] || fail "review session-env lost LARCH_TIMING_LEDGER"

UNSAFE_ENV="$TMP/unsafe-implement-session-env.sh"
UNSAFE_REVIEW_ENV="$TMP/unsafe-review-session-env.sh"
UNSAFE_ERR="$TMP/unsafe-session-setup.err"
cat > "$UNSAFE_ENV" <<EOF_ENV
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_TIMING_LEDGER=/etc/passwd
LARCH_TOKEN_SESSION_ID=parent-implement-session
LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env
EOF_ENV
if ! "${SESSION_SETUP[@]}" \
    --prefix claude-review-token-test \
    --skip-preflight \
    --skip-repo-check \
    --caller-env "$UNSAFE_ENV" \
    --write-session-env "$UNSAFE_REVIEW_ENV" \
    >/dev/null 2>"$UNSAFE_ERR"; then
    fail "session-setup exited non-zero for unsafe LARCH_TIMING_LEDGER"
fi
unsafe_timing_ledger=$("${READ_KEY[@]}" --file "$UNSAFE_REVIEW_ENV" --key LARCH_TIMING_LEDGER --default "")
[[ -z "$unsafe_timing_ledger" ]] || fail "unsafe LARCH_TIMING_LEDGER was written to review session-env"
grep -Fq "session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)" "$UNSAFE_ERR" \
    || fail "unsafe LARCH_TIMING_LEDGER warning missing"

CORE_STUB="$TMP/review-core-stub.sh"
cat > "$CORE_STUB" <<'EOF_CORE'
#!/usr/bin/env bash
set -euo pipefail
: "${CORE_CAPTURE_FILE:?}"
printf 'REVIEW_CORE_ARGV' >> "$CORE_CAPTURE_FILE"
printf ' %q' "$@" >> "$CORE_CAPTURE_FILE"
printf '\n' >> "$CORE_CAPTURE_FILE"
out=""
session_env=""
round="1"
panel=""
tier=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) out="$2"; shift 2 ;;
        --session-env-path) session_env="$2"; shift 2 ;;
        --round-num) round="$2"; shift 2 ;;
        --panel) panel="$2"; shift 2 ;;
        --tier) tier="$2"; shift 2 ;;
        --mode|--diff-file|--plan-file|--feature-file|--run-id|--commit-count|--dynamic-archetypes|--codex-available|--cursor-available|--escalated-round|--prune-ledger|--site) shift 2 ;;
        *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
    esac
done
case "$tier" in
    TRIVIAL) panel_shape="singles"; effective_cap="2" ;;
    MODERATE) panel_shape="pairs"; effective_cap="2" ;;
    HARD) panel_shape="pairs"; effective_cap="2" ;;
    *) panel_shape="unknown"; effective_cap="0" ;;
esac
mkdir -p "$out"
printf 'SESSION_ENV_PATH=%s\n' "$session_env" >> "$CORE_CAPTURE_FILE"
printf 'PANEL_ARG=%s\n' "$panel" >> "$CORE_CAPTURE_FILE"
printf 'TIER_ARG=%s\n' "$tier" >> "$CORE_CAPTURE_FILE"
printf 'ROUND_ARG=%s\n' "$round" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_TOKEN_SESSION_ID=%s\n' "${LARCH_TOKEN_SESSION_ID:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_CLAUDE_SOURCE_FILE=%s\n' "${LARCH_CLAUDE_SOURCE_FILE:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_TIMING_LEDGER=%s\n' "${LARCH_TIMING_LEDGER:-}" >> "$CORE_CAPTURE_FILE"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/oos-accepted-review.md"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=%s\nPANEL_TIER=%s\nEFFECTIVE_ROUND_CAP=%s\n' "$round" "$out" "$out" "$panel_shape" "$tier" "$effective_cap"
EOF_CORE
chmod +x "$CORE_STUB"

IMPLEMENT_TMPDIR="$TMP/claude-implement-token-test"
mkdir -p "$IMPLEMENT_TMPDIR"
cp "$REVIEW_ENV" "$IMPLEMENT_TMPDIR/session-env.sh"
printf 'RUN_ID=token-test-run\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n' >> "$IMPLEMENT_TMPDIR/session-env.sh"
printf 'plan\n' > "$IMPLEMENT_TMPDIR/plan.txt"
printf 'feature\n' > "$IMPLEMENT_TMPDIR/feature-description.txt"
CORE_CAPTURE="$TMP/review-core-capture.env"
export CORE_CAPTURE_FILE="$CORE_CAPTURE"
set +e
LARCH_TOKEN_SESSION_ID="$token_session_id" \
    LARCH_CLAUDE_SOURCE_FILE="$claude_source_file" \
    LARCH_TIMING_LEDGER="$timing_ledger" \
    LARCH_TEST_REVIEW_CORE_OVERRIDE=1 \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$CORE_STUB" \
    "${REVIEW_AND_FIX[@]}" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" \
        --mode single \
        --round-num 1 \
        --session-env-path "$IMPLEMENT_TMPDIR/session-env.sh" \
        --codex-available false \
        --cursor-available false >/dev/null 2>"$IMPLEMENT_TMPDIR/review-and-fix.err"
rfa=$?
set -e
[[ "$rfa" -eq 0 ]] || {
    echo "review-and-fix rc=$rfa" >&2
    cat "$IMPLEMENT_TMPDIR/review-and-fix.err" >&2 || true
    ls -la "$IMPLEMENT_TMPDIR" >&2 || true
    ls -la "$IMPLEMENT_TMPDIR/round-1" >&2 || true
    cat "$IMPLEMENT_TMPDIR/round-1/review-core.env" >&2 || true
    cat "$CORE_CAPTURE" >&2 || true
    fail "review-and-fix exited $rfa (diagnostics above)"
}

expected_session_env="$(python3 - <<PY
import os
print(os.path.normpath("$IMPLEMENT_TMPDIR/session-env.sh"))
PY
)"
grep -Fq "SESSION_ENV_PATH=$expected_session_env" "$CORE_CAPTURE" \
    || {
        cat "$CORE_CAPTURE" >&2 || true
        fail "review-and-fix did not pass implement session-env path to review-core"
    }
grep -Fq "REVIEW_CORE_ARGV" "$CORE_CAPTURE" \
    || fail "review-core stub did not record argv capture header"
argv_line=$(grep '^REVIEW_CORE_ARGV' "$CORE_CAPTURE" || true)
case "$argv_line" in
    *"--panel"*"hard"*) ;;
    *) fail "review-core argv did not include internal --panel hard (see REVIEW_CORE_ARGV line in capture)" ;;
esac
grep -Fq "LARCH_TOKEN_SESSION_ID=parent-implement-session" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent token session id"
grep -Fq "LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent Claude source file"
grep -Fq "LARCH_TIMING_LEDGER=$TIMING_LEDGER" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent timing ledger"
grep -Fq "PANEL_TIER=MODERATE" "$IMPLEMENT_TMPDIR/round-1/review-core.env" \
    || fail "default review-core env did not carry PANEL_TIER=MODERATE"
grep -Fq "PANEL_SHAPE=pairs" "$IMPLEMENT_TMPDIR/round-1/review-core.env" \
    || fail "default review-core env did not carry MODERATE pair shape"
grep -Fq "EFFECTIVE_ROUND_CAP=2" "$IMPLEMENT_TMPDIR/round-1/review-core.env" \
    || fail "default review-core env did not carry MODERATE cap"

run_difficulty_case() {
    local tier="$1" expected_panel="$2" expected_shape="$3" expected_cap="$4"
    local lower
    lower="$(printf '%s' "$tier" | tr '[:upper:]' '[:lower:]')"
    local case_tmp="$TMP/claude-implement-difficulty-$lower"
    local capture="$TMP/review-core-capture-$lower.env"
    mkdir -p "$case_tmp"
    cp "$REVIEW_ENV" "$case_tmp/session-env.sh"
    printf 'RUN_ID=token-test-run-%s\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n' "$lower" >> "$case_tmp/session-env.sh"
    printf 'plan\n' > "$case_tmp/plan.txt"
    printf 'feature\n' > "$case_tmp/feature-description.txt"
    : > "$capture"
    set +e
    CORE_CAPTURE_FILE="$capture" \
        LARCH_TOKEN_SESSION_ID="$token_session_id" \
        LARCH_CLAUDE_SOURCE_FILE="$claude_source_file" \
        LARCH_TIMING_LEDGER="$timing_ledger" \
        LARCH_TEST_REVIEW_CORE_OVERRIDE=1 \
        REVIEW_AND_FIX_REVIEW_CORE_SH="$CORE_STUB" \
        "${REVIEW_AND_FIX[@]}" \
            --implement-tmpdir "$case_tmp" \
            --mode single \
            --round-num 1 \
            --session-env-path "$case_tmp/session-env.sh" \
            --codex-available false \
            --cursor-available false \
            --difficulty "$tier" >/dev/null 2>"$case_tmp/review-and-fix.err"
    local rc=$?
    set -e
    [[ "$rc" -eq 0 ]] || {
        echo "review-and-fix --difficulty $tier rc=$rc" >&2
        cat "$case_tmp/review-and-fix.err" >&2 || true
        cat "$case_tmp/round-1/review-core.env" >&2 || true
        cat "$capture" >&2 || true
        fail "review-and-fix --difficulty $tier exited $rc"
    }

    local case_argv_line
    case_argv_line=$(grep '^REVIEW_CORE_ARGV' "$capture" || true)
    case "$case_argv_line" in
        *"--panel"*"${expected_panel}"*) ;;
        *) fail "difficulty $tier did not pass --panel $expected_panel to review-core" ;;
    esac
    case "$case_argv_line" in
        *"--tier"*"${tier}"*) ;;
        *) fail "difficulty $tier did not pass --tier $tier to review-core" ;;
    esac
    grep -Fq "PANEL_ARG=$expected_panel" "$capture" \
        || fail "difficulty $tier capture missed PANEL_ARG=$expected_panel"
    grep -Fq "TIER_ARG=$tier" "$capture" \
        || fail "difficulty $tier capture missed TIER_ARG=$tier"
    grep -Fq "PANEL_SHAPE=$expected_shape" "$case_tmp/round-1/review-core.env" \
        || fail "difficulty $tier review-core.env missed PANEL_SHAPE=$expected_shape"
    grep -Fq "PANEL_TIER=$tier" "$case_tmp/round-1/review-core.env" \
        || fail "difficulty $tier review-core.env missed PANEL_TIER=$tier"
    grep -Fq "EFFECTIVE_ROUND_CAP=$expected_cap" "$case_tmp/round-1/review-core.env" \
        || fail "difficulty $tier review-core.env missed EFFECTIVE_ROUND_CAP=$expected_cap"
}

run_difficulty_case TRIVIAL simple singles 2
run_difficulty_case MODERATE hard pairs 2
run_difficulty_case HARD hard pairs 2

echo "PASS: test-implement-review-token-propagation.sh"
