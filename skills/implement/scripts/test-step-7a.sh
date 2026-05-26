#!/usr/bin/env bash
# test-step-7a.sh — offline harness for step-7a.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-7a.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-7a.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() {
    PASS=$((PASS + 1))
    printf 'PASS: %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf 'FAIL: %s\n' "$1" >&2
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then
        pass "$label"
    else
        fail "$label (missing: $needle)"
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then
        fail "$label (unexpected: $needle)"
    else
        pass "$label"
    fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3
    assert_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_file_equals() {
    local expected=$1 path=$2 label=$3 actual
    actual=$(cat "$path" 2>/dev/null || true)
    if [ "$expected" = "$actual" ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_equals() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then
        pass "$label"
    else
        fail "$label (expected $expected got $actual)"
    fi
}

assert_call_order() {
    local file=$1 first=$2 second=$3 label=$4 first_line second_line
    first_line=$(grep -nF "$first" "$file" 2>/dev/null | head -n 1 | cut -d: -f1 || true)
    second_line=$(grep -nF "$second" "$file" 2>/dev/null | head -n 1 | cut -d: -f1 || true)
    if [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

green_expected_summary() {
    cat <<'EOF'
Architecture diagram not available.

## Code Flow Diagram

```mermaid
graph TD
  A --> B
```
EOF
}

placeholder_expected_summary() {
    local placeholder=$1
    cat <<EOF
Architecture diagram not available.

$placeholder
EOF
}

finish() {
    printf 'PASS=%s\n' "$PASS"
    printf 'FAIL=%s\n' "$FAIL"
    [ "$FAIL" -eq 0 ]
}

setup_plugin() {
    local root=$1
    mkdir -p "$root/scripts" "$root/skills/implement/scripts"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    cp "$REPO_ROOT/scripts/lib-execution-issues.sh" "$root/scripts/lib-execution-issues.sh"
    cp "$REPO_ROOT/scripts/lib-redact.sh" "$root/scripts/lib-redact.sh"

    cat > "$root/skills/implement/scripts/generate-code-flow-diagram.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'generate-code-flow-diagram.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
tmpdir=""
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) tmpdir=$2; shift 2 ;;
        *) shift ;;
    esac
done
case "${STEP7A_GEN_MODE:-ok}" in
    ok)
        printf '## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A --> B\n```\n' > "$tmpdir/code-flow-diagram.md"
        printf 'STATUS=ok\nDIAGRAM_FILE=%s\nSKIP_REASON=\n' "$tmpdir/code-flow-diagram.md"
        ;;
    rejected)
        token=${STEP7A_SANITIZER_TOKEN:-pipe-in-node-label}
        printf 'generator sanitizer rejected\n' >&2
        printf 'STATUS=skipped\nDIAGRAM_FILE=\nSKIP_REASON=%s fence=mermaid line=7\n' "$token"
        ;;
    failed)
        printf 'generator helper failed\n' >&2
        printf 'STATUS=failed\nDIAGRAM_FILE=\nSKIP_REASON=%s\n' "${STEP7A_GEN_FORCE_SKIP_REASON:-helper-error}"
        ;;
    crash)
        printf 'generator crashed\n' >&2
        exit 99
        ;;
esac
STUB

    cat > "$root/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
content=""
args="$*"
while [ $# -gt 0 ]; do
    case "$1" in
        --content-file) content=$2; shift 2 ;;
        *) shift ;;
    esac
done
[ -n "$content" ] && [ -f "$content" ] && printf 'compose-summary-diagrams %s\n' "$content" >> "$STEP7A_CALLS_LOG"
printf 'tracking-issue-summary.sh %s\n' "$args" >> "$STEP7A_CALLS_LOG"
if [ "${STEP7A_UPSERT_FAIL:-0}" = "1" ]; then
    printf 'upsert failed\n' >&2
    exit 1
fi
printf 'COMMENT_URL=https://example.test/comment/1\n'
STUB

    cat > "$root/scripts/rebase-checkpoint-probe.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'rebase-checkpoint-probe.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
case "${STEP7A_REBASE_MODE:-ok}" in
    ok)
        printf 'REBASE_OUTCOME=ok\n'
        ;;
    conflict)
        printf 'REBASE_OUTCOME=conflict\nCONFLICT_FILES=skills/implement/scripts/step-7a.sh\n'
        exit 1
        ;;
    failed)
        printf 'REBASE_OUTCOME=failed\nREBASE_ERROR=rebase-failed\n'
        exit 3
        ;;
    unexpected)
        printf 'REBASE_OUTCOME=failed\nREBASE_ERROR=unexpected-rc-5\n'
        exit 5
        ;;
esac
STUB

    cat > "$root/skills/implement/scripts/flush-execution-issues.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
count_file="${STEP7A_FLUSH_COUNT_FILE:?}"
count=0
[ -f "$count_file" ] && count=$(cat "$count_file")
count=$((count + 1))
printf '%s\n' "$count" > "$count_file"
printf 'flush-execution-issues.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
if [ "${STEP7A_FLUSH_FAIL_FIRST:-0}" = "1" ] && [ "$count" -eq 1 ]; then
    printf 'flush failed\n' >&2
    exit 1
fi
printf 'FLUSH_STATUS=ok\nRECORDS=0\n'
STUB

    cat > "$root/scripts/capture-session-transcript.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'capture-session-transcript.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
printf 'SESSION_TRANSCRIPT_STATUS=ok\n'
STUB

    cat > "$root/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
cmd=${1:-}
shift || true
printf 'larch-log.sh %s %s\n' "$cmd" "$*" >> "$STEP7A_CALLS_LOG"
printf 'LOG_STATUS=ok\n'
STUB

    cat > "$root/scripts/read-session-env-key.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
file=""; key=""; default=""
while [ $# -gt 0 ]; do
    case "$1" in
        --file) file=$2; shift 2 ;;
        --key) key=$2; shift 2 ;;
        --default) default=$2; shift 2 ;;
        *) shift ;;
    esac
done
awk -F= -v key="$key" -v default="$default" '$1==key{print substr($0, index($0, "=") + 1); found=1; exit} END{if(!found) print default}' "$file" 2>/dev/null
STUB

    cat > "$root/scripts/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log=""; site=""; tool=""; exit_code=""; category=""; output_file=""
while [ $# -gt 0 ]; do
    case "$1" in
        --log) log=$2; shift 2 ;;
        --site) site=$2; shift 2 ;;
        --tool) tool=$2; shift 2 ;;
        --exit-code) exit_code=$2; shift 2 ;;
        --category) category=$2; shift 2 ;;
        --output-file) output_file=$2; shift 2 ;;
        --redact) shift ;;
        *) shift ;;
    esac
done
{
    printf '\n### %s\n\n' "$category"
    printf -- '- **Step %s — %s failed (exit %s)**:\n' "$site" "$tool" "$exit_code"
    cat "$output_file" 2>/dev/null || true
    printf '\n'
} >> "$log"
STUB

    for stub in token-ledger.sh timing-ledger.sh token-report.sh timing-report.sh; do
        cat > "$root/scripts/$stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s %s\n' "$(basename "$0")" "$*" >> "$STEP7A_CALLS_LOG"
if [ "$(basename "$0")" = "token-report.sh" ] || [ "$(basename "$0")" = "timing-report.sh" ]; then
    out=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --output) out=$2; shift 2 ;;
            *) shift ;;
        esac
    done
    [ -n "$out" ] && printf '{}\n' > "$out"
fi
STUB
    done

    chmod +x "$root/scripts/"*.sh "$root/skills/implement/scripts/"*.sh
}

new_case() {
    local name=$1
    CASE_DIR="$TMP_ROOT/$name"
    mkdir -p "$CASE_DIR/tmp"
    : > "$CASE_DIR/calls.log"
    : > "$CASE_DIR/flush-count"
    touch "$CASE_DIR/tmp/execution-issues.md"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s/plugin\nLARCH_TOKEN_SESSION_ID=test-session\nLARCH_CLAUDE_SOURCE_FILE=%s/source.jsonl\nLARCH_TIMING_LEDGER=%s/timing.log\nLARCH_ISSUE_NUMBER=42\nLARCH_RUN_ID=run-001\nLARCH_NO_LOGS_COMMIT=false\nLARCH_FORKED_TARGET=false\n' \
        "$TMP_ROOT" "$CASE_DIR" "$CASE_DIR" > "$CASE_DIR/tmp/session-env.sh"
}

run_helper() {
    local workdir=$1
    shift
    (
        cd "$workdir"
        CLAUDE_PLUGIN_ROOT="$TMP_ROOT/plugin" \
        STEP7A_CALLS_LOG="$CASE_DIR/calls.log" \
        STEP7A_FLUSH_COUNT_FILE="$CASE_DIR/flush-count" \
        "$HELPER" "$@"
    )
}

run_helper_quiet() {
    local workdir=$1
    shift
    (
        cd "$workdir"
        unset LARCH_QUIET_DISABLE
        CLAUDE_PLUGIN_ROOT="$TMP_ROOT/plugin" \
        STEP7A_CALLS_LOG="$CASE_DIR/calls.log" \
        STEP7A_FLUSH_COUNT_FILE="$CASE_DIR/flush-count" \
        "$HELPER" "$@"
    )
}

make_skip_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-origin.git" >/dev/null 2>&1
    git -C "$repo" remote add origin "$repo-origin.git"
    git -C "$repo" fetch origin main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m docs
}

make_forked_skip_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-upstream.git" >/dev/null 2>&1
    git -C "$repo" remote add upstream "$repo-upstream.git"
    git -C "$repo" fetch upstream main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m docs
}

make_forked_generate_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-upstream.git" >/dev/null 2>&1
    git -C "$repo" remote add upstream "$repo-upstream.git"
    git -C "$repo" fetch upstream main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    printf 'feature\n' > "$repo/docs/Y.md"
    printf 'feature\n' > "$repo/docs/Z.md"
    git -C "$repo" add docs/X.md docs/Y.md docs/Z.md
    git -C "$repo" commit -q -m docs
}

echo "=== test-step-7a ==="

setup_plugin "$TMP_ROOT/plugin"

new_case green
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "green exits 0"
assert_contains "DIAGRAM_STATUS=ok" "$out" "green emits diagram ok"
assert_contains "DIAGRAM_PATH=$CASE_DIR/tmp/code-flow-diagram.md" "$out" "green emits diagram path"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "green emits comment URL"
assert_contains "LOG_FLUSH_STATUS=ok" "$out" "green emits log flush ok"
assert_contains "SESSION_TRANSCRIPT_STATUS=ok" "$out" "green relays transcript status"
assert_contains "STEP_7A_BAIL_REASON=" "$out" "green emits empty bail reason"
assert_contains "REBASE_OUTCOME=ok" "$out" "green emits rebase outcome"
assert_contains "generate-code-flow-diagram.sh --implement-tmpdir" "$(cat "$CASE_DIR/calls.log")" "green passes tmpdir to generator"
assert_contains "--base-remote origin --base-ref main" "$(cat "$CASE_DIR/calls.log")" "green passes origin base args to generator"
assert_call_order "$CASE_DIR/calls.log" "token-ledger.sh mark Step 7a — code flow diagram" "generate-code-flow-diagram.sh" "green marks token ledger before generator"
assert_call_order "$CASE_DIR/calls.log" "timing-ledger.sh mark Step 7a — code flow diagram" "generate-code-flow-diagram.sh" "green marks timing ledger before generator"
assert_call_order "$CASE_DIR/calls.log" "generate-code-flow-diagram.sh" "compose-summary-diagrams" "green generate before compose"
assert_call_order "$CASE_DIR/calls.log" "compose-summary-diagrams" "tracking-issue-summary.sh" "green compose before upsert"
assert_call_order "$CASE_DIR/calls.log" "tracking-issue-summary.sh" "rebase-checkpoint-probe.sh" "green upsert before rebase"
assert_call_order "$CASE_DIR/calls.log" "rebase-checkpoint-probe.sh" "flush-execution-issues.sh" "green rebase before flush"
assert_file_equals "$(green_expected_summary)" "$CASE_DIR/tmp/summary-diagrams.md" "green writes expected summary diagrams"

new_case diagram-skip
make_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-skip exits 0"
assert_contains "DIAGRAM_STATUS=skip" "$out" "diagram-skip emits skip"
assert_contains "diagrams status=skip reason=small-non-runtime-change" "$out" "diagram-skip prints skip line"
assert_not_contains "generate-code-flow-diagram.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-skip does not invoke generator"
assert_file_contains "(Code Flow Diagram skipped — small/non-runtime change)" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-skip writes placeholder"
assert_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-skip still posts comment"

new_case diagram-skip-forked
make_forked_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-skip-forked exits 0"
assert_contains "DIAGRAM_STATUS=skip" "$out" "diagram-skip-forked emits skip"
assert_contains "diagrams status=skip reason=small-non-runtime-change" "$out" "diagram-skip-forked prints skip line"
assert_not_contains "generate-code-flow-diagram.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-skip-forked does not invoke generator"
assert_file_contains "(Code Flow Diagram skipped — small/non-runtime change)" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-skip-forked writes placeholder"
assert_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-skip-forked still posts comment"

new_case diagram-generate-forked
make_forked_generate_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-generate-forked exits 0"
assert_contains "DIAGRAM_STATUS=ok" "$out" "diagram-generate-forked emits diagram ok"
assert_contains "generate-code-flow-diagram.sh --implement-tmpdir" "$(cat "$CASE_DIR/calls.log")" "diagram-generate-forked passes tmpdir to generator"
assert_contains "--base-remote upstream --base-ref main" "$(cat "$CASE_DIR/calls.log")" "diagram-generate-forked passes upstream base args to generator"

new_case diagram-rejected
set +e
out=$(STEP7A_GEN_MODE=rejected run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-rejected exits 0"
assert_contains "DIAGRAM_STATUS=skipped" "$out" "diagram-rejected emits skipped"
assert_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-rejected still posts comment"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "diagram-rejected emits comment URL"
assert_contains "LOG_FLUSH_STATUS=ok" "$out" "diagram-rejected keeps flush ok"
assert_not_contains "### Warnings" "$(cat "$CASE_DIR/tmp/execution-issues.md")" "diagram-rejected does not append warning"
assert_file_equals "$(placeholder_expected_summary "pipe-in-node-label fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected writes expected summary diagrams with generator SKIP_REASON"

for sanitizer_token in br-in-participant-alias dollar-in-participant-alias unclosed-frontmatter; do
    new_case "diagram-rejected-$sanitizer_token"
    set +e
    out=$(STEP7A_GEN_MODE=rejected STEP7A_SANITIZER_TOKEN="$sanitizer_token" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
    rc=$?
    set -e
    assert_equals 0 "$rc" "diagram-rejected-$sanitizer_token exits 0"
    assert_contains "DIAGRAM_STATUS=skipped" "$out" "diagram-rejected-$sanitizer_token emits skipped"
    assert_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-rejected-$sanitizer_token still posts comment"
    assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "diagram-rejected-$sanitizer_token emits comment URL"
    assert_file_equals "$(placeholder_expected_summary "${sanitizer_token} fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-rejected-$sanitizer_token writes expected summary diagrams with token SKIP_REASON"
done

new_case diagram-failure
set +e
out=$(STEP7A_GEN_MODE=failed run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-generation-failure exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "diagram-generation-failure emits failed"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "diagram-generation-failure still posts comment"
assert_file_contains "helper-error" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-failure writes generator SKIP_REASON helper-error"
assert_file_contains "### Warnings" "$CASE_DIR/tmp/execution-issues.md" "diagram-generation-failure appends warning"

new_case diagram-failure-sanitizer
set +e
out=$(STEP7A_GEN_MODE=failed STEP7A_SANITIZER_TOKEN=pipe-in-node-label STEP7A_GEN_FORCE_SKIP_REASON='pipe-in-node-label fence=mermaid line=7' run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-failure-sanitizer exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "diagram-failure-sanitizer emits failed"
assert_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "diagram-failure-sanitizer still posts comment"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "diagram-failure-sanitizer emits comment URL"
assert_file_equals "$(placeholder_expected_summary "pipe-in-node-label fence=mermaid line=7")" "$CASE_DIR/tmp/summary-diagrams.md" "diagram-failure-sanitizer writes expected summary diagrams with fixture SKIP_REASON"

new_case upsert-failure
set +e
out=$(STEP7A_UPSERT_FAIL=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "summary-upsert-failure exits 0"
assert_contains "COMMENT_URL=" "$out" "summary-upsert-failure emits empty URL"
assert_file_contains "### Tool Failures" "$CASE_DIR/tmp/execution-issues.md" "summary-upsert-failure appends tool failure"
assert_contains "rebase-checkpoint-probe.sh" "$(cat "$CASE_DIR/calls.log")" "summary-upsert-failure still runs rebase"
assert_contains "flush-execution-issues.sh" "$(cat "$CASE_DIR/calls.log")" "summary-upsert-failure still runs flush"

new_case flush-failure
set +e
out=$(STEP7A_FLUSH_FAIL_FIRST=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "flush-failure exits 0"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "flush-failure emits degraded"
assert_file_contains "### Tool Failures" "$CASE_DIR/tmp/execution-issues.md" "flush-failure appends tool failure"
assert_equals 2 "$(cat "$CASE_DIR/flush-count")" "flush-failure still runs post-transcript flush"
assert_contains "larch-log.sh commit" "$(cat "$CASE_DIR/calls.log")" "flush-failure still runs commit"

new_case flush-failure-no-logs-commit
set +e
out=$(STEP7A_FLUSH_FAIL_FIRST=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit true --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "flush-failure-no-logs-commit exits 0"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "flush-failure-no-logs-commit preserves degraded"
assert_not_contains "larch-log.sh commit" "$(cat "$CASE_DIR/calls.log")" "flush-failure-no-logs-commit skips commit"

new_case no-logs-commit
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit true --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "no-logs-commit exits 0"
assert_not_contains "larch-log.sh commit" "$(cat "$CASE_DIR/calls.log")" "no-logs-commit skips commit"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "no-logs-commit emits skipped"

new_case forked-target
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "forked-target exits 0"
assert_contains "rebase-checkpoint-probe.sh 7a.r diagrams --base-remote upstream --base-ref main" "$(cat "$CASE_DIR/calls.log")" "forked-target passes upstream argv"

new_case issue-empty
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number "" --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "ISSUE_NUMBER empty exits 0"
assert_not_contains "tracking-issue-summary.sh" "$(cat "$CASE_DIR/calls.log")" "ISSUE_NUMBER empty skips upsert"
assert_contains "COMMENT_URL=" "$out" "ISSUE_NUMBER empty emits empty URL"
assert_contains "rebase-checkpoint-probe.sh" "$(cat "$CASE_DIR/calls.log")" "ISSUE_NUMBER empty still runs rebase"

new_case generator-crash
set +e
out=$(STEP7A_GEN_MODE=crash run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "generator-crash exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "generator-crash emits failed"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "generator-crash still posts comment"
assert_file_contains "Code flow diagram not available." "$CASE_DIR/tmp/summary-diagrams.md" "generator-crash writes unavailable placeholder"
assert_file_contains "### Warnings" "$CASE_DIR/tmp/execution-issues.md" "generator-crash appends warning"

new_case rebase-conflict
set +e
out=$(STEP7A_REBASE_MODE=conflict run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 1 "$rc" "rebase-conflict exits 1"
assert_contains "REBASE_OUTCOME=conflict" "$out" "rebase-conflict emits conflict outcome"
assert_contains "LOG_FLUSH_STATUS=skipped-rebase-checkpoint" "$out" "rebase-conflict emits skipped rebase flush status"
assert_not_contains "flush-execution-issues.sh" "$(cat "$CASE_DIR/calls.log")" "rebase-conflict skips flush"

new_case rebase-failed
set +e
out=$(STEP7A_REBASE_MODE=failed run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 3 "$rc" "rebase-failed exits 3"
assert_contains "REBASE_OUTCOME=failed" "$out" "rebase-failed emits failed outcome"
assert_contains "LOG_FLUSH_STATUS=skipped-rebase-checkpoint" "$out" "rebase-failed emits skipped rebase flush status"
assert_not_contains "flush-execution-issues.sh" "$(cat "$CASE_DIR/calls.log")" "rebase-failed skips flush"

new_case rebase-unexpected-rc
set +e
out=$(STEP7A_REBASE_MODE=unexpected run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 5 "$rc" "rebase-unexpected-rc exits 5"
assert_contains "REBASE_OUTCOME=failed" "$out" "rebase-unexpected-rc emits failed outcome"
assert_contains "REBASE_ERROR=unexpected-rc-5" "$out" "rebase-unexpected-rc emits unexpected rc error"
assert_contains "LOG_FLUSH_STATUS=skipped-rebase-checkpoint" "$out" "rebase-unexpected-rc emits skipped rebase flush status"
assert_not_contains "flush-execution-issues.sh" "$(cat "$CASE_DIR/calls.log")" "rebase-unexpected-rc skips flush"

new_case quiet-rebase-contract
set +e
out=$(run_helper_quiet "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "quiet-rebase-contract exits 0"
assert_contains "REBASE_OUTCOME=ok" "$out" "quiet-rebase-contract preserves rebase outcome on contract stream"
assert_contains "LOG_FLUSH_STATUS=ok" "$out" "quiet-rebase-contract emits final tail"

new_case quiet-diagram-skip-contract
make_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper_quiet "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "quiet-diagram-skip-contract exits 0"
assert_contains "⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=0s" "$out" "quiet-diagram-skip-contract preserves skip line on contract stream"

new_case argv-error
set +e
out=$(run_helper "$CASE_DIR" --issue-number 42 2>&1)
rc=$?
set -e
assert_equals 2 "$rc" "argv error exits 2"
assert_contains "STEP_7A_BAIL_REASON=argv" "$out" "argv error emits bail reason"

finish
