#!/usr/bin/env bash
# test-write-final-report.sh — /fix-issue write-final-report harness.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-fix-wfr.XXXXXX")"
TRACKING_LOG="$TMP_ROOT/tracking-invocations.log"
STDERR_CAP="$TMP_ROOT/stderr-cap.log"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

plugin="$TMP_ROOT/plugin"
mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/"
cp "$REPO_ROOT/scripts/render-run-summary.sh" "$plugin/scripts/"
cp "$REPO_ROOT/scripts/token-cost.sh" "$plugin/scripts/"
chmod +x "$plugin/scripts/render-run-summary.sh" "$plugin/scripts/token-cost.sh"
# Embed log path so the stub does not rely on TRACKING_LOG in the child environment.
cat > "$plugin/scripts/tracking-issue-summary.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$0 \$*" >> "$TRACKING_LOG"
printf 'COMMENT_URL=https://ex.example/c\n'
STUB
chmod +x "$plugin/scripts/tracking-issue-summary.sh"

run_case() {
    local name="$1" fixd="$2" expect_tracking="$3"
    : >"$TRACKING_LOG"
    : >"$STDERR_CAP"
    set +e
    out=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --fix-issue-tmpdir "$fixd" --print-stdout 2>"$STDERR_CAP")
    rc=$?
    set -e
    [ "$rc" = 0 ] || fail "$name: exit $rc"
    case "$out" in *'## /fix-issue'*) ;; *) fail "$name: missing header" ;; esac
    if [ "$expect_tracking" = "no" ]; then
        if [ -s "$TRACKING_LOG" ]; then
            fail "$name: tracking-issue-summary should not run (log nonempty)"
        fi
        grep -Fq 'STATUS=skipped' "$STDERR_CAP" || fail "$name: missing STATUS=skipped on stderr"
        grep -Fq 'REASON=fix-issue-summary-not-posted' "$STDERR_CAP" || fail "$name: missing REASON on stderr"
    else
        [ -s "$TRACKING_LOG" ] || fail "$name: tracking-issue-summary not invoked"
        grep -Fq 'STATUS=ok' "$STDERR_CAP" || fail "$name: missing STATUS=ok on stderr"
    fi
}

# --- Outcomes that skip GitHub upsert (terminal projection only) ---
for oc in pr-merged pr-open no-candidate lock-failed bailed-implement-failed bailed-adopted-issue-closed; do
    fixd="$TMP_ROOT/skip-$oc"
    mkdir -p "$fixd"
    printf 'ISSUE_NUMBER=42\nCLASSIFICATION=PR\nOUTCOME=%s\n' "$oc" >"$fixd/final-report-state.sh"
    printf 'REPO=own/r\nREPO_UNAVAILABLE=false\n' >"$fixd/session-env.sh"
    printf 'sid-%s\n' "$oc" >"$fixd/session-id"
    run_case "skip-upsert-$oc" "$fixd" no
    pass "skip-upsert-$oc"
done

# --- Outcomes that still attempt upsert (stub succeeds) ---
for oc in closed-non-pr closed-not-material; do
    fixd="$TMP_ROOT/up-$oc"
    mkdir -p "$fixd"
    printf 'ISSUE_NUMBER=7\nCLASSIFICATION=PR\nOUTCOME=%s\n' "$oc" >"$fixd/final-report-state.sh"
    printf 'REPO=own/r\nREPO_UNAVAILABLE=false\n' >"$fixd/session-env.sh"
    printf 'sid2\n' >"$fixd/session-id"
    run_case "upsert-$oc" "$fixd" yes
    pass "upsert-$oc"
done

# --- no-candidate + issue 0: stderr envelope (no tracking call) ---
fixd="$TMP_ROOT/nocand0"
mkdir -p "$fixd"
: >"$TRACKING_LOG"
: >"$STDERR_CAP"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --outcome no-candidate --issue-number 0 --print-stdout 2>"$STDERR_CAP")
case "$out" in *'no-candidate'*) ;; *) fail 'no-candidate issue 0 body' ;; esac
[ ! -s "$TRACKING_LOG" ] || fail 'no-candidate issue 0 should not invoke tracking'
grep -Fq 'STATUS=skipped' "$STDERR_CAP" || fail 'no-candidate 0 STATUS=skipped'
pass 'no-candidate issue-number 0'

# --- Non-numeric ISSUE fails before tracking (digits-only guard) ---
fixd="$TMP_ROOT/badissue"
mkdir -p "$fixd"
: >"$TRACKING_LOG"
: >"$STDERR_CAP"
set +e
CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --outcome closed-non-pr --issue-number 'xx' --print-stdout >/dev/null 2>"$STDERR_CAP"
rc=$?
set -e
[ "$rc" = 1 ] || fail "bad issue exit (got $rc)"
grep -Fq 'STATUS=failed' "$STDERR_CAP" || fail 'bad issue STATUS=failed'
grep -Fq 'ISSUE_NUMBER must be numeric' "$STDERR_CAP" || fail 'bad issue ERROR text'
[ ! -s "$TRACKING_LOG" ] || fail 'bad issue should not invoke tracking'
pass 'non-numeric ISSUE_NUMBER'

printf 'PASS=all-fix-issue-write-final-report-cases\n'
