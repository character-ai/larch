#!/usr/bin/env bash
# test-launch-codex-ci.sh — argv contract tests for launch-codex-ci.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-codex-ci-test.XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR_BASE/execution-issues.md"
export IMPLEMENT_TMPDIR="$TMPDIR_BASE"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

PASS=0
FAIL=0
ok() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

assert_fails() {
    local label=$1
    shift
    set +e
    "$REPO_ROOT/scripts/launch-codex-ci.sh" "$@" > "$TMPDIR_BASE/out" 2> "$TMPDIR_BASE/err"
    local rc=$?
    set -e
    if [[ "$rc" == 2 ]]; then ok "$label"; else fail "$label"; cat "$TMPDIR_BASE/err"; fi
}

assert_fails "rejects bad role" --role nope --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo
assert_fails "rejects relative output" --role fix --output relative --run-id 1 --repo owner/repo
assert_fails "rejects unsafe output characters" --role fix --output "$TMPDIR_BASE/out with space" --run-id 1 --repo owner/repo
assert_fails "rejects relative --plan-file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --plan-file relative/plan.txt
assert_fails "rejects conflict-files with .." --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files '../etc/passwd'
assert_fails "rejects conflict-files with invalid characters" --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files 'foo bar'

: >"$TMPDIR_BASE/failure-log-fixture.log"
assert_fails "rejects_failure_log_outside_implement_tmpdir" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log /etc/passwd
assert_fails "rejects_relative_failure_log" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log relative-only.log
assert_fails "rejects_missing_failure_log_file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log "$TMPDIR_BASE/no-such-failure.log"

if grep -q -- '--conflict-files' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --conflict-files"; else fail "script supports --conflict-files"; fi
if grep -q '<<<CONFLICT_PATHS>>>' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "resolve-conflict prompt fences conflict paths"; else fail "resolve-conflict prompt fences conflict paths"; fi
if grep -q -- "--task-kind \"\$TIMING_TASK_KIND\"" "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "uses timing task kind"; else fail "uses timing task kind"; fi
if grep -q 'plan-file' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --plan-file"; else fail "script supports --plan-file"; fi
if grep -q -- '--failure-log' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --failure-log"; else fail "script supports --failure-log"; fi
if grep -q 'Local reproduction invariant' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "fix role prompt carries local reproduction invariant"; else fail "fix role prompt carries local reproduction invariant"; fi
if grep -q 'codex-ci-fix' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then ok "timing allow-list includes codex-ci-fix"; else fail "timing allow-list includes codex-ci-fix"; fi

cat > "$TMPDIR_BASE/token-record" <<'EOF'
TOOL=codex
INPUT=10
OUTPUT=5
CACHE_READ=90
TOTAL=105
RAW=codex_ci_fix
EOF
"$REPO_ROOT/scripts/append-token-record.sh" --input "$TMPDIR_BASE/token-record" --tmpdir "$TMPDIR_BASE"
if grep -q '"tool":"codex"' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"input":10' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"cache_read":90' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"output":5' "$TMPDIR_BASE/token-report.ndjson"; then
    ok "append-token-record normalizes codex per-bucket sidecar"
else
    fail "append-token-record normalizes codex per-bucket sidecar"
fi

stub_bin="$TMPDIR_BASE/ci-fix-stub-bin"
mkdir -p "$stub_bin"
cat > "$stub_bin/codex" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_bin/codex"
OUT_FIX="$TMPDIR_BASE/ci-fix-prompt-fix"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_FIX" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_FIX}.prompt" 2>/dev/null; then
    ok "fix role prompt includes topology.tsv sentinel"
else
    fail "fix role prompt includes topology.tsv sentinel"
fi
if grep -qF 'persistent interactive subprocess' "${OUT_FIX}.prompt" 2>/dev/null; then
    ok "fix-role prompt prohibits persistent interactive subprocesses (issue #2991)"
else
    fail "fix-role prompt prohibits persistent interactive subprocesses (issue #2991)"
fi
for role in resolve-conflict bump-classify changelog-draft; do
    OUT_NF="$TMPDIR_BASE/ci-fix-prompt-$role"
    case "$role" in
        resolve-conflict)
            (cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
                bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role "$role" --output "$OUT_NF" --run-id r1 --repo owner/repo \
                --conflict-files README.md --timeout 60) >/dev/null 2>&1 || true
            ;;
        *)
            (cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
                bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role "$role" --output "$OUT_NF" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
            ;;
    esac
    if grep -qF 'topology.tsv' "${OUT_NF}.prompt" 2>/dev/null; then
        fail "non-fix role $role must not include topology.tsv"
    else
        ok "non-fix role $role omits topology.tsv"
    fi
done

runtime_bin="$TMPDIR_BASE/ci-runtime-bin"
mkdir -p "$runtime_bin"
runtime_argv="$TMPDIR_BASE/ci-runtime-argv.txt"

cat > "$runtime_bin/codex" <<EOF
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
: > "$runtime_argv"
for arg in "\$@"; do
    printf '%s\n' "\$arg" >> "$runtime_argv"
    if [[ "\$last" == "--output-last-message" ]]; then output_path="\$arg"; fi
    last="\$arg"
done
[[ -n "\$output_path" ]] || exit 9
printf 'ci fix transcript\n' > "\$output_path"
printf '{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}\n'
EOF
chmod +x "$runtime_bin/codex"

OUT_SUCCESS="$TMPDIR_BASE/ci-runtime-success"
(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_SUCCESS" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1
if grep -q '^TOOL=codex$' "${OUT_SUCCESS}.token-record" \
    && grep -q '^INPUT=100$' "${OUT_SUCCESS}.token-record" \
    && grep -q '^CACHE_READ=900$' "${OUT_SUCCESS}.token-record" \
    && grep -q '^OUTPUT=50$' "${OUT_SUCCESS}.token-record" \
    && grep -q '^TOTAL=1050$' "${OUT_SUCCESS}.token-record" \
    && grep -q '^RAW=codex_ci_fix$' "${OUT_SUCCESS}.token-record"; then
    ok "runtime success writes per-bucket codex token-record"
else
    fail "runtime success writes per-bucket codex token-record: $(cat "${OUT_SUCCESS}.token-record" 2>/dev/null)"
fi
rm -f "$TMPDIR_BASE/token-report.ndjson"
"$REPO_ROOT/scripts/append-token-record.sh" --input "${OUT_SUCCESS}.token-record" --tmpdir "$TMPDIR_BASE"
if grep -q '"tool":"codex"' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"input":100' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"cache_read":900' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"output":50' "$TMPDIR_BASE/token-report.ndjson" \
    && grep -q '"total":1050' "$TMPDIR_BASE/token-report.ndjson"; then
    ok "runtime success appends per-bucket codex ledger row"
else
    fail "runtime success appends per-bucket codex ledger row: $(cat "$TMPDIR_BASE/token-report.ndjson" 2>/dev/null)"
fi
if grep -qx -- '--json' "$runtime_argv" 2>/dev/null; then
    ok "runtime success argv includes --json"
else
    fail "runtime success argv includes --json: $(cat "$runtime_argv" 2>/dev/null)"
fi

cat > "$runtime_bin/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'ci fix transcript without usage\n' > "$output_path"
EOF
chmod +x "$runtime_bin/codex"
OUT_EMPTY="$TMPDIR_BASE/ci-runtime-empty"
(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_EMPTY" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1
if [[ ! -s "${OUT_EMPTY}.token-record" ]]; then
    ok "runtime no-usage leaves codex token-record empty"
else
    fail "runtime no-usage leaves codex token-record empty: $(cat "${OUT_EMPTY}.token-record" 2>/dev/null)"
fi
rm -f "$TMPDIR_BASE/token-report.ndjson"
"$REPO_ROOT/scripts/append-token-record.sh" --input "${OUT_EMPTY}.token-record" --tmpdir "$TMPDIR_BASE" >/dev/null 2>&1 || true
if [[ ! -e "$TMPDIR_BASE/token-report.ndjson" ]] || ! grep -q '"tool":"codex"' "$TMPDIR_BASE/token-report.ndjson"; then
    ok "empty codex token-record appends no ledger row"
else
    fail "empty codex token-record should append no ledger row: $(cat "$TMPDIR_BASE/token-report.ndjson" 2>/dev/null)"
fi

cat > "$runtime_bin/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'ci fix transcript schema drift\n' > "$output_path"
printf '{"type":"token_usage","input_tokens":"abc","cached_input_tokens":0,"output_tokens":1}\n'
EOF
chmod +x "$runtime_bin/codex"
OUT_DRIFT="$TMPDIR_BASE/ci-runtime-drift"
(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_DRIFT" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1
if grep -q 'parse-codex-usage.sh: jq failed' "${OUT_DRIFT}.sidecar" 2>/dev/null; then
    ok "runtime schema drift appends parse diagnostic to sidecar"
else
    fail "runtime schema drift appends parse diagnostic to sidecar: $(cat "${OUT_DRIFT}.sidecar" 2>/dev/null)"
fi
if [[ ! -s "${OUT_DRIFT}.token-record" ]]; then
    ok "runtime schema drift leaves codex token-record empty"
else
    fail "runtime schema drift leaves codex token-record empty: $(cat "${OUT_DRIFT}.token-record" 2>/dev/null)"
fi

cat > "$runtime_bin/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'ci fix transcript failed with usage\n' > "$output_path"
printf '{"type":"token_usage","input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}\n'
exit 1
EOF
chmod +x "$runtime_bin/codex"
OUT_FAILED="$TMPDIR_BASE/ci-runtime-failed"
set +e
(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_FAILED" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1
failed_rc=$?
set -e
if [[ "$failed_rc" == "0" ]] \
    && grep -q '^TOOL=codex$' "${OUT_FAILED}.token-record" \
    && grep -q '^INPUT=777$' "${OUT_FAILED}.token-record" \
    && grep -q '^CACHE_READ=7000$' "${OUT_FAILED}.token-record" \
    && grep -q '^OUTPUT=222$' "${OUT_FAILED}.token-record" \
    && grep -q '^TOTAL=7999$' "${OUT_FAILED}.token-record" \
    && grep -q '^RAW=codex_ci_fix$' "${OUT_FAILED}.token-record"; then
    ok "failed runtime still writes per-bucket codex token-record when usage parses"
else
    fail "failed runtime should still write per-bucket codex token-record when usage parses: rc=$failed_rc token-record=$(cat "${OUT_FAILED}.token-record" 2>/dev/null)"
fi

cat > "$runtime_bin/codex" <<'EOF'
#!/usr/bin/env bash
printf 'Error: not logged in\n' >&2
exit 7
EOF
chmod +x "$runtime_bin/codex"
OUT_AUTH="$TMPDIR_BASE/ci-runtime-auth"
set +e
auth_out=$(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_EXTERNAL_AUTH_RETRIES=1 LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_AUTH" --run-id r1 --repo owner/repo --timeout 60 2>/dev/null)
auth_rc=$?
set -e
if [[ "$auth_rc" == "0" ]] && [[ "$auth_out" == *"LAUNCHER_FAILURE_REASON=auth"* ]] && grep -q 'not logged in' "${OUT_AUTH}.sidecar"; then
    ok "stderr-routed auth failure remains classified from sidecar"
else
    fail "stderr-routed auth failure classification unexpected rc=$auth_rc out=$auth_out sidecar=$(cat "${OUT_AUTH}.sidecar" 2>/dev/null)"
fi

# #3390: codex exec --json reports a usage limit on its stdout events stream
# (→ ${OUTPUT}.events.jsonl), not the stderr sidecar or the --output-last-message
# file. The launcher mirrors that signal into the sidecar before classifying, so
# external_classify_launch_failure reports `health`/`quota` (which takes
# precedence over the {5,7} health-probe heuristic) instead of a generic
# non-auth/health-probe failure.
cat > "$runtime_bin/codex" <<'EOF'
#!/usr/bin/env bash
# Usage-limit events on STDOUT only; empty stderr; no --output-last-message write.
printf '{"type":"error","message":"hit your usage limit; try again at Jun 7th, 2026 8:22 AM"}\n'
printf '{"type":"turn.failed","error":{"message":"hit your usage limit"}}\n'
exit 7
EOF
chmod +x "$runtime_bin/codex"
OUT_QUOTA="$TMPDIR_BASE/ci-runtime-quota"
set +e
quota_out=$(cd "$REPO_ROOT" && PATH="$runtime_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    LARCH_EXTERNAL_AUTH_RETRIES=1 LARCH_CODEX_MODEL=stub-model RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_QUOTA" --run-id r1 --repo owner/repo --timeout 60 2>/dev/null)
quota_rc=$?
set -e
if [[ "$quota_rc" == "0" ]] \
    && [[ "$quota_out" == *"LAUNCHER_FAILURE_CLASS=health"* ]] \
    && [[ "$quota_out" == *"LAUNCHER_FAILURE_REASON=quota"* ]] \
    && grep -q 'usage limit' "${OUT_QUOTA}.events.jsonl" \
    && grep -q 'codex exec --json events stream' "${OUT_QUOTA}.sidecar"; then
    ok "events-stream usage limit mirrors into the sidecar and classifies as quota"
else
    fail "events-stream quota classification unexpected rc=$quota_rc out=$quota_out events=$(cat "${OUT_QUOTA}.events.jsonl" 2>/dev/null) sidecar=$(cat "${OUT_QUOTA}.sidecar" 2>/dev/null)"
fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-codex-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-codex-ci: $PASS pass(es)"
