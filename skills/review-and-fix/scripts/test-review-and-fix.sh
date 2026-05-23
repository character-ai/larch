#!/usr/bin/env bash
# Regression harness for review-and-fix.sh.

set -euo pipefail

# Do not inherit a parent larch quiet-session FD map (e.g. Cursor agent shell);
# stale LARCH_QUIET_BREADCRUMB_FD breaks emit_breadcrumb with EBADF in children.
unset LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_BREADCRUMBS LARCH_QUIET_PID \
    LARCH_QUIET_ACTIVE LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG 2>/dev/null || true

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-review-and-fix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

SECTION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --section)
            [[ $# -ge 2 ]] || {
                printf 'ERROR: --section requires a value\n' >&2
                exit 1
            }
            SECTION="$2"
            shift 2
            ;;
        *)
            printf 'ERROR: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done
if [[ -n "$SECTION" ]]; then
    case "$SECTION" in
        dispatch|convergence) ;;
        *)
            printf 'ERROR: unknown --section: %s\n' "$SECTION" >&2
            exit 1
            ;;
    esac
fi
section_runs() {
    [[ -z "$SECTION" || "$SECTION" == "$1" ]]
}

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

pass() {
    echo "ok: $1"
}

cat > "$TMP/run-external-agent-stub.sh" <<'EOF_AGENT'
#!/usr/bin/env bash
set -euo pipefail
tool=""
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) tool="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --timeout) shift 2 ;;
    --capture-stdout) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$output")"
if [[ "$tool" == "cursor" ]]; then
  joined=" $* "
  [[ "${1:-}" == "cursor" ]] || { printf 'bad cursor argv: %s\n' "$*" > "$output"; exit 1; }
  [[ "${2:-}" == "agent" ]] || { printf 'bad cursor argv: %s\n' "$*" > "$output"; exit 1; }
  [[ "${3:-}" == "-p" ]] || { printf 'bad cursor argv: %s\n' "$*" > "$output"; exit 1; }
  [[ "$joined" == *" --trust "* ]] || { printf 'missing --trust: %s\n' "$*" > "$output"; exit 1; }
  [[ "$joined" == *" --workspace "* ]] || { printf 'missing --workspace: %s\n' "$*" > "$output"; exit 1; }
  [[ "$joined" != *" cursor-agent "* ]] || { printf 'old cursor binary used: %s\n' "$*" > "$output"; exit 1; }
  [[ "$joined" != *" --print "* ]] || { printf 'old cursor flag used: %s\n' "$*" > "$output"; exit 1; }
  [[ "$joined" != *" --prompt "* ]] || { printf 'old cursor flag used: %s\n' "$*" > "$output"; exit 1; }
fi
case "${TEST_AGENT_BEHAVIOR:-codex-success}:$tool" in
  codex-success:codex)
    printf 'modified by codex stub\n' >> src/main.py
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  cursor-success:cursor)
    printf 'modified by cursor stub\n' >> src/main.py
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  codex-no-changes:codex)
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  claude-success:codex|claude-success:cursor)
    printf 'failed\n' > "$output"
    exit 1
    ;;
  all-fail:codex|all-fail:cursor)
    printf 'failed\n' > "$output"
    exit 1
    ;;
  submodule-violation:codex)
    printf 'changed by coder\n' > vendor/lib/file.txt
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  submodule-untracked-violation:codex)
    printf 'created by coder\n' > vendor/lib/new.txt
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  *)
    printf 'failed\n' > "$output"
    exit 1
    ;;
esac
EOF_AGENT
chmod +x "$TMP/run-external-agent-stub.sh"

cat > "$TMP/review-core-stub.sh" <<'EOF_CORE'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/findings.md"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
case "${TEST_CORE_STATUS:-fix-required}" in
  fix-required)
    cat > "$out/accepted-findings.md" <<'EOF_FINDING'
### FINDING_1: Stub finding
- **Location**: src/main.py
- **Concern**: Stub concern.
- **Suggested revision**: Stub fix.
EOF_FINDING
    cat > "$out/oos-accepted-review.md" <<'EOF_OOS'
### OOS_1: Stub follow-up
Description: deferred work
EOF_OOS
    printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
  submodule-finding)
    cat > "$out/accepted-findings.md" <<'EOF_FINDING'
### FINDING_1: Stub submodule finding
- **Location**: vendor/lib/Cargo.toml
- **Concern**: Stub concern.
- **Suggested revision**: Stub fix.
EOF_FINDING
    printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
  main-agent-vote-required)
    cat > "$out/findings.md" <<'EOF_FINDING'
### FINDING_1: Stub finding needing adjudication
- **Location**: src/main.py
- **Concern**: Stub concern.
- **Suggested revision**: Stub fix.
EOF_FINDING
    printf 'REVIEW_CORE_STATUS=main-agent-vote-required\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nFINDINGS_FILE=%s/findings.md\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out" "$out"
    ;;
  tally-fidelity)
    cat > "$out/review-round-summary.md" <<'EOF_SUMMARY'
# Review Round 1

- Mode: `diff`
- 1 accepted, 4 rejected (0 exonerated)
EOF_SUMMARY
    cat > "$out/accepted-findings.md" <<'EOF_ACCEPTED'
### FINDING_1: First accepted
- **Location**: src/main.py
- **Concern**: First concern quoting [code-review/accepted] should not inflate the derived tally.
- **Suggested revision**: First fix.

### FINDING_2: Second accepted
- **Location**: src/main.py
- **Concern**: Second concern.
- **Suggested revision**: Second fix.

### FINDING_3: Third accepted
- **Location**: src/main.py
- **Concern**: Third concern.
- **Suggested revision**: Third fix.
EOF_ACCEPTED
    cat > "$out/rejected-findings.md" <<'EOF_REJECTED'
### [Code Review] Cursor-Quality

**Finding**: First rejected finding mentioning [code-review/rejected] in prose only.
**Reason not implemented**: Fixture.

### [Code Review] Codex-Quality

**Finding**: Second rejected finding.
**Reason not implemented**: Fixture.
EOF_REJECTED
    printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=4\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
  aggregator-validation-exhausted)
    printf 'REVIEW_CORE_STATUS=aggregator-validation-exhausted\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    exit 2
    ;;
  *)
    printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
esac
EOF_CORE
chmod +x "$TMP/review-core-stub.sh"

make_work_repo() {
    local dir="$1"
    mkdir -p "$dir/src"
    git -C "$dir" init -q
    git -C "$dir" config user.email "test@example.com"
    git -C "$dir" config user.name "Test User"
    git -C "$dir" config commit.gpgsign false
    printf 'original\n' > "$dir/src/main.py"
    # Production-equivalent: IMPLEMENT_TMPDIR lives outside the repo. In the
    # harness we keep it under the work tree for convenience, so .gitignore
    # prevents `git add -A` (from the per-round commit step) from staging it.
    printf 'implement*/\nreview*/\n' > "$dir/.gitignore"
    git -C "$dir" add src/main.py .gitignore
    git -C "$dir" commit -qm init
}

run_review_and_fix() {
    local work="$1"; shift
    (
        cd "$work"
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        CURSOR_API_KEY=test-cursor-key \
        REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
        REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
        REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="${REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH:-$REPO_ROOT/scripts/scrub-submodule-paths.sh}" \
        "$SCRIPT" "$@"
    )
}

if section_runs dispatch; then
work_agg_exhaust="$TMP/agg-validation-exhausted-prop"
make_work_repo "$work_agg_exhaust"
impl_agg="$work_agg_exhaust/implement"
mkdir -p "$impl_agg"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$impl_agg/session-env.sh"
set +e
out_agg=$(TEST_CORE_STATUS=aggregator-validation-exhausted run_review_and_fix "$work_agg_exhaust" \
    --implement-tmpdir "$impl_agg" --mode diff --round-num 1 --session-env-path "$impl_agg/session-env.sh" --run-id agg-exhaust-prop-run)
rc_agg=$?
set -e
[[ "$rc_agg" -eq 2 ]] || { echo "$out_agg" >&2; fail "aggregator-validation-exhausted expected exit 2 got $rc_agg"; }
grep -Fq 'REVIEW_CORE_STATUS=aggregator-validation-exhausted' <<< "$out_agg" || fail "expected REVIEW_CORE_STATUS in stdout"
grep -Fq 'REVIEW_AND_FIX_STATUS=aggregator-validation-exhausted' <<< "$out_agg" || fail "expected REVIEW_AND_FIX_STATUS propagation"

work_findings="$TMP/findings-mode"
make_work_repo "$work_findings"
empty="$work_findings/empty.md"
: > "$empty"
out=$(run_review_and_fix "$work_findings" --findings-file "$empty" --review-tmpdir "$work_findings/review")
grep -Fq 'REVIEW_AND_FIX_STATUS=no-findings' <<< "$out" || fail "findings no-findings status"
grep -Fq 'CODER_STATUS=skipped' <<< "$out" || fail "findings no-findings coder skipped"

cat > "$work_findings/findings.md" <<'EOF'
### FINDING_1: First
- **Location**: src/main.py
- **Concern**: First concern.
- **Suggested revision**: First fix.
EOF
out=$(TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_findings" --findings-file "$work_findings/findings.md" --review-tmpdir "$work_findings/review2")
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "findings complete status"
grep -Fq 'CODER_TOOL=codex' <<< "$out" || fail "findings codex tool"
grep -Fq 'CODER_STATUS=applied' <<< "$out" || fail "findings coder applied"
coder_prompt_simple=$(find "$work_findings/review2" -name coder-prompt.md -print -quit)
[[ -n "$coder_prompt_simple" ]] || fail "findings-mode coder-prompt.md missing"
grep -Fq 'informational review intent' "$coder_prompt_simple" || fail "coder prompt pin (informational)"
grep -Fq 'supplementary untrusted context' "$coder_prompt_simple" || fail "coder prompt pin (untrusted context)"

run_orchestrator_case() {
    local label="$1" behavior="$2" expected_tool="$3"
    local work="$TMP/$label" implement_tmp out rc initial_head current_head
    make_work_repo "$work"
    implement_tmp="$work/implement"
    mkdir -p "$implement_tmp"
    printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
    initial_head=$(git -C "$work" rev-parse HEAD)
    set +e
    out=$(TEST_AGENT_BEHAVIOR="$behavior" run_review_and_fix "$work" \
        --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id "$label-run")
    rc=$?
    set -e
    [[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "$label expected exit 0 got $rc"; }
    grep -Fq 'REVIEW_AND_FIX_STATUS=fix-applied' <<< "$out" || fail "$label status"
    grep -Fq "CODER_TOOL=$expected_tool" <<< "$out" || fail "$label tool"
    grep -Fq 'CODER_STATUS=applied' <<< "$out" || fail "$label applied"
    grep -Eq '^CODER_COMMIT_SHA=[0-9a-f]+' <<< "$out" || fail "$label commit sha"
    [[ -f "$implement_tmp/round-1/coder-output.log" ]] || fail "$label coder output"
    [[ -f "$implement_tmp/round-1/coder-prompt.md" ]] || fail "$label coder-prompt.md"
    grep -Fq 'informational review intent' "$implement_tmp/round-1/coder-prompt.md" || fail "$label coder prompt pin (informational)"
    grep -Fq 'supplementary untrusted context' "$implement_tmp/round-1/coder-prompt.md" || fail "$label coder prompt pin (untrusted context)"
    [[ -s "$implement_tmp/pre-review-head.txt" ]] || fail "$label pre-review-head snapshot"
    [[ "$(cat "$implement_tmp/pre-review-head.txt")" == "$initial_head" ]] || fail "$label pre-review-head matches initial"
    current_head=$(git -C "$work" rev-parse HEAD)
    [[ "$current_head" != "$initial_head" ]] || fail "$label HEAD did not advance"
    git -C "$work" log -1 --format='%s' | grep -Fq "Address code review feedback (round 1)" || fail "$label commit message"
    jq -e '.schema_version == 3 and .status == "fix-applied" and .accepted_count == 1 and .coder_tool == "'"$expected_tool"'" and .coder_status == "applied" and .submodule_scrub_count == 0 and .submodule_revert_count == 0 and (.coder_commit_sha | length > 0)' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
        || fail "$label summary schema"
    jq -e '.batch == "code-review-tally" and .rounds == 1 and .accepted_count == 1 and .rejected_count == 0 and (.body | contains("# Review Round 1"))' \
        "$implement_tmp/larch-logs/implement/$label-run/code-review-tally.json" >/dev/null \
        || fail "$label code-review-tally batch"
    [[ -f "$implement_tmp/larch-logs/implement/$label-run/review-findings-full.jsonl" ]] || fail "$label review-findings-full batch"
    [[ -s "$implement_tmp/accumulated-oos.jsonl" ]] || fail "$label oos jsonl"
    [[ -s "$implement_tmp/oos-accepted-review.md" ]] || fail "$label oos markdown"
}

run_orchestrator_case codex-case codex-success codex
run_orchestrator_case cursor-case cursor-success cursor

cat > "$TMP/review-core-capture-dynamic-stub.sh" <<'EOF_CORE_DYNAMIC'
#!/usr/bin/env bash
set -euo pipefail
out=""
dynamic=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --dynamic-archetypes) dynamic="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
printf 'DYNAMIC_ARCHETYPES=%s\n' "$dynamic" > "${CAPTURE_DYNAMIC_FILE:?}"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_DYNAMIC
chmod +x "$TMP/review-core-capture-dynamic-stub.sh"
work_empty_env="$TMP/empty-dynamic-env"
make_work_repo "$work_empty_env"
implement_tmp="$work_empty_env/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\nLARCH_DYNAMIC_ARCHETYPES_MAX=3\n' > "$implement_tmp/session-env.sh"
capture_dynamic="$TMP/review-core-dynamic.env"
set +e
out=$(
    cd "$work_empty_env" && \
    CAPTURE_DYNAMIC_FILE="$capture_dynamic" \
    LARCH_DYNAMIC_ARCHETYPES_MAX='' \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-capture-dynamic-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="${REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH:-$REPO_ROOT/scripts/scrub-submodule-paths.sh}" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id empty-env-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "empty dynamic env expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "empty dynamic env status"
grep -Fq 'DYNAMIC_ARCHETYPES=3' "$capture_dynamic" || fail "empty dynamic env should fall through to session-env dynamic cap"

work_no_changes="$TMP/no-changes"
make_work_repo "$work_no_changes"
implement_tmp="$work_no_changes/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
initial_head=$(git -C "$work_no_changes" rev-parse HEAD)
set +e
out=$(TEST_AGENT_BEHAVIOR=codex-no-changes run_review_and_fix "$work_no_changes" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id no-changes-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "no-changes expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=no-changes' <<< "$out" || fail "no-changes status"
grep -Fq 'CODER_STATUS=no-changes' <<< "$out" || fail "no-changes coder status"
if grep -q '^CODER_COMMIT_SHA=' <<< "$out"; then
    fail "no-changes must not emit CODER_COMMIT_SHA"
fi
[[ "$(git -C "$work_no_changes" rev-parse HEAD)" == "$initial_head" ]] || fail "no-changes must not advance HEAD"
jq -e '.schema_version == 3 and .status == "no-changes" and .coder_status == "no-changes" and .coder_commit_sha == ""' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
    || fail "no-changes summary schema"

work_main_agent="$TMP/main-agent-required"
make_work_repo "$work_main_agent"
implement_tmp="$work_main_agent/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=main-agent-vote-required run_review_and_fix "$work_main_agent" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id main-agent-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "main-agent required expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=main-agent-vote-required' <<< "$out" || fail "main-agent required status"
grep -Fq "FINDINGS_FILE=$implement_tmp/round-1/findings.md" <<< "$out" || fail "main-agent required findings file"
jq -e '.schema_version == 3 and .status == "main-agent-vote-required" and .accepted_count == 0 and .rejected_count == 0' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
    || fail "main-agent required summary"

work_rejected="$TMP/rejected-full"
make_work_repo "$work_rejected"
implement_tmp="$work_rejected/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$TMP/review-core-rejected-stub.sh" <<'EOF_CORE_REJECTED'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
cat > "$out/rejected-findings.md" <<'EOF_REJECTED_SUMMARY'
# Rejected Findings

1:FINDING_9_ACCEPTED=false
EOF_REJECTED_SUMMARY
cat > "$out/rejected-findings-full.md" <<'EOF_REJECTED_FULL'
### [Code Review] Cursor-Security

**Finding**: full rejected review prose
**Reason not implemented**: test fixture
EOF_REJECTED_FULL
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":1}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=1\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_REJECTED
chmod +x "$TMP/review-core-rejected-stub.sh"
out=$(
    cd "$work_rejected" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-rejected-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id rejected-full-run
)
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "rejected-full status"
grep -Fq '## Round 1' "$implement_tmp/rejected-findings.md" || fail "rejected-full run-root missing round header"
grep -Fq 'full rejected review prose' "$implement_tmp/rejected-findings.md" \
    || fail "rejected-full run-root missing preserved rejected prose"
grep -Fq 'full rejected review prose' "$implement_tmp/larch-logs/implement/rejected-full-run/code-review-tally.json" \
    || fail "rejected-full tally missing preserved rejected prose"
grep -Fq 'full rejected review prose' "$implement_tmp/larch-logs/implement/rejected-full-run/review-findings-full.jsonl" \
    || fail "rejected-full findings batch missing preserved rejected prose"

work_rejected_aggregate="$TMP/rejected-aggregate"
make_work_repo "$work_rejected_aggregate"
implement_tmp="$work_rejected_aggregate/implement"
mkdir -p "$implement_tmp/round-1"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$implement_tmp/round-1/rejected-findings-full.md" <<'EOF_AGG_ROUND1'
### [Code Review] Codex-Testing

**Finding**: first round full prose
**Reason not implemented**: test fixture
EOF_AGG_ROUND1
out=$(
    cd "$work_rejected_aggregate" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-rejected-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 --session-env-path "$implement_tmp/session-env.sh" --run-id rejected-aggregate-run
)
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "rejected-aggregate status"
grep -Fq '## Round 1' "$implement_tmp/rejected-findings.md" || fail "rejected-aggregate missing round 1 header"
grep -Fq '## Round 2' "$implement_tmp/rejected-findings.md" || fail "rejected-aggregate missing round 2 header"
grep -Fq 'first round full prose' "$implement_tmp/rejected-findings.md" || fail "rejected-aggregate missing round 1 prose"
grep -Fq 'full rejected review prose' "$implement_tmp/rejected-findings.md" || fail "rejected-aggregate missing round 2 prose"
python3 - "$implement_tmp/rejected-findings.md" <<'PYEOF' || fail "rejected-aggregate round order"
import sys

body = open(sys.argv[1], encoding="utf-8").read()
pos1 = body.find("## Round 1")
pos2 = body.find("## Round 2")
if pos1 == -1 or pos2 == -1 or pos1 >= pos2:
    raise SystemExit(1)
PYEOF

work_rejected_fallback="$TMP/rejected-fallback"
make_work_repo "$work_rejected_fallback"
implement_tmp="$work_rejected_fallback/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$TMP/review-core-rejected-fallback-stub.sh" <<'EOF_CORE_REJECTED_FALLBACK'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
cat > "$out/rejected-findings.md" <<'EOF_REJECTED_SUMMARY'
# Rejected Findings

1:FINDING_9_ACCEPTED=false
EOF_REJECTED_SUMMARY
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":1}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=1\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_REJECTED_FALLBACK
chmod +x "$TMP/review-core-rejected-fallback-stub.sh"
out=$(
    cd "$work_rejected_fallback" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-rejected-fallback-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id rejected-fallback-run
)
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "rejected-fallback status"
if grep -Fq '## Round 1' "$implement_tmp/rejected-findings.md"; then
    fail "rejected-fallback should preserve bare ledger without synthetic round header"
fi
grep -Fq 'FINDING_9_ACCEPTED=false' "$implement_tmp/rejected-findings.md" || fail "rejected-fallback missing bare ledger"

work_tally="$TMP/tally-fidelity"
make_work_repo "$work_tally"
implement_tmp="$work_tally/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=tally-fidelity TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_tally" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id tally-fidelity-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "tally-fidelity expected exit 0 got $rc"; }
jq -e '.accepted_count == 3 and .rejected_count == 2' \
    "$implement_tmp/larch-logs/implement/tally-fidelity-run/code-review-tally.json" >/dev/null \
    || fail "tally-fidelity derived tally counts"
jq -e '.accepted_count == 3 and .rejected_count == 2' \
    "$implement_tmp/review-and-fix-summary.json" >/dev/null \
    || fail "tally-fidelity summary matches composed tally"
grep -Fq 'ACCEPTED_COUNT=1' <<< "$out" || fail "tally-fidelity stdout accepted kv remains per-round"
grep -Fq 'REJECTED_COUNT=4' <<< "$out" || fail "tally-fidelity stdout rejected kv remains per-round"
grep -Fq 'TOTAL_ACCEPTED_COUNT=3' <<< "$out" || fail "tally-fidelity stdout total accepted kv matches composed tally"
grep -Fq 'TOTAL_REJECTED_COUNT=2' <<< "$out" || fail "tally-fidelity stdout total rejected kv matches composed tally"
[[ "$(jq -c 'select(.phase == "code-review" and .outcome == "accepted")' "$implement_tmp/larch-logs/implement/tally-fidelity-run/review-findings-full.jsonl" | wc -l | tr -d ' ')" == "3" ]] \
    || fail "tally-fidelity accepted record count"
grep -Fq -- '1 accepted, 4 rejected (0 exonerated)' "$implement_tmp/round-1/review-round-summary.md" || fail "tally-fidelity fixture summary keeps per-round outcome line"
if grep -Fq -- '- Accepted findings:' "$implement_tmp/larch-logs/implement/tally-fidelity-run/code-review-tally.json"; then
    fail "tally-fidelity tally body must omit stale per-round count lines"
fi

cat > "$TMP/compose-review-findings-fail-stub.sh" <<'EOF_COMPOSE_FAIL'
#!/usr/bin/env bash
exit 2
EOF_COMPOSE_FAIL
chmod +x "$TMP/compose-review-findings-fail-stub.sh"
work_compose_fail="$TMP/compose-fail"
make_work_repo "$work_compose_fail"
implement_tmp="$work_compose_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(LARCH_QUIET_BREADCRUMBS=1 REVIEW_AND_FIX_COMPOSE_REVIEW_FINDINGS_SH="$TMP/compose-review-findings-fail-stub.sh" TEST_CORE_STATUS=zero run_review_and_fix "$work_compose_fail" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id compose-fail-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "compose-fail expected exit 0 got $rc"; }
grep -Fq 'failed to compose review findings for summary derivation' <<< "$out" || fail "compose-fail summary warning breadcrumb"
[[ ! -f "$implement_tmp/larch-logs/implement/compose-fail-run/code-review-tally.json" ]] || fail "compose-fail must skip tally batch write"
[[ ! -f "$implement_tmp/larch-logs/implement/compose-fail-run/review-findings-full.jsonl" ]] || fail "compose-fail must skip findings batch write"

work_claude="$TMP/claude-removed"
make_work_repo "$work_claude"
implement_tmp="$work_claude/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=claude-success run_review_and_fix "$work_claude" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "claude removed expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "claude removed status"
grep -Fq 'CODER_TOOL=none' <<< "$out" || fail "claude removed tool"
grep -Fq 'claude-subagent' "$implement_tmp/review-and-fix-summary.json" && fail "claude removed summary must not report claude-subagent"

work_fail="$TMP/all-fail"
make_work_repo "$work_fail"
implement_tmp="$work_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=all-fail run_review_and_fix "$work_fail" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "all-fail expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "all-fail status"
grep -Fq 'CODER_TOOL=none' <<< "$out" || fail "all-fail tool"
grep -Fq 'CODER_STATUS=failed' <<< "$out" || fail "all-fail coder status"

work_fail_early="$TMP/all-fail-early-breadcrumb"
make_work_repo "$work_fail_early"
implement_tmp="$work_fail_early/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(LARCH_QUIET_BREADCRUMBS=1 CLAUDE_PLUGIN_OPTION_CURSOR_MODEL=' ' TEST_AGENT_BEHAVIOR=all-fail run_review_and_fix "$work_fail_early" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "all-fail early breadcrumb expected exit 2 got $rc"; }
grep -Fq '⚠ review-and-fix: coder dispatch failed (both codex and cursor)' <<< "$out" \
    || fail "all-fail early breadcrumb missing failure breadcrumb"

work_sub="$TMP/submodule-violation"
make_work_repo "$work_sub"
mkdir -p "$work_sub/vendor/lib"
cat > "$work_sub/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
printf 'original submodule content\n' > "$work_sub/vendor/lib/file.txt"
git -C "$work_sub" add .gitmodules vendor/lib/file.txt
git -C "$work_sub" -c user.email=test@example.com -c user.name='Test User' commit -qm submodule-fixture
implement_tmp="$work_sub/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=submodule-violation run_review_and_fix "$work_sub" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "submodule violation expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "submodule violation status"
grep -Fq 'CODER_STATUS=submodule-violation' <<< "$out" || fail "submodule violation coder status"
grep -Fq 'SUBMODULE_REVERT_COUNT=1' <<< "$out" || fail "submodule violation revert count"
grep -Fq 'original submodule content' "$work_sub/vendor/lib/file.txt" || fail "submodule path was not reverted"

work_sub_untracked="$TMP/submodule-untracked-violation"
make_work_repo "$work_sub_untracked"
mkdir -p "$work_sub_untracked/vendor/lib"
cat > "$work_sub_untracked/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
printf 'original submodule content\n' > "$work_sub_untracked/vendor/lib/file.txt"
git -C "$work_sub_untracked" add .gitmodules vendor/lib/file.txt
git -C "$work_sub_untracked" -c user.email=test@example.com -c user.name='Test User' commit -qm submodule-fixture
implement_tmp="$work_sub_untracked/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=submodule-untracked-violation run_review_and_fix "$work_sub_untracked" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "submodule untracked violation expected exit 2 got $rc"; }
grep -Fq 'CODER_STATUS=submodule-violation' <<< "$out" || fail "submodule untracked coder status"
grep -Fq 'SUBMODULE_REVERT_COUNT=1' <<< "$out" || fail "submodule untracked revert count"
[[ ! -e "$work_sub_untracked/vendor/lib/new.txt" ]] || fail "untracked submodule path was not removed"

work_scrubbed="$TMP/scrubbed-out"
make_work_repo "$work_scrubbed"
mkdir -p "$work_scrubbed/vendor/lib"
cat > "$work_scrubbed/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
git -C "$work_scrubbed" add .gitmodules
git -C "$work_scrubbed" -c user.email=test@example.com -c user.name='Test User' commit -qm submodule-config
implement_tmp="$work_scrubbed/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=submodule-finding TEST_AGENT_BEHAVIOR=all-fail run_review_and_fix "$work_scrubbed" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "scrubbed-out expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=in-scope-filtered-out' <<< "$out" || fail "scrubbed-out status"
grep -Fq 'CODER_TOOL=none' <<< "$out" || fail "scrubbed-out tool"
grep -Fq 'CODER_STATUS=skipped' <<< "$out" || fail "scrubbed-out coder skipped"
grep -Fq 'SUBMODULE_SCRUB_COUNT=1' <<< "$out" || fail "scrubbed-out scrub count"

cat > "$TMP/scrub-fails-stub.sh" <<'EOF_SCRUB'
#!/usr/bin/env bash
printf 'SCRUB_OK=false\n'
exit 2
EOF_SCRUB
chmod +x "$TMP/scrub-fails-stub.sh"
work_scrub_fail="$TMP/scrub-fail"
make_work_repo "$work_scrub_fail"
implement_tmp="$work_scrub_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$TMP/scrub-fails-stub.sh" TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_scrub_fail" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "scrub fail expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "scrub fail status"
grep -Fq 'CODER_TOOL=none' <<< "$out" || fail "scrub fail tool"
grep -Fq 'CODER_STATUS=failed' <<< "$out" || fail "scrub fail coder status"

work_zero="$TMP/zero"
make_work_repo "$work_zero"
implement_tmp="$work_zero/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=zero run_review_and_fix "$work_zero" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id zero-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "zero expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "zero status"
jq -e '.schema_version == 3 and .status == "complete" and .coder_status == "skipped"' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
    || fail "zero summary"
jq -e '.batch == "code-review-tally" and .rounds == 1 and .accepted_count == 0 and .rejected_count == 0 and (.body | contains("# Review Round 1"))' \
    "$implement_tmp/larch-logs/implement/zero-run/code-review-tally.json" >/dev/null \
    || fail "zero code-review-tally batch"
[[ -f "$implement_tmp/larch-logs/implement/zero-run/review-findings-full.jsonl" ]] || fail "zero review-findings-full batch"
[[ "$out" != *"LOG_WRITTEN="* ]] || fail "zero flush leaked larch-log writer stdout"

work_sorted="$TMP/sorted-summaries"
make_work_repo "$work_sorted"
implement_tmp="$work_sorted/implement"
mkdir -p "$implement_tmp/round-2" "$implement_tmp/round-10"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
printf '# Review Round 10\nlate round\n' > "$implement_tmp/round-10/review-round-summary.md"
printf '# Review Round 2\nearly round\n' > "$implement_tmp/round-2/review-round-summary.md"
printf '{"schema_version":1,"rounds_completed":10,"accepted_count":0,"rejected_count":0}\n' > "$implement_tmp/round-10/review-summary.json"
set +e
out=$(TEST_CORE_STATUS=zero run_review_and_fix "$work_sorted" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 10 --session-env-path "$implement_tmp/session-env.sh" --run-id sorted-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "sorted summaries expected exit 0 got $rc"; }
python3 - "$implement_tmp/larch-logs/implement/sorted-run/code-review-tally.json" <<'PYEOF' || fail "sorted summaries order"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    body = json.load(fh)["body"]

pos2 = body.find("# Review Round 2")
pos10 = body.find("# Review Round 10")
if pos2 == -1 or pos10 == -1 or pos2 >= pos10:
    raise SystemExit(1)
PYEOF

work_rejected_mix="$TMP/rejected-findings-mixed-rounds"
make_work_repo "$work_rejected_mix"
implement_tmp="$work_rejected_mix/implement"
mkdir -p "$implement_tmp/round-1" "$implement_tmp/round-2"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$implement_tmp/round-1/rejected-findings-full.md" <<'EOF_REJECTED_FULL'
### FINDING_1: Round 1 rejected finding
- **Concern**: Keep full prose when present.
EOF_REJECTED_FULL
cat > "$implement_tmp/round-2/rejected-findings.md" <<'EOF_REJECTED_COMPACT'
### FINDING_2: Round 2 rejected finding
- **Concern**: Keep compact fallback when full detail is absent.
EOF_REJECTED_COMPACT
set +e
out=$(TEST_CORE_STATUS=zero run_review_and_fix "$work_rejected_mix" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 --session-env-path "$implement_tmp/session-env.sh" --run-id rejected-mix-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "mixed rejected aggregate expected exit 0 got $rc"; }
grep -Fq '## Round 1' "$implement_tmp/rejected-findings.md" || fail "mixed rejected aggregate kept round 1 heading"
grep -Fq 'Round 1 rejected finding' "$implement_tmp/rejected-findings.md" || fail "mixed rejected aggregate kept round 1 full detail"
grep -Fq '## Round 2' "$implement_tmp/rejected-findings.md" || fail "mixed rejected aggregate kept round 2 heading"
grep -Fq 'Round 2 rejected finding' "$implement_tmp/rejected-findings.md" || fail "mixed rejected aggregate kept round 2 compact detail"
python3 - "$implement_tmp/rejected-findings.md" <<'PYEOF' || fail "mixed rejected aggregate should strip duplicate top-level heading from compact round body"
import sys

body = open(sys.argv[1], encoding="utf-8").read()
if "# Rejected Findings\n\n# Rejected Findings" in body:
    raise SystemExit(1)
PYEOF
jq -e '.batch == "code-review-tally" and (.body | contains("Round 1 rejected finding")) and (.body | contains("Round 2 rejected finding"))' \
    "$implement_tmp/larch-logs/implement/rejected-mix-run/code-review-tally.json" >/dev/null \
    || fail "mixed rejected aggregate feeds code-review-tally body"

work_rejected_heading_edges="$TMP/rejected-findings-heading-edges"
make_work_repo "$work_rejected_heading_edges"
implement_tmp="$work_rejected_heading_edges/implement"
mkdir -p "$implement_tmp/round-1" "$implement_tmp/round-2" "$implement_tmp/round-3"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$implement_tmp/round-1/rejected-findings-full.md" <<'EOF_REJECTED_FULL'
### FINDING_0: full-detail round keeps aggregate mode enabled
- **Concern**: Preserve full prose when any round emitted the detailed artifact.
EOF_REJECTED_FULL
cat > "$implement_tmp/round-2/rejected-findings.md" <<'EOF_REJECTED_NO_BLANK'
# Rejected Findings
### FINDING_1: compact body without blank separator
- **Concern**: Preserve compact prose when the title is immediately followed by content.
EOF_REJECTED_NO_BLANK
cat > "$implement_tmp/round-3/rejected-findings.md" <<'EOF_REJECTED_LEADING_BLANK'

# Rejected Findings

### FINDING_2: title preceded by a blank line
- **Concern**: Strip only the top-level title block before aggregation.
EOF_REJECTED_LEADING_BLANK
set +e
out=$(TEST_CORE_STATUS=zero run_review_and_fix "$work_rejected_heading_edges" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 4 --session-env-path "$implement_tmp/session-env.sh" --run-id rejected-heading-edges-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "heading-edge rejected aggregate expected exit 0 got $rc"; }
grep -Fq 'compact body without blank separator' "$implement_tmp/rejected-findings.md" \
    || fail "heading-edge rejected aggregate keeps compact body without blank separator"
grep -Fq 'title preceded by a blank line' "$implement_tmp/rejected-findings.md" \
    || fail "heading-edge rejected aggregate keeps body after leading blank"
python3 - "$implement_tmp/rejected-findings.md" <<'PYEOF' || fail "heading-edge rejected aggregate strips duplicate top-level headings"
import sys

body = open(sys.argv[1], encoding="utf-8").read()
if body.count("# Rejected Findings") != 1:
    raise SystemExit(1)
PYEOF

cat > "$TMP/write-tally-fails-stub.sh" <<'EOF_WRITE_TALLY'
#!/usr/bin/env bash
printf 'stub write-tally failure\n' >&2
exit 2
EOF_WRITE_TALLY
chmod +x "$TMP/write-tally-fails-stub.sh"
work_flush_warn="$TMP/flush-warning"
make_work_repo "$work_flush_warn"
implement_tmp="$work_flush_warn/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=zero LARCH_QUIET_BREADCRUMBS=1 REVIEW_AND_FIX_WRITE_TALLY_SH="$TMP/write-tally-fails-stub.sh" run_review_and_fix "$work_flush_warn" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id flush-warning-run 2>&1)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "flush warning expected exit 0 got $rc"; }
grep -Fq 'failed to flush code-review-tally batch' <<< "$out" || fail "flush warning breadcrumb"
grep -Fq 'stub write-tally failure' <<< "$out" || fail "flush warning stderr"

work_skipped="$TMP/skipped-routing"
make_work_repo "$work_skipped"
implement_tmp="$work_skipped/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cat > "$TMP/review-core-skipped-stub.sh" <<'EOF_CORE_SKIPPED'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
cat > "$out/accepted-findings.md" <<'EOF_FINDINGS'
### FINDING_1: Non-security skipped finding
- **Concern**: Keep it public.
- **Suggested revision**: Skip for test.

### FINDING_2: Security skipped finding
- **Concern**: Contains focus-area = security and must stay local.
- **Suggested revision**: Skip for test.
EOF_FINDINGS
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":2,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=2\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_SKIPPED
chmod +x "$TMP/review-core-skipped-stub.sh"
cat > "$work_skipped/implement/round-1-coder.log.seed" <<'EOF_LOG'
SKIPPED: FINDING_1
SKIPPED: FINDING_2
SKIPPED: FINDING_2
SKIPPED: FINDING_999
EOF_LOG
cat > "$TMP/run-external-agent-skipped-stub.sh" <<'EOF_AGENT_SKIPPED'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --timeout) shift 2 ;;
    --capture-stdout) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$output")"
# Mimic a real coder run that applied at least one finding (so CODER_STATUS
# becomes "applied" under the new dirty-tree contract) while also logging
# SKIPPED lines that the SKIPPED-routing logic must classify.
printf 'modified by skipped stub\n' >> src/main.py
cat "$PWD/implement/round-1-coder.log.seed" > "$output"
exit 0
EOF_AGENT_SKIPPED
chmod +x "$TMP/run-external-agent-skipped-stub.sh"
set +e
out=$(
    cd "$work_skipped" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-skipped-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-skipped-stub.sh" \
    REVIEW_AND_FIX_LAUNCH_CLAUDE_SUBPROCESS_SH="$TMP/launch-claude-subprocess-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh"
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "skipped-routing expected exit 0 got $rc"; }
grep -Fq 'SKIPPED_FINDING_COUNT=2' <<< "$out" || fail "skipped-routing count"
grep -Fq 'FIX_COUNT=2' <<< "$out" || fail "skipped-routing fix count"
grep -Fq 'Non-security skipped finding' "$implement_tmp/oos-accepted-review.md" || fail "skipped-routing public skipped finding missing"
if grep -Fq 'Security skipped finding' "$implement_tmp/oos-accepted-review.md"; then
    fail "skipped-routing security finding leaked to public OOS"
fi
grep -Fq 'Security skipped finding' "$implement_tmp/skipped-security-findings.md" || fail "skipped-routing security finding missing from local audit"

mkdir -p "$TMP/fail-python-bin"
cat > "$TMP/fail-python-bin/python3" <<'EOF_PYFAIL'
#!/usr/bin/env bash
exit 1
EOF_PYFAIL
chmod +x "$TMP/fail-python-bin/python3"
work_classifier_fail="$TMP/skipped-classifier-fail"
make_work_repo "$work_classifier_fail"
implement_tmp="$work_classifier_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
cp "$work_skipped/implement/round-1-coder.log.seed" "$implement_tmp/round-1-coder.log.seed"
set +e
out=$(
    cd "$work_classifier_fail" && \
    PATH="$TMP/fail-python-bin:$PATH" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-skipped-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-skipped-stub.sh" \
    REVIEW_AND_FIX_LAUNCH_CLAUDE_SUBPROCESS_SH="$TMP/launch-claude-subprocess-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh"
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "skipped-classifier-fail expected exit 2 got $rc"; }
if [[ -e "$implement_tmp/skipped-security-findings.md" ]]; then
    fail "skipped-classifier-fail should not emit security audit file on classifier failure"
fi

cat > "$TMP/scrub-submodule-paths-drop-one.sh" <<'EOF_SCRUB'
#!/usr/bin/env bash
set -euo pipefail
input=""
output=""
log_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) input="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --log) log_file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
awk '
  /^### FINDING_2:/ { skip=1 }
  /^### FINDING_[0-9]+:/ && !/^### FINDING_2:/ { skip=0 }
  !skip { print }
' "$input" > "$output"
: > "$log_file"
printf 'SCRUB_COUNT=1\n'
EOF_SCRUB
chmod +x "$TMP/scrub-submodule-paths-drop-one.sh"
work_scrub="$TMP/scrub-fix-count"
make_work_repo "$work_scrub"
cat > "$work_scrub/findings.md" <<'EOF_SCRUB_FINDINGS'
### FINDING_1: Keep
- **Location**: src/main.py
- **Concern**: First concern.
- **Suggested revision**: First fix.

### FINDING_2: Drop
- **Location**: vendor/lib/file.txt
- **Concern**: Submodule concern.
- **Suggested revision**: Skip by scrubber.
EOF_SCRUB_FINDINGS
out=$(
    cd "$work_scrub" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_LAUNCH_CLAUDE_SUBPROCESS_SH="$TMP/launch-claude-subprocess-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$TMP/scrub-submodule-paths-drop-one.sh" \
    TEST_AGENT_BEHAVIOR=codex-success \
    "$SCRIPT" --findings-file "$work_scrub/findings.md" --review-tmpdir "$work_scrub/review"
)
grep -Fq 'FIX_COUNT=1' <<< "$out" || fail "findings-mode fix count uses post-scrub count"
grep -Fq 'SUBMODULE_SCRUB_COUNT=1' <<< "$out" || fail "findings-mode scrub count"

cat > "$TMP/larch-log-write-round-fail-stub.sh" <<'EOF_LARCH_LOG_FAIL'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "write-round" ]]; then
  printf 'late write-round failed with sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
  exit 9
fi
printf 'LOG_WRITTEN=true\nLOG_PATH=\nBYTES=0\nSHA256=\nCOMMIT_SHA=\nUNCHANGED=false\n'
EOF_LARCH_LOG_FAIL
chmod +x "$TMP/larch-log-write-round-fail-stub.sh"
work_late_flush="$TMP/late-flush-warning"
make_work_repo "$work_late_flush"
implement_tmp="$work_late_flush/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=codex-success REVIEW_AND_FIX_LARCH_LOG_SH="$TMP/larch-log-write-round-fail-stub.sh" run_review_and_fix "$work_late_flush" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 --session-env-path "$implement_tmp/session-env.sh" --run-id late-flush-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "late flush warning expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=fix-applied' <<< "$out" || fail "late flush warning status"
grep -Fq 'larch-log.sh write-round failed (exit 9' "$implement_tmp/execution-issues.md" || fail "late flush warning execution issue missing"
grep -Fq 'post-coder round 1' "$implement_tmp/execution-issues.md" || fail "late flush warning verdict missing"
if grep -Fq 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' "$implement_tmp/execution-issues.md"; then
    fail "late flush warning should redact stderr"
fi


# Tests 6-7: review-scout-manifest flush from /implement path

cat > "$TMP/review-core-scout-stub.sh" <<'EOF_SCOUT_CORE'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "${1:-}" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/findings.md"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
scout_manifest="$out/scout-round${round}-manifest.json"
yield_tsv="$out/scout-archetype-yield.tsv"
case "${TEST_SCOUT_STATUS:-ok}" in
  ok)
    printf '{"archetypes":["api-contract"]}\n' > "$scout_manifest"
    printf 'archetype\tyield\napi-contract\t1\n' > "$yield_tsv"
    printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\nSCOUT_STATUS=ok\nDYNAMIC_SLOTS=%s\nSCOUT_MANIFEST=%s\nYIELD_TSV_FILE=%s\n' \
        "$round" "$out" "$out" "${TEST_DYNAMIC_SLOTS:-2}" "${TEST_SCOUT_MANIFEST_PATH:-$scout_manifest}" "${TEST_YIELD_TSV_PATH:-$yield_tsv}"
    ;;
  panel-failed)
    printf '{"archetypes":["api-contract"]}\n' > "$scout_manifest"
    printf 'archetype\tyield\napi-contract\t1\n' > "$yield_tsv"
    printf 'REVIEW_CORE_STATUS=panel-failed\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\nSCOUT_STATUS=ok\nDYNAMIC_SLOTS=%s\nSCOUT_MANIFEST=%s\nYIELD_TSV_FILE=%s\n' \
        "$round" "$out" "$out" "${TEST_DYNAMIC_SLOTS:-2}" "${TEST_SCOUT_MANIFEST_PATH:-$scout_manifest}" "${TEST_YIELD_TSV_PATH:-$yield_tsv}"
    exit 2
    ;;
  *)
    printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\nSCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSCOUT_MANIFEST=\nYIELD_TSV_FILE=\n' \
        "$round" "$out" "$out"
    ;;
esac
EOF_SCOUT_CORE
chmod +x "$TMP/review-core-scout-stub.sh"

# Test 6: scout summary committed in /implement when SCOUT_STATUS=ok
work_scout="$TMP/scout-manifest-ok"
make_work_repo "$work_scout"
scout_impl_tmp="$work_scout/implement"
mkdir -p "$scout_impl_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$scout_impl_tmp/session-env.sh"
scout_run_id="scout-run-test-ok"
scout_log_root="$scout_impl_tmp/larch-logs"
(cd "$work_scout" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/larch-log.sh" init \
    --log-root "$scout_log_root" --skill implement --run-id "$scout_run_id" --issue 2356) >/dev/null

set +e
out=$(
    cd "$work_scout" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-scout-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$REPO_ROOT/scripts/scrub-submodule-paths.sh" \
    TEST_SCOUT_STATUS=ok \
    "$SCRIPT" --implement-tmpdir "$scout_impl_tmp" --mode diff \
        --round-num 1 --session-env-path "$scout_impl_tmp/session-env.sh" \
        --run-id "$scout_run_id"
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "scout-ok test expected exit 0 got $rc"; }
scout_batch="$scout_log_root/implement/$scout_run_id/review-scout-manifest.json"
if [[ -f "$scout_batch" ]]; then
    pass "review-scout-manifest.json committed when SCOUT_STATUS=ok"
else
    fail "review-scout-manifest.json must be committed when SCOUT_STATUS=ok (missing: $scout_batch)"
fi
if jq -e '.status == "ok" and .dynamic_slots == 2 and (.manifest_basename | length > 0) and .yield_tsv_basename == "scout-archetype-yield.tsv"' "$scout_batch" >/dev/null 2>&1; then
    pass "review-scout-manifest.json has expected fields (status, dynamic_slots, manifest_basename, yield_tsv_basename)"
else
    fail "review-scout-manifest.json fields wrong: $(cat "$scout_batch" 2>/dev/null)"
fi

# Test 7: panel-failed still flushes review-scout-manifest before exiting nonzero
work_scout_panel_failed="$TMP/scout-manifest-panel-failed"
make_work_repo "$work_scout_panel_failed"
scout_panel_failed_impl_tmp="$work_scout_panel_failed/implement"
mkdir -p "$scout_panel_failed_impl_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$scout_panel_failed_impl_tmp/session-env.sh"
scout_panel_failed_run_id="scout-run-test-panel-failed"
scout_panel_failed_log_root="$scout_panel_failed_impl_tmp/larch-logs"
(cd "$work_scout_panel_failed" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/larch-log.sh" init \
    --log-root "$scout_panel_failed_log_root" --skill implement --run-id "$scout_panel_failed_run_id" --issue 2356) >/dev/null

set +e
out=$(
    cd "$work_scout_panel_failed" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-scout-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$REPO_ROOT/scripts/scrub-submodule-paths.sh" \
    TEST_SCOUT_STATUS=panel-failed \
    "$SCRIPT" --implement-tmpdir "$scout_panel_failed_impl_tmp" --mode diff \
        --round-num 1 --session-env-path "$scout_panel_failed_impl_tmp/session-env.sh" \
        --run-id "$scout_panel_failed_run_id"
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "scout-panel-failed test expected exit 2 got $rc"; }
scout_panel_failed_batch="$scout_panel_failed_log_root/implement/$scout_panel_failed_run_id/review-scout-manifest.json"
if [[ -f "$scout_panel_failed_batch" ]]; then
    pass "review-scout-manifest.json committed before panel-failed exit"
else
    fail "review-scout-manifest.json must be committed before panel-failed exit (missing: $scout_panel_failed_batch)"
fi

# Test 8: no review-scout-manifest.json committed when SCOUT_STATUS=na
work_scout_na="$TMP/scout-manifest-na"
make_work_repo "$work_scout_na"
scout_na_impl_tmp="$work_scout_na/implement"
mkdir -p "$scout_na_impl_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$scout_na_impl_tmp/session-env.sh"
scout_na_run_id="scout-run-test-na"
scout_na_log_root="$scout_na_impl_tmp/larch-logs"
(cd "$work_scout_na" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/larch-log.sh" init \
    --log-root "$scout_na_log_root" --skill implement --run-id "$scout_na_run_id" --issue 2356) >/dev/null

set +e
out=$(
    cd "$work_scout_na" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-scout-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$REPO_ROOT/scripts/scrub-submodule-paths.sh" \
    TEST_SCOUT_STATUS=na \
    "$SCRIPT" --implement-tmpdir "$scout_na_impl_tmp" --mode diff \
        --round-num 1 --session-env-path "$scout_na_impl_tmp/session-env.sh" \
        --run-id "$scout_na_run_id"
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "scout-na test expected exit 0 got $rc"; }
scout_na_batch="$scout_na_log_root/implement/$scout_na_run_id/review-scout-manifest.json"
if [[ ! -f "$scout_na_batch" ]]; then
    pass "review-scout-manifest.json NOT committed when SCOUT_STATUS=na"
else
    fail "review-scout-manifest.json must NOT be committed when SCOUT_STATUS=na"
fi

# Test 9: invalid DYNAMIC_SLOTS logs a warning, clears stale payload, and skips scout manifest flush
work_scout_invalid="$TMP/scout-manifest-invalid"
make_work_repo "$work_scout_invalid"
scout_invalid_impl_tmp="$work_scout_invalid/implement"
mkdir -p "$scout_invalid_impl_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$scout_invalid_impl_tmp/session-env.sh"
scout_invalid_run_id="scout-run-test-invalid"
scout_invalid_log_root="$scout_invalid_impl_tmp/larch-logs"
(cd "$work_scout_invalid" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/larch-log.sh" init \
    --log-root "$scout_invalid_log_root" --skill implement --run-id "$scout_invalid_run_id" --issue 2356) >/dev/null
mkdir -p "$scout_invalid_impl_tmp/round-1"
printf '{"status":"stale","dynamic_slots":99,"manifest_basename":"stale.json","yield_tsv_basename":"stale.tsv"}\n' \
    > "$scout_invalid_impl_tmp/round-1/.scout-payload.json"

set +e
out=$(
    cd "$work_scout_invalid" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-scout-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$REPO_ROOT/scripts/scrub-submodule-paths.sh" \
    TEST_SCOUT_STATUS=ok \
    TEST_DYNAMIC_SLOTS=bogus \
    "$SCRIPT" --implement-tmpdir "$scout_invalid_impl_tmp" --mode diff \
        --round-num 1 --session-env-path "$scout_invalid_impl_tmp/session-env.sh" \
        --run-id "$scout_invalid_run_id"
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "scout-invalid test expected exit 0 got $rc"; }
scout_invalid_batch="$scout_invalid_log_root/implement/$scout_invalid_run_id/review-scout-manifest.json"
if [[ ! -f "$scout_invalid_batch" ]]; then
    pass "review-scout-manifest.json not committed when DYNAMIC_SLOTS is invalid"
else
    fail "review-scout-manifest.json must not be committed with invalid DYNAMIC_SLOTS"
fi
if grep -Fq 'review-scout-manifest payload validation' "$scout_invalid_impl_tmp/execution-issues.md" 2>/dev/null; then
    pass "invalid DYNAMIC_SLOTS warning appended to execution-issues.md"
else
    fail "invalid DYNAMIC_SLOTS warning missing from execution-issues.md"
fi

# Test 10: basename fields come from non-empty KVs even if the files are absent
work_scout_missing_files="$TMP/scout-manifest-missing-files"
make_work_repo "$work_scout_missing_files"
scout_missing_files_impl_tmp="$work_scout_missing_files/implement"
mkdir -p "$scout_missing_files_impl_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$scout_missing_files_impl_tmp/session-env.sh"
scout_missing_files_run_id="scout-run-test-missing-files"
scout_missing_files_log_root="$scout_missing_files_impl_tmp/larch-logs"
(cd "$work_scout_missing_files" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/larch-log.sh" init \
    --log-root "$scout_missing_files_log_root" --skill implement --run-id "$scout_missing_files_run_id" --issue 2356) >/dev/null

set +e
out=$(
    cd "$work_scout_missing_files" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    CURSOR_API_KEY=test-cursor-key \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-scout-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    REVIEW_AND_FIX_SCRUB_SUBMODULE_PATHS_SH="$REPO_ROOT/scripts/scrub-submodule-paths.sh" \
    TEST_SCOUT_STATUS=ok \
    TEST_SCOUT_MANIFEST_PATH="$scout_missing_files_impl_tmp/round-1/not-present/scout-round1-manifest.json" \
    TEST_YIELD_TSV_PATH="$scout_missing_files_impl_tmp/round-1/not-present/scout-archetype-yield.tsv" \
    "$SCRIPT" --implement-tmpdir "$scout_missing_files_impl_tmp" --mode diff \
        --round-num 1 --session-env-path "$scout_missing_files_impl_tmp/session-env.sh" \
        --run-id "$scout_missing_files_run_id"
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "scout-missing-files test expected exit 0 got $rc"; }
scout_missing_files_batch="$scout_missing_files_log_root/implement/$scout_missing_files_run_id/review-scout-manifest.json"
if jq -e '.manifest_basename == "scout-round1-manifest.json" and .yield_tsv_basename == "scout-archetype-yield.tsv"' \
    "$scout_missing_files_batch" >/dev/null 2>&1; then
    pass "review-scout-manifest basenames come from non-empty KVs"
else
    fail "review-scout-manifest basenames should come from non-empty KVs: $(cat "$scout_missing_files_batch" 2>/dev/null)"
fi

fi  # end section: dispatch

if section_runs convergence; then
# ── Convergence and degraded-round tests ────────────────────────────────────

# Helper: stub a prior round by writing its review-core.env with the given accepted count.
write_prior_round() {
    local impl_tmpdir="$1" round="$2" accepted_count="$3" degraded="${4:-false}"
    mkdir -p "$impl_tmpdir/round-${round}"
    printf 'REVIEW_CORE_STATUS=ok\nACCEPTED_COUNT=%s\nREJECTED_COUNT=0\n' "$accepted_count" \
        > "$impl_tmpdir/round-${round}/review-core.env"
    : > "$impl_tmpdir/round-${round}/findings.md"
    printf 'DEGRADED_ROUND=%s\n' "$degraded" > "$impl_tmpdir/round-${round}/review-and-fix.env"
}

# Test 1: Convergence — two small rounds terminate loop.
# Round 2 is small (accepted=2) and round 3 is small (accepted=1) → converged after round 3.
cat > "$TMP/review-core-small-stub.sh" <<'EOF_CORE_SMALL'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=%s\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "${STUB_ACCEPTED:-0}" "$out" "$out"
EOF_CORE_SMALL
chmod +x "$TMP/review-core-small-stub.sh"

work_converge="$TMP/converge-two-small"
make_work_repo "$work_converge"
implement_tmp="$work_converge/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10  # round 1: 10 accepts (not small)
write_prior_round "$implement_tmp" 2 2   # round 2: 2 accepts (small)
set +e
out=$(
    cd "$work_converge" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id converge-two-small-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "converge-two-small expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out" \
    || fail "converge-two-small should emit converged-small-changes (round 3=1 and round 2=2, both ≤3)"
grep -Fq 'DEGRADED_ROUND=false' <<< "$out" || fail "converge-two-small degraded should be false"

# Test 2: Convergence — Important finding blocks early-termination.
# Round 2 has Important finding → loop continues to round 3.
cat > "$TMP/review-core-important-stub.sh" <<'EOF_CORE_IMP'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
# Write canonical Important finding heading into findings.md to block convergence.
printf '### FINDING_1: **Important** severity finding here\n' > "$out/findings.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_IMP
chmod +x "$TMP/review-core-important-stub.sh"

work_important="$TMP/converge-important-blocks"
make_work_repo "$work_important"
implement_tmp="$work_important/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10   # round 1: 10 accepts
# Round 2 core.env: accepted=2 (small), but its findings.md has Important.
mkdir -p "$implement_tmp/round-2"
printf 'REVIEW_CORE_STATUS=ok\nACCEPTED_COUNT=2\nREJECTED_COUNT=0\n' > "$implement_tmp/round-2/review-core.env"
printf 'DEGRADED_ROUND=false\n' > "$implement_tmp/round-2/review-and-fix.env"
printf '### FINDING_1: **Important** severity finding in round 2\n' > "$implement_tmp/round-2/findings.md"
set +e
out=$(
    cd "$work_important" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-important-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id converge-important-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "converge-important expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "converge-important must NOT converge when prior round has Important findings"
fi

# Test 2b: Convergence ignores Important findings from degraded rounds between the compared rounds.
work_degraded_gap="$TMP/converge-degraded-gap-ignored"
make_work_repo "$work_degraded_gap"
implement_tmp="$work_degraded_gap/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 1 false
write_prior_round "$implement_tmp" 2 2 true
printf '### FINDING_1: **Important** severity finding in degraded round 2\n' > "$implement_tmp/round-2/findings.md"
set +e
out=$(
    cd "$work_degraded_gap" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id converge-degraded-gap-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "converge-degraded-gap-ignored expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out" \
    || fail "converge-degraded-gap-ignored should converge using rounds 1 and 3 only"

# Test 2a: Convergence — structured [important] concern blocks early-termination.
work_structured_important="$TMP/converge-structured-important-blocks"
make_work_repo "$work_structured_important"
implement_tmp="$work_structured_important/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10 false
mkdir -p "$implement_tmp/round-2"
printf 'REVIEW_CORE_STATUS=ok\nACCEPTED_COUNT=2\nREJECTED_COUNT=0\n' > "$implement_tmp/round-2/review-core.env"
printf 'DEGRADED_ROUND=false\n' > "$implement_tmp/round-2/review-and-fix.env"
cat > "$implement_tmp/round-2/findings.md" <<'EOF_STRUCTURED_IMPORTANT'
### FINDING_1: correctness: demo/path.sh:10
- **Concern**: [important] Structured severity form should still block convergence.
- **Suggested revision**: Fix it.
EOF_STRUCTURED_IMPORTANT
set +e
out=$(
    cd "$work_structured_important" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id converge-structured-important-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "converge-structured-important expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "converge-structured-important must NOT converge when prior round has [important] concern formatting"
fi

# Test 2b: Convergence — prior degraded small round is excluded from the comparison.
work_prev_degraded="$TMP/converge-prior-degraded-excluded"
make_work_repo "$work_prev_degraded"
implement_tmp="$work_prev_degraded/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10 false
write_prior_round "$implement_tmp" 2 2 true
set +e
out=$(
    cd "$work_prev_degraded" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id prior-degraded-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "converge-prior-degraded-excluded expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "converge-prior-degraded-excluded must ignore degraded round 2 when evaluating convergence"
fi

# Test 3: Degraded round detection — banner excluded from convergence.
# Round 3 has degraded panel; convergence must not fire even though accepts=1.
cat > "$TMP/review-core-degraded-stub.sh" <<'EOF_CORE_DEG'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
# Write degraded banner into voting-tally.md unconditionally (both initial + retry)
printf '**⚠ Degraded code-review panel: 0 judges available.**\n' > "$out/voting-tally.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_DEG
chmod +x "$TMP/review-core-degraded-stub.sh"

work_degraded="$TMP/degraded-excluded"
make_work_repo "$work_degraded"
implement_tmp="$work_degraded/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10   # round 1: 10 accepts (clean)
write_prior_round "$implement_tmp" 2 2    # round 2: 2 accepts (clean, small)
set +e
out=$(
    cd "$work_degraded" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-degraded-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-excluded-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-excluded expected exit 0 got $rc"; }
grep -Fq 'DEGRADED_ROUND=true' <<< "$out" || fail "degraded-excluded should set DEGRADED_ROUND=true"
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "degraded-excluded must NOT converge on a degraded round"
fi
grep -Fq 'panel was degraded (banner triggered)' <<< "$out" \
    || fail "degraded-excluded should emit degraded breadcrumb"

# Test 4: Degraded round panel-retry — retry succeeds (clean), tally from retry used.
cat > "$TMP/review-core-degraded-then-clean.sh" <<'EOF_CORE_DEG_CLEAN'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
# First invocation: write degraded banner. Retry (retry flag present): write clean tally.
retry_flag="$out/degraded-retry.flag"
if [[ -f "$retry_flag" ]]; then
    : > "$out/voting-tally.md"  # clean retry
else
    printf '**⚠ Degraded code-review panel: 0 judges available.**\n' > "$out/voting-tally.md"
fi
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=5\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_DEG_CLEAN
chmod +x "$TMP/review-core-degraded-then-clean.sh"

work_retry_ok="$TMP/degraded-retry-clean"
make_work_repo "$work_retry_ok"
implement_tmp="$work_retry_ok/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_retry_ok" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-degraded-then-clean.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-retry-clean-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-retry-clean expected exit 0 got $rc"; }
grep -Fq 'DEGRADED_ROUND=false' <<< "$out" || fail "degraded-retry-clean should set DEGRADED_ROUND=false after clean retry"
[[ -f "$implement_tmp/round-1/degraded-retry.flag" ]] || fail "degraded-retry-clean should write retry flag"
[[ -f "$implement_tmp/round-1/degraded-retry.done" ]] || fail "degraded-retry-clean should write retry completion marker"

# Test 4a: Stale degraded retry marker from a prior interrupted invocation does not block a retry.
cat > "$TMP/review-core-stale-retry-recovered.sh" <<'EOF_CORE_STALE_RETRY'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
count_file="$out/retry-count"
count=0
if [[ -f "$count_file" ]]; then
    count=$(cat "$count_file")
fi
count=$((count + 1))
printf '%s\n' "$count" > "$count_file"
if [[ "$count" -ge 2 ]]; then
    : > "$out/voting-tally.md"
else
    printf '**⚠ Degraded code-review panel: 0 judges available.**\n' > "$out/voting-tally.md"
fi
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=5\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_STALE_RETRY
chmod +x "$TMP/review-core-stale-retry-recovered.sh"

work_retry_stale="$TMP/degraded-retry-stale"
make_work_repo "$work_retry_stale"
implement_tmp="$work_retry_stale/implement"
mkdir -p "$implement_tmp/round-1"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
touch "$implement_tmp/round-1/degraded-retry.flag"
set +e
out=$(
    cd "$work_retry_stale" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stale-retry-recovered.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-retry-stale-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-retry-stale expected exit 0 got $rc"; }
grep -Fq 'panel was degraded (banner triggered)' <<< "$out" || fail "degraded-retry-stale should still detect degradation and retry"
grep -Fq 'DEGRADED_ROUND=false' <<< "$out" || fail "degraded-retry-stale should still complete the retry"
[[ -f "$implement_tmp/round-1/degraded-retry.done" ]] || fail "degraded-retry-stale should rewrite retry completion marker"

# Test 4b: Completed degraded retry markers from a prior invocation do not suppress a fresh retry.
work_retry_done_stale="$TMP/degraded-retry-done-stale"
make_work_repo "$work_retry_done_stale"
implement_tmp="$work_retry_done_stale/implement"
mkdir -p "$implement_tmp/round-1"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
touch "$implement_tmp/round-1/degraded-retry.flag" "$implement_tmp/round-1/degraded-retry.done"
set +e
out=$(
    cd "$work_retry_done_stale" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-degraded-then-clean.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-retry-done-stale-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-retry-done-stale expected exit 0 got $rc"; }
grep -Fq 'panel was degraded (banner triggered)' <<< "$out" || fail "degraded-retry-done-stale should still schedule a fresh retry"
grep -Fq 'DEGRADED_ROUND=false' <<< "$out" || fail "degraded-retry-done-stale should complete the fresh retry"

# Test 5: Degraded round retry exhausted — both attempts degraded, proceeds best-effort.
work_retry_fail="$TMP/degraded-retry-exhausted"
make_work_repo "$work_retry_fail"
implement_tmp="$work_retry_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_retry_fail" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-degraded-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-retry-exhausted-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-retry-exhausted expected exit 0 got $rc"; }
grep -Fq 'DEGRADED_ROUND=true' <<< "$out" || fail "degraded-retry-exhausted should remain DEGRADED_ROUND=true"
grep -Fq 'panel retry also degraded' <<< "$out" || fail "degraded-retry-exhausted should log retry-also-degraded warning"

# Test 5a: Degraded retry preserves OOS from the first attempt before retry overwrite.
cat > "$TMP/review-core-degraded-oos-then-clean.sh" <<'EOF_CORE_DEG_OOS'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
retry_flag="$out/degraded-retry.flag"
if [[ -f "$retry_flag" ]]; then
    printf '### OOS_2: second attempt\nDescription: retry artifact\n' > "$out/oos-accepted-review.md"
    : > "$out/voting-tally.md"
else
    printf '### OOS_1: first attempt\nDescription: degraded artifact\n' > "$out/oos-accepted-review.md"
    printf '**⚠ Degraded code-review panel: 0 judges available.**\n' > "$out/voting-tally.md"
fi
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_DEG_OOS
chmod +x "$TMP/review-core-degraded-oos-then-clean.sh"

work_retry_oos="$TMP/degraded-retry-oos-preserved"
make_work_repo "$work_retry_oos"
implement_tmp="$work_retry_oos/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_retry_oos" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-degraded-oos-then-clean.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id degraded-retry-oos-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "degraded-retry-oos-preserved expected exit 0 got $rc"; }
grep -Fq 'first attempt' "$implement_tmp/accumulated-oos.md" || fail "degraded-retry-oos-preserved should retain first-attempt OOS content"
grep -Fq 'second attempt' "$implement_tmp/accumulated-oos.md" || fail "degraded-retry-oos-preserved should retain retry OOS content"
[[ "$(jq -s 'length' "$implement_tmp/accumulated-oos.jsonl")" -eq 2 ]] || fail "degraded-retry-oos-preserved should append both OOS jsonl entries"

# Test 5b: fix-applied remains the status even when low accepted counts would otherwise converge.
work_fix_applied="$TMP/fix-applied-not-overwritten"
make_work_repo "$work_fix_applied"
implement_tmp="$work_fix_applied/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 1 false
set +e
out=$(TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_fix_applied" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 --session-env-path "$implement_tmp/session-env.sh" --run-id fix-applied-round-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "fix-applied-not-overwritten expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=fix-applied' <<< "$out" || fail "fix-applied-not-overwritten must preserve fix-applied status"

# Test 5c: main-agent-vote-required remains the status even on low accepted counts.
work_vote_required="$TMP/main-agent-vote-not-overwritten"
make_work_repo "$work_vote_required"
implement_tmp="$work_vote_required/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 0 false
set +e
out=$(TEST_CORE_STATUS=main-agent-vote-required run_review_and_fix "$work_vote_required" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 --session-env-path "$implement_tmp/session-env.sh" --run-id main-agent-vote-round-run)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "main-agent-vote-not-overwritten expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=main-agent-vote-required' <<< "$out" || fail "main-agent-vote-not-overwritten must preserve main-agent-vote-required status"

# Test 6: Churn warning — round-N accepts > round-(N-1) accepts fires on stderr.
work_churn="$TMP/churn-warning"
make_work_repo "$work_churn"
implement_tmp="$work_churn/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 5   # round 1: 5 accepts
write_prior_round "$implement_tmp" 2 4   # round 2: 4 accepts
# Round 3: 8 accepts (> round 2's 4) → churn warning fires
cat > "$TMP/review-core-churn-stub.sh" <<'EOF_CORE_CHURN'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=ok\nROUND_NUM=%s\nACCEPTED_COUNT=8\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE_CHURN
chmod +x "$TMP/review-core-churn-stub.sh"
set +e
out=$(
    cd "$work_churn" && \
    LARCH_QUIET_BREADCRUMBS=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-churn-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 3 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id churn-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "churn-warning expected exit 0 got $rc"; }
grep -Fq 'round 3 accepted 8 findings' <<< "$out" || fail "churn-warning should fire on stderr"
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "churn-warning must not trigger early-termination"
fi

# Test 7: Single small round does NOT terminate (need two consecutive small rounds).
work_single_small="$TMP/single-small-no-terminate"
make_work_repo "$work_single_small"
implement_tmp="$work_single_small/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 10   # round 1: 10 accepts (not small)
set +e
out=$(
    cd "$work_single_small" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id single-small-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "single-small-no-terminate expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "single-small: must NOT converge when only one small round (prev=10 is not small)"
fi

# Test 8: Non-default convergence threshold is honored.
work_threshold="$TMP/convergence-threshold-one"
make_work_repo "$work_threshold"
implement_tmp="$work_threshold/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 2 false
set +e
out=$(
    cd "$work_threshold" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 \
        --convergence-threshold 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id threshold-one-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "convergence-threshold-one expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "convergence-threshold-one must not converge when prior round accepted count exceeds threshold 1"
fi

# Test 8a: Non-default convergence threshold positive path converges when both rounds meet the threshold.
work_threshold_positive="$TMP/convergence-threshold-one-positive"
make_work_repo "$work_threshold_positive"
implement_tmp="$work_threshold_positive/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 1 false
set +e
out=$(
    cd "$work_threshold_positive" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 \
        --convergence-threshold 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id threshold-one-positive-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "convergence-threshold-one-positive expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out" \
    || fail "convergence-threshold-one-positive should converge when both rounds are <= threshold 1"

# Test 9: Invalid convergence threshold fails validation.
work_threshold_invalid="$TMP/convergence-threshold-invalid"
make_work_repo "$work_threshold_invalid"
implement_tmp="$work_threshold_invalid/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_threshold_invalid" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --convergence-threshold nope \
        --session-env-path "$implement_tmp/session-env.sh" --run-id threshold-invalid-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "convergence-threshold-invalid expected exit 2 got $rc"; }
grep -Fq -- '--convergence-threshold must be a non-negative integer' <<< "$out" || fail "convergence-threshold-invalid should name validation error"

# Test 9a: review-and-fix.env writes literal values without shell expansion.
cat > "$TMP/review-core-shell-literal.sh" <<EOF_CORE_SHELL_LITERAL
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ \$# -gt 0 ]]; do
  case "\$1" in
    --output-dir) out="\$2"; shift 2 ;;
    --round-num) round="\$2"; shift 2 ;;
    *) shift; [[ \$# -gt 0 && "\$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "\$out"
: > "\$out/findings.md"
: > "\$out/accepted-findings.md"
: > "\$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "\$round" > "\$out/review-summary.json"
printf '# Review Round %s\n' "\$round" > "\$out/review-round-summary.md"
printf 'REVIEW_CORE_STATUS=\$(touch %s/shell-expanded)\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$TMP" "\$round" "\$out" "\$out"
EOF_CORE_SHELL_LITERAL
chmod +x "$TMP/review-core-shell-literal.sh"

work_shell_literal="$TMP/review-env-literal"
make_work_repo "$work_shell_literal"
implement_tmp="$work_shell_literal/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_shell_literal" && \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-shell-literal.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id review-env-literal-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "review-env-literal expected exit 0 got $rc"; }
[[ ! -e "$TMP/shell-expanded" ]] || fail "review-env-literal must not execute command substitution while writing review-and-fix.env"
expected_review_core_status="REVIEW_CORE_STATUS=\$(touch $TMP/shell-expanded)"
grep -Fq "$expected_review_core_status" "$implement_tmp/round-1/review-and-fix.env" \
    || fail "review-env-literal should persist the literal core status"

# Test 10: Missing findings files fail closed during Important detection.
work_missing_findings="$TMP/converge-missing-findings-fails"
make_work_repo "$work_missing_findings"
implement_tmp="$work_missing_findings/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
write_prior_round "$implement_tmp" 1 1 false
rm -f "$implement_tmp/round-1/findings.md"
set +e
out=$(
    cd "$work_missing_findings" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 2 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id missing-findings-run 2>&1
)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "converge-missing-findings-fails expected exit 2 got $rc"; }
grep -Fq 'findings file not readable for Important check' <<< "$out" || fail "converge-missing-findings-fails should fail closed on unreadable findings"

# Test 11: Round 1 alone is small — no convergence fires (need prior round).
work_round1_small="$TMP/round1-small-no-converge"
make_work_repo "$work_round1_small"
implement_tmp="$work_round1_small/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(
    cd "$work_round1_small" && \
    STUB_ACCEPTED=1 \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-small-stub.sh" \
    REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
        --session-env-path "$implement_tmp/session-env.sh" --run-id round1-small-run
)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "round1-small-no-converge expected exit 0 got $rc"; }
if grep -Fq 'REVIEW_AND_FIX_STATUS=converged-small-changes' <<< "$out"; then
    fail "round1-small-no-converge: must NOT converge on round 1 (no prior round to compare)"
fi
fi  # end section: convergence

# Breadcrumb pin: round entry and coder dispatch breadcrumbs appear when LARCH_QUIET_BREADCRUMBS=1.
if section_runs dispatch; then
work_breadcrumb_round="$TMP/breadcrumb-round-entry"
make_work_repo "$work_breadcrumb_round"
implement_tmp="$work_breadcrumb_round/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(LARCH_QUIET_BREADCRUMBS=1 TEST_CORE_STATUS=zero run_review_and_fix "$work_breadcrumb_round" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
    --session-env-path "$implement_tmp/session-env.sh" --run-id breadcrumb-round-run 2>&1)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "breadcrumb round-entry expected exit 0 got $rc"; }
grep -Fq '→ review-and-fix: round 1' <<< "$out" || fail "breadcrumb round-entry: missing round entry breadcrumb"

work_breadcrumb_coder="$TMP/breadcrumb-coder-dispatch"
make_work_repo "$work_breadcrumb_coder"
implement_tmp="$work_breadcrumb_coder/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(LARCH_QUIET_BREADCRUMBS=1 TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_breadcrumb_coder" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
    --session-env-path "$implement_tmp/session-env.sh" --run-id breadcrumb-coder-run 2>&1)
rc=$?
set -e
grep -Fq '→ review-and-fix: dispatching coder' <<< "$out" || fail "breadcrumb coder-dispatch: missing dispatching coder breadcrumb"

work_breadcrumb_no_changes="$TMP/breadcrumb-no-changes"
make_work_repo "$work_breadcrumb_no_changes"
implement_tmp="$work_breadcrumb_no_changes/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(LARCH_QUIET_BREADCRUMBS=1 TEST_AGENT_BEHAVIOR=codex-no-changes run_review_and_fix "$work_breadcrumb_no_changes" \
    --implement-tmpdir "$implement_tmp" --mode diff --round-num 1 \
    --session-env-path "$implement_tmp/session-env.sh" --run-id breadcrumb-no-changes-run 2>&1)
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "breadcrumb no-changes expected exit 0 got $rc"; }
grep -Fq 'coder dispatch exited 0 but did not modify the working tree' <<< "$out" \
    || fail "breadcrumb no-changes: missing halting breadcrumb"
fi  # end section: dispatch (breadcrumb additions)

grep -Fq -- '--panel hard' "$SCRIPT" \
    || fail "review-and-fix.sh must invoke review-core with literal --panel hard"

work_reject_panel="$TMP/reject-public-panel"
make_work_repo "$work_reject_panel"
impl_rp="$work_reject_panel/implement"
mkdir -p "$impl_rp"
printf 'CODEX_PRESENT=true\nCURSOR_PRESENT=true\n' > "$impl_rp/session-env.sh"
set +e
out=$(run_review_and_fix "$work_reject_panel" \
    --implement-tmpdir "$impl_rp" --mode diff --panel simple --round-num 1 \
    --session-env-path "$impl_rp/session-env.sh" 2>&1)
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "public --panel argv must exit 2, got $rc"
printf '%s\n' "$out" | grep -qi 'unknown option' || fail "expected unknown option for --panel"

echo "test-review-and-fix: ok"
