#!/usr/bin/env bash
# test-lint-foreground-markers.sh — regression harness for lint-foreground-markers.sh
#
# Issue #2749 (FINDING_22 / FINDING_23) rewrote the lint contract from the
# foreground-required banner to the background+monitor pair banner. This
# harness exercises the new contract: clean cases must carry BOTH halves
# (run_in_background: true AND breadcrumb-monitor.sh --stream) within the
# same fence, plus the canonical banner/comment phrases.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINT="$REPO_ROOT/scripts/lint-foreground-markers.sh"

if [[ ! -f "$LINT" ]]; then
    printf 'ERROR: lint script not found: %s\n' "$LINT" >&2
    exit 1
fi

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lint-foreground-markers.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0

reset_tree() {
    find "$TMPROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

write_md() {
    local rel="$1"
    mkdir -p "$(dirname "$TMPROOT/$rel")"
    cat >"$TMPROOT/$rel"
}

write_sh() {
    local rel="$1"
    mkdir -p "$(dirname "$TMPROOT/$rel")"
    cat >"$TMPROOT/$rel"
}

run_lint() {
    local stderr_file="$1"
    set +e
    bash "$LINT" --root "$TMPROOT" 2>"$stderr_file"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

assert_case() {
    local label="$1"
    local expected_exit="$2"
    local stderr_file="$3"
    local rc="$4"
    shift 4

    if [[ "$rc" -ne "$expected_exit" ]]; then
        printf 'FAIL [%s]: expected exit %s, got %s\n' "$label" "$expected_exit" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    for needle in "$@"; do
        if ! grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr missing expected needle: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return
        fi
    done
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

assert_case_clean() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    if [[ "$rc" -ne 0 ]]; then
        printf 'FAIL [%s]: expected exit 0, got %s\n' "$label" "$rc" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    if [[ -s "$stderr_file" ]]; then
        printf 'FAIL [%s]: expected empty stderr\n' "$label" >&2
        cat "$stderr_file" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    printf 'PASS [%s]\n' "$label"
    PASS=$((PASS + 1))
}

assert_case_err() {
    local label="$1"
    local stderr_file="$2"
    local rc="$3"
    shift 3
    assert_case "$label" 1 "$stderr_file" "$rc" "$@"
}

assert_stderr_lacks() {
    local label="$1"
    local stderr_file="$2"
    shift 2

    local needle
    for needle in "$@"; do
        if grep -Fq "$needle" "$stderr_file"; then
            printf 'FAIL [%s]: stderr unexpectedly contained: %s\n' "$label" "$needle" >&2
            cat "$stderr_file" >&2
            FAIL=$((FAIL + 1))
            return 1
        fi
    done
    return 0
}

stderr_file="$(mktemp)"

# 1 — clean collect-agent-results.sh (background+monitor pair)
reset_tree
write_md skills/clean/SKILL.md <<'EOF'
# Case 1

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "clean collect-agent-results fence" "$stderr_file" "$rc"

# 2 — missing banner
reset_tree
write_md skills/miss-banner/SKILL.md <<'EOF'
# Case 2

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "missing banner" 1 "$stderr_file" "$rc" 'missing background-pair banner for collect-agent-results.sh'

# 3 — missing comment
reset_tree
write_md skills/miss-comment/SKILL.md <<'EOF'
# Case 3

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "missing comment" 1 "$stderr_file" "$rc" 'missing background-pair comment for collect-agent-results.sh'

# 4 — blockquoted banner is accepted
reset_tree
write_md skills/bq-banner/SKILL.md <<'EOF'
# Case 4

> **⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "blockquoted banner" "$stderr_file" "$rc"

# 5 — banner falls outside the 20-line pre-fence window
reset_tree
write_md skills/banner-window/SKILL.md <<'EOF'
# Case 5

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x
x

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "banner outside pre-fence window" 1 "$stderr_file" "$rc" 'missing background-pair banner for collect-agent-results.sh'

# 6 — comment more than five in-fence lines above the anchor
reset_tree
write_md skills/comment-window/SKILL.md <<'EOF'
# Case 6

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE




${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "comment too far above anchor" 1 "$stderr_file" "$rc" 'missing background-pair comment for collect-agent-results.sh'

# 7 — non-denylist script
reset_tree
write_md skills/non-deny/SKILL.md <<'EOF'
# Case 7

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-reviewers.sh --timeout 1 a.done b.done
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "wait-for-reviewers not denylisted" "$stderr_file" "$rc"

# 8 — yaml fence ignored
reset_tree
write_md skills/yaml-fence/SKILL.md <<'EOF'
# Case 8

```yaml
path: ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "yaml fence ignores shell anchors" "$stderr_file" "$rc"

# 9 — ship-pr.sh
reset_tree
write_md skills/ship-pr/SKILL.md <<'EOF'
# Case 9

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "ship-pr with markers" "$stderr_file" "$rc"

# 10 — indented ```bash opening fence
reset_tree
write_md skills/indented-fence/SKILL.md <<'EOF'
# Case 10

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

   ```bash
   # Background pair required: see BASH_AUTHORING.md §4
   # Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
   ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
   COLLECTOR_PID=$!
   monitor_rc=0
   ${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
   if [ "$monitor_rc" -eq 0 ]; then
       wait "$COLLECTOR_PID"
   else
       wait "$COLLECTOR_PID" 2>/dev/null || true
   fi
   ```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "indented bash fence" "$stderr_file" "$rc"

# 11 — skills/shared/*.md
reset_tree
write_md skills/shared/case11.md <<'EOF'
# Case 11

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "skills/shared markdown path" "$stderr_file" "$rc"

# 12 — if-shaped run-step5-review.sh
reset_tree
write_md skills/if-shape/SKILL.md <<'EOF'
# Case 12

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
"${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh" --flag &
RUN_STEP5_REVIEW_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$RUN_STEP5_REVIEW_PID"
else
    wait "$RUN_STEP5_REVIEW_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "if-shaped denylisted invoke" "$stderr_file" "$rc"

# 13 — assignment-shaped review-and-fix.sh
reset_tree
write_md skills/assign-shape/SKILL.md <<'EOF'
# Case 13

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
CMD=${CLAUDE_PLUGIN_ROOT}/scripts/review-and-fix.sh
printf '%s\n' "$CMD"
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "assignment-shaped denylisted invoke" "$stderr_file" "$rc"

# 13b — command-substitution assignment with denylisted path (dispatch-with-waterfall)
reset_tree
write_md skills/cmdsubst-assign/SKILL.md <<'EOF'
# Case 13b

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
VAR=$(${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.sh --timeout 1)
printf '%s\n' "$VAR"
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "cmdsubst assignment-shaped denylisted invoke" "$stderr_file" "$rc"

# 13c — unbraced CLAUDE_PLUGIN_ROOT path to denylisted script
reset_tree
write_md skills/unbraced-root/SKILL.md <<'EOF'
# Case 13c

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
$CLAUDE_PLUGIN_ROOT/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "unbraced CLAUDE_PLUGIN_ROOT denylisted invoke" "$stderr_file" "$rc"

# 14 — substring file name must not anchor collect-agent-results.sh
reset_tree
write_md skills/substring-guard/SKILL.md <<'EOF'
# Case 14

```bash
echo "fixture path test-collect-agent-results.sh"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "substring test-collect-agent-results false negative" "$stderr_file" "$rc"

# 14b — plugin-root path ending in test-review-and-fix.sh must not match review-and-fix.sh
reset_tree
write_md skills/plugin-root-suffix-guard/SKILL.md <<'EOF'
# Case 14b

```bash
echo "${CLAUDE_PLUGIN_ROOT}/scripts/test-review-and-fix.sh"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "plugin-root path suffix must not false-anchor review-and-fix" "$stderr_file" "$rc"

# 15 — dispatch-plan-voters.sh
reset_tree
write_md skills/plan-voters/SKILL.md <<'EOF'
# Case 15

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-plan-voters.sh --tmpdir "$TMP" &
DISPATCH_PLAN_VOTERS_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$DISPATCH_PLAN_VOTERS_PID"
else
    wait "$DISPATCH_PLAN_VOTERS_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "dispatch-plan-voters with markers" "$stderr_file" "$rc"

# 17 — parse-only safety: fence body would exit 99 if executed as a script; linter must not
reset_tree
write_md skills/parse-only-exec/SKILL.md <<'EOF'
# Case 17

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
exit 99
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "parse-only fence body not executed" "$stderr_file" "$rc"

# 18 — EOF: unterminated fence still scanned (missing banner)
reset_tree
write_md skills/eof-open-fence/SKILL.md <<'EOF'
# Case 18

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
EOF
rc="$(run_lint "$stderr_file")"
assert_case "EOF unterminated fence still linted" 1 "$stderr_file" "$rc" 'missing background-pair banner for collect-agent-results.sh'

# 19 — second Family-B anchor after >5 in-fence lines needs its own comment
reset_tree
write_md skills/multi-anchor-gap/SKILL.md <<'EOF'
# Case 19

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"




${CLAUDE_PLUGIN_ROOT}/scripts/ci-wait.sh --dry-run
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case "second anchor after long gap needs comment" 1 "$stderr_file" "$rc" 'missing background-pair comment for ci-wait.sh'

# 20 — if ! with repo-relative path (no CLAUDE_PLUGIN_ROOT prefix)
reset_tree
write_md skills/if-not-claude-path/SKILL.md <<'EOF'
# Case 20

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
scripts/run-step5-review.sh --mode loop &
RUN_STEP5_REVIEW_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$RUN_STEP5_REVIEW_PID"
else
    wait "$RUN_STEP5_REVIEW_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "if ! relative denylisted path" "$stderr_file" "$rc"

# 21 — env-prefixed bash invocation
reset_tree
write_md skills/env-bash-prefix/SKILL.md <<'EOF'
# Case 21

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
FOO=1 bash "${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh" --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "env-prefixed bash denylisted invoke" "$stderr_file" "$rc"

# 21b — step2-implement.sh (denylist coverage)
reset_tree
write_md skills/step2-impl/SKILL.md <<'EOF'
# Case 21b

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
bash "${CLAUDE_PLUGIN_ROOT}/scripts/step2-implement.sh" --help
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "step2-implement denylisted invoke" "$stderr_file" "$rc"

# 22 — commented-out denylisted path is not an anchor
reset_tree
write_md skills/commented-denylist/SKILL.md <<'EOF'
# Case 22

```bash
# ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
echo ok
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "commented denylisted line ignored" "$stderr_file" "$rc"

# 23 — step-7a is foreground-only and uses the foreground marker pair
reset_tree
write_md skills/step7a/SKILL.md <<'EOF'
# Case 23

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-7a.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "step-7a foreground invocation" "$stderr_file" "$rc"

# 24 — step-7a missing the foreground banner fails
reset_tree
write_md skills/step7a-missing-banner/SKILL.md <<'EOF'
# Case 24

```bash
# Foreground required: see BASH_AUTHORING.md §4
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-7a.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "step-7a missing foreground banner" "$stderr_file" "$rc" "missing foreground-required banner for step-7a.sh"

# 25 — step-7a missing the foreground comment fails
reset_tree
write_md skills/step7a-missing-comment/SKILL.md <<'EOF'
# Case 25

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-7a.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "step-7a missing foreground comment" "$stderr_file" "$rc" "missing foreground-required comment for step-7a.sh"

# 26 — step-7a must not set run_in_background: true
reset_tree
write_md skills/step7a-background/SKILL.md <<'EOF'
# Case 26

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
# Foreground required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-7a.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "step-7a forbids run_in_background" "$stderr_file" "$rc" "foreground-only invocation must not set run_in_background: true for step-7a.sh"

# 27 — denylist-shaped path inside a quoted heredoc body must not anchor (false-positive guard)
reset_tree
write_md skills/heredoc-doc/SKILL.md <<'EOF'
# Case 27

```bash
cat <<'MD'
Example: ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1
MD
echo done
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "heredoc body ignores denylist-shaped text" "$stderr_file" "$rc"

# 28 — backslash-continued denylisted path with markers (single logical invocation)
reset_tree
write_md skills/bs-cont/SKILL.md <<'EOF'
# Case 28

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.\
sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "backslash-continued denylisted path with markers" "$stderr_file" "$rc"

# 29 — top-level Family B missing paired PID allocation fails
reset_tree
write_md skills/missing-pid-alloc/SKILL.md <<'EOF'
# Case 29

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing paired PID allocation" "$stderr_file" "$rc" 'missing LARCH_PAIRED_PID_FILE allocation for collect-agent-results.sh'

# 30 — bare export without same-fence mktemp allocation fails
reset_tree
write_md skills/bare-pid-export/SKILL.md <<'EOF'
# Case 30

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "bare paired PID export" "$stderr_file" "$rc" 'missing LARCH_PAIRED_PID_FILE allocation for collect-agent-results.sh'

# 31 — allocation without monitor flag fails
reset_tree
write_md skills/missing-pid-flag/SKILL.md <<'EOF'
# Case 31

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing paired PID monitor flag" "$stderr_file" "$rc" 'missing --paired-pid-file monitor argument for collect-agent-results.sh'

# 31b — missing breadcrumb monitor fails before the missing-wait check.
reset_tree
write_md skills/missing-monitor/SKILL.md <<'EOF'
# Case 31b

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
wait "$COLLECTOR_PID"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing breadcrumb monitor" "$stderr_file" "$rc" 'missing breadcrumb-monitor.sh after top-level Family B writer collect-agent-results.sh'

# 32 — top-level Family B happy path with allocation and monitor flag
reset_tree
write_md skills/pid-happy/SKILL.md <<'EOF'
# Case 32

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "paired PID happy path" "$stderr_file" "$rc"

# 32b — run-step2-dispatch.sh keeps the top-level paired PID requirements.
reset_tree
write_md skills/pid-step2-dispatch/SKILL.md <<'EOF'
# Case 32b

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/run-step2-dispatch.sh --help &
RUN_STEP2_DISPATCH_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$RUN_STEP2_DISPATCH_PID"
else
    wait "$RUN_STEP2_DISPATCH_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "run-step2-dispatch paired PID happy path" "$stderr_file" "$rc"

# 33 — nested-only denylisted basenames keep the background pair but do not
# require paired PID allocation/flag.
for nested_bn in ci-wait.sh review-and-fix.sh step2-implement.sh dispatch-with-waterfall.sh; do
    reset_tree
    write_md "skills/nested-${nested_bn}/SKILL.md" <<EOF
# Case 33 ${nested_bn}

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

\`\`\`bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
\${CLAUDE_PLUGIN_ROOT}/scripts/${nested_bn} --help
\${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u
\`\`\`
EOF
    rc="$(run_lint "$stderr_file")"
    assert_case_clean "nested-only ${nested_bn} without paired PID" "$stderr_file" "$rc"
done

# 34 — shell-script parent-unset rule catches literal invocation.
reset_tree
write_sh scripts/call-waterfall.sh <<'EOF'
#!/usr/bin/env bash
scripts/dispatch-with-waterfall.sh --help
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "parent unset literal missing" "$stderr_file" "$rc" 'missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested dispatch-with-waterfall.sh'

# 35 — shell-script parent-unset rule catches variable-backed invocation.
reset_tree
write_sh scripts/call-waterfall-var.sh <<'EOF'
#!/usr/bin/env bash
WATERFALL_SH="$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"
"$WATERFALL_SH" --help
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "parent unset variable missing" "$stderr_file" "$rc" 'missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested dispatch-with-waterfall.sh'

# 36 — default-expansion assignment is recognized.
reset_tree
write_sh skills/design/scripts/call-waterfall-default.sh <<'EOF'
#!/usr/bin/env bash
DISPATCH_WATERFALL_SH="${EXTERNAL:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"
_out=$("$DISPATCH_WATERFALL_SH" --help)
printf '%s\n' "$_out"
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "parent unset default-expansion variable missing" "$stderr_file" "$rc" 'missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested dispatch-with-waterfall.sh'

# 37 — unset 1, 3, and 5 non-blank non-comment lines before literal invocation passes.
for gap in 1 3 5; do
    reset_tree
    {
        printf '#!/usr/bin/env bash\n'
        printf 'unset LARCH_PAIRED_PID_FILE\n'
        i=1
        while [[ "$i" -lt "$gap" ]]; do
            printf 'x%s=%s\n' "$i" "$i"
            i=$((i + 1))
        done
        printf 'scripts/dispatch-with-waterfall.sh --help\n'
    } | write_sh "scripts/call-waterfall-gap-${gap}.sh"
    rc="$(run_lint "$stderr_file")"
    assert_case_clean "parent unset literal gap ${gap}" "$stderr_file" "$rc"
done

# 38 — unset within window before variable-backed invocation passes.
reset_tree
write_sh scripts/call-waterfall-var-ok.sh <<'EOF'
#!/usr/bin/env bash
WATERFALL_SH="$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"
unset LARCH_PAIRED_PID_FILE
one=1
two=2
"$WATERFALL_SH" --help
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "parent unset variable backed ok" "$stderr_file" "$rc"

# 39 — six non-blank non-comment lines is outside the boundary.
reset_tree
write_sh scripts/call-waterfall-far.sh <<'EOF'
#!/usr/bin/env bash
unset LARCH_PAIRED_PID_FILE
a=1
b=2
c=3
d=4
e=5
f=6
scripts/dispatch-with-waterfall.sh --help
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "parent unset too far" "$stderr_file" "$rc" 'missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested dispatch-with-waterfall.sh'

# 40 — inline suppression permits an exceptional invocation.
reset_tree
write_sh scripts/call-waterfall-suppressed.sh <<'EOF'
#!/usr/bin/env bash
scripts/dispatch-with-waterfall.sh --help # lint-foreground-markers: ok fixture
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "parent unset suppressed" "$stderr_file" "$rc"

# 41 — test scripts and diagnostic --tool strings are not shell anchors.
reset_tree
write_sh scripts/test-waterfall-fixture.sh <<'EOF'
#!/usr/bin/env bash
scripts/dispatch-with-waterfall.sh --help
EOF
write_sh scripts/diagnostic-tool-string.sh <<'EOF'
#!/usr/bin/env bash
bash scripts/append-tool-failure.sh --tool "dispatch-with-waterfall.sh"
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "parent unset carve outs" "$stderr_file" "$rc"

# 42 — contradictory post-fence prose after a background+monitor fence fails.
reset_tree
write_md skills/post-fence/SKILL.md <<'EOF'
# Case 42

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```

Use `timeout: 1000`. Do NOT set `run_in_background: true`.
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "post-fence contradiction" "$stderr_file" "$rc" 'contradictory post-fence prose "Do NOT set run_in_background: true" after background+monitor fence'

# 43 — valid post-fence prose is accepted.
reset_tree
write_md skills/post-fence-ok/SKILL.md <<'EOF'
# Case 43

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```

Use `run_in_background: true` and wait on the paired monitor.
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "post-fence valid prose" "$stderr_file" "$rc"

# 44 — post-fence contradiction suppression is accepted.
reset_tree
write_md skills/post-fence-suppressed/SKILL.md <<'EOF'
# Case 44

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1 x.txt &
COLLECTOR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$COLLECTOR_PID"
else
    wait "$COLLECTOR_PID" 2>/dev/null || true
fi
```

Do NOT set `run_in_background: true`. # lint-foreground-markers: ok fixture
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "post-fence contradiction suppressed" "$stderr_file" "$rc"

# 45 — multiline top-level writer with canonical PID wait passes.
reset_tree
write_md skills/multiline-wait/SKILL.md <<'EOF'
# Case 45

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh \
  --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
  --repo "$REPO" &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
  writer_rc=0
  wait "$SHIP_PR_PID" || writer_rc=$?
  exit "$writer_rc"
else
  wait "$SHIP_PR_PID" 2>/dev/null || true
  exit "$monitor_rc"
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "multiline ship-pr PID wait" "$stderr_file" "$rc"

# 46 — local PID capture in shell file passes.
reset_tree
write_sh scripts/local-pid-capture.sh <<'EOF'
#!/usr/bin/env bash
run_pair() {
    "${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" --dry-run &
    local SHIP_PR_PID=$!
    local monitor_rc=0
    "${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" --stream s || monitor_rc=$?
    if [ "$monitor_rc" -eq 0 ]; then
        wait "$SHIP_PR_PID"
    else
        wait "$SHIP_PR_PID" 2>/dev/null || true
    fi
}
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "local PID capture in shell file" "$stderr_file" "$rc"

# 47 — all accepted wait forms pass.
# shellcheck disable=SC2016 # Literal wait forms are fixture text.
for wait_form in 'wait "$SHIP_PR_PID"' 'wait $SHIP_PR_PID' 'wait "${SHIP_PR_PID}"'; do
    reset_tree
    write_md skills/wait-form/SKILL.md <<EOF
# Case 47

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

\`\`\`bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="\$(mktemp "\$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
\${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=\$!
monitor_rc=0
\${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "\$LARCH_PAIRED_PID_FILE" || monitor_rc=\$?
if [ "\$monitor_rc" -eq 0 ]; then
    ${wait_form}
else
    wait "\$SHIP_PR_PID" 2>/dev/null || true
fi
\`\`\`
EOF
    rc="$(run_lint "$stderr_file")"
    assert_case_clean "wait form ${wait_form}" "$stderr_file" "$rc"
done

# 48 — missing wait fails.
reset_tree
write_md skills/missing-wait/SKILL.md <<'EOF'
# Case 48

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing PID wait" "$stderr_file" "$rc" 'missing wait'

# 49 — missing PID capture fails.
reset_tree
write_md skills/missing-pid-capture/SKILL.md <<'EOF'
# Case 49

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing PID capture" "$stderr_file" "$rc" 'missing PID capture'

# 50 — wait before monitor fails.
reset_tree
write_md skills/wait-before-monitor/SKILL.md <<'EOF'
# Case 50

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
wait "$SHIP_PR_PID"
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "wait before monitor" "$stderr_file" "$rc" 'wait must follow breadcrumb-monitor.sh'

# 51 — missing shell ampersand fails.
reset_tree
write_md skills/missing-amp/SKILL.md <<'EOF'
# Case 51

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing shell ampersand" "$stderr_file" "$rc" 'missing shell ampersand'

# 52 — wait/capture identifier mismatch fails.
reset_tree
write_md skills/wait-mismatch/SKILL.md <<'EOF'
# Case 52

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$OTHER_PID"
else
    wait "$OTHER_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "wait identifier mismatch" "$stderr_file" "$rc" 'does not match captured PID variable'

# 53 — nested Family B child remains exempt from PID wait.
reset_tree
write_md skills/nested-pid-wait-exempt/SKILL.md <<'EOF'
# Case 53

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
${CLAUDE_PLUGIN_ROOT}/scripts/review-and-fix.sh --help
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "nested Family B child unchanged" "$stderr_file" "$rc"

# 54 — missing monitor_rc init/capture/branch reports all three defects.
reset_tree
write_md skills/monitor-rc-none/SKILL.md <<'EOF'
# Case 54

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
wait "$SHIP_PR_PID"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing monitor_rc tokens" "$stderr_file" "$rc" \
    'missing monitor_rc= initialization' \
    'missing "|| monitor_rc=$?"' \
    'missing conditional branching on monitor_rc'

# 55 — monitor_rc capture without a branch is rejected.
reset_tree
write_md skills/monitor-rc-no-branch/SKILL.md <<'EOF'
# Case 55

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
wait "$SHIP_PR_PID"
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing monitor_rc branch" "$stderr_file" "$rc" 'missing conditional branching on monitor_rc'

# 56 — monitor_rc inside a heredoc body does not satisfy the init window.
reset_tree
write_md skills/monitor-rc-heredoc/SKILL.md <<'EOF'
# Case 56

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
cat <<'SCRIPT'
monitor_rc=0
SCRIPT
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "heredoc monitor_rc init ignored" "$stderr_file" "$rc" 'missing monitor_rc= initialization'
assert_stderr_lacks "heredoc monitor_rc init ignored" "$stderr_file" \
    'missing "|| monitor_rc=$?"' \
    'missing conditional branching on monitor_rc'

# 57 — shell-file top-level writer also requires monitor_rc initialization.
reset_tree
write_sh scripts/shell-missing-monitor-rc.sh <<'EOF'
#!/usr/bin/env bash
run_pair() {
    "${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" --dry-run &
    local SHIP_PR_PID=$!
    "${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" --stream s || monitor_rc=$?
    if [ "$monitor_rc" -eq 0 ]; then
        wait "$SHIP_PR_PID"
    else
        wait "$SHIP_PR_PID" 2>/dev/null || true
    fi
}
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "shell file missing monitor_rc init" "$stderr_file" "$rc" 'missing monitor_rc= initialization'

# 58 — backslash-continued breadcrumb-monitor capture is accepted.
reset_tree
write_md skills/monitor-rc-backslash-capture/SKILL.md <<'EOF'
# Case 58

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh \
  --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
  || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "backslash-continued monitor_rc capture" "$stderr_file" "$rc"

# 59 — init and branch without monitor_rc capture still fails.
reset_tree
write_md skills/monitor-rc-missing-capture/SKILL.md <<'EOF'
# Case 59

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE"
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "missing monitor_rc capture only" "$stderr_file" "$rc" 'missing "|| monitor_rc=$?"'
assert_stderr_lacks "missing monitor_rc capture only" "$stderr_file" \
    'missing monitor_rc= initialization' \
    'missing conditional branching on monitor_rc'

# 60 — decorative conditional plus comment does not satisfy monitor_rc branching.
reset_tree
write_md skills/monitor-rc-decorative-conditional/SKILL.md <<'EOF'
# Case 60

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
wait "$SHIP_PR_PID"
if true; then
    :
fi
# monitor_rc
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "decorative conditional monitor_rc bypass rejected" "$stderr_file" "$rc" 'missing conditional branching on monitor_rc'

# 61 — multiline monitor_rc if opener is accepted.
reset_tree
write_md skills/monitor-rc-multiline-if/SKILL.md <<'EOF'
# Case 61

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if \
    [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "multiline if monitor_rc branch" "$stderr_file" "$rc"

# 62 — comment-only monitor_rc on conditional opener does not satisfy the branch.
reset_tree
write_md skills/monitor-rc-comment-only-branch/SKILL.md <<'EOF'
# Case 62

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if true; then # monitor_rc
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "comment-only monitor_rc conditional rejected" "$stderr_file" "$rc" 'missing conditional branching on monitor_rc'

# 63 — monitor_rc init four non-blank lines above the monitor is rejected.
reset_tree
write_md skills/monitor-rc-init-too-far/SKILL.md <<'EOF'
# Case 63

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
tmp_one=1
tmp_two=2
tmp_three=3
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "monitor_rc init too far above monitor" "$stderr_file" "$rc" 'missing monitor_rc= initialization'
assert_stderr_lacks "monitor_rc init too far above monitor" "$stderr_file" \
    'missing "|| monitor_rc=$?"' \
    'missing conditional branching on monitor_rc'

# 64 — later valid elif monitor_rc branch is accepted after an unrelated if.
reset_tree
write_md skills/monitor-rc-elif-later/SKILL.md <<'EOF'
# Case 64

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if true; then
    :
elif [ "$monitor_rc" -eq 0 ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "later elif monitor_rc branch" "$stderr_file" "$rc"

# 65 — case "$monitor_rc" in is accepted.
reset_tree
write_md skills/monitor-rc-case/SKILL.md <<'EOF'
# Case 65

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
case "$monitor_rc" in
    (0)
        wait "$SHIP_PR_PID"
        ;;
    (*)
        wait "$SHIP_PR_PID" 2>/dev/null || true
        ;;
esac
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_clean "case monitor_rc branch" "$stderr_file" "$rc"

# 66 — quoted literal monitor_rc text does not satisfy the branch check.
reset_tree
write_md skills/monitor-rc-literal-text/SKILL.md <<'EOF'
# Case 66

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
# Background pair required: see BASH_AUTHORING.md §4
# Tool JSON: run_in_background: true
LARCH_PAIRED_PID_FILE="$(mktemp "$IMPLEMENT_TMPDIR/breadcrumbs/fixture.pid.XXXXXX")"
export LARCH_PAIRED_PID_FILE
${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh --dry-run &
SHIP_PR_PID=$!
monitor_rc=0
${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
if [ "monitor_rc" = "monitor_rc" ]; then
    wait "$SHIP_PR_PID"
else
    wait "$SHIP_PR_PID" 2>/dev/null || true
fi
```
EOF
rc="$(run_lint "$stderr_file")"
assert_case_err "quoted literal monitor_rc rejected" "$stderr_file" "$rc" 'missing conditional branching on monitor_rc'

# 16 — Family A: minimum run_in_background: true counts on reference paths (sketch / dialectic / voting)
assert_family_count() {
    local path="$1" expected="$2" label="$3"
    local got
    got=$(grep -cF 'run_in_background: true' "$path" || true)
    if [[ "$got" -lt "$expected" ]]; then
        printf 'FAIL [family-a %s]: count decreased below floor %s, got %s (%s)\n' "$label" "$expected" "$got" "$path" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    printf 'PASS [family-a %s]\n' "$label"
    PASS=$((PASS + 1))
}

assert_family_count "$REPO_ROOT/skills/design/references/sketch-launch.md" 7 'sketch-launch.md'
assert_family_count "$REPO_ROOT/skills/design/references/dialectic-execution.md" 5 'dialectic-execution.md'
assert_family_count "$REPO_ROOT/skills/shared/voting-protocol.md" 3 'voting-protocol.md'
assert_family_count "$REPO_ROOT/skills/shared/dialectic-protocol.md" 3 'dialectic-protocol.md'

rm -f "$stderr_file"

printf 'Summary: %s passed, %s failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
