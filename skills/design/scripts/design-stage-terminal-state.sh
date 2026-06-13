#!/usr/bin/env bash
# design-stage-terminal-state.sh — write strict /design terminal failure state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
REPORT_SH="$PLUGIN_ROOT/skills/implement/scripts/stall-recovery-report.sh"

# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

usage() {
    larch_err 'Usage: design-stage-terminal-state.sh --design-tmpdir DIR --outcome TOKEN --step TOKEN --phase TOKEN --site TOKEN --trigger TOKEN --bail-reason TOKEN --exit-code N|unknown --source-script TOKEN [--failure-detail-log PATH] [--root-cause-hint TOKEN] [--summary-outcome TOKEN] [--evidence-ref TOKEN]'
}

fail() { larch_err "design-stage-terminal-state.sh: $*"; exit 2; }

DESIGN_TMPDIR_ARG=""
OUTCOME=""
STEP=""
PHASE=""
SITE=""
TRIGGER=""
BAIL_REASON=""
EXIT_CODE=""
SOURCE_SCRIPT=""
FAILURE_DETAIL_LOG=""
ROOT_CAUSE_HINT=""
SUMMARY_OUTCOME=""
EVIDENCE_REF=""

while [ $# -gt 0 ]; do
    case "$1" in
        --design-tmpdir) [ $# -ge 2 ] || fail '--design-tmpdir requires a value'; DESIGN_TMPDIR_ARG=$2; shift 2 ;;
        --outcome) [ $# -ge 2 ] || fail '--outcome requires a value'; OUTCOME=$2; shift 2 ;;
        --step) [ $# -ge 2 ] || fail '--step requires a value'; STEP=$2; shift 2 ;;
        --phase) [ $# -ge 2 ] || fail '--phase requires a value'; PHASE=$2; shift 2 ;;
        --site) [ $# -ge 2 ] || fail '--site requires a value'; SITE=$2; shift 2 ;;
        --trigger) [ $# -ge 2 ] || fail '--trigger requires a value'; TRIGGER=$2; shift 2 ;;
        --bail-reason) [ $# -ge 2 ] || fail '--bail-reason requires a value'; BAIL_REASON=$2; shift 2 ;;
        --exit-code) [ $# -ge 2 ] || fail '--exit-code requires a value'; EXIT_CODE=$2; shift 2 ;;
        --source-script) [ $# -ge 2 ] || fail '--source-script requires a value'; SOURCE_SCRIPT=$2; shift 2 ;;
        --failure-detail-log) [ $# -ge 2 ] || fail '--failure-detail-log requires a value'; FAILURE_DETAIL_LOG=$2; shift 2 ;;
        --root-cause-hint) [ $# -ge 2 ] || fail '--root-cause-hint requires a value'; ROOT_CAUSE_HINT=$2; shift 2 ;;
        --summary-outcome) [ $# -ge 2 ] || fail '--summary-outcome requires a value'; SUMMARY_OUTCOME=$2; shift 2 ;;
        --evidence-ref) [ $# -ge 2 ] || fail '--evidence-ref requires a value'; EVIDENCE_REF=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; fail "unknown option: $1" ;;
    esac
done

[ -n "$DESIGN_TMPDIR_ARG" ] || fail '--design-tmpdir is required'
larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG" || exit $?
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"

for pair in "outcome:$OUTCOME" "step:$STEP" "phase:$PHASE" "site:$SITE" "trigger:$TRIGGER" "bail:$BAIL_REASON" "source-script:$SOURCE_SCRIPT"; do
    kind=${pair%%:*}
    value=${pair#*:}
    [ -n "$value" ] || fail "$kind is required"
    "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" \
        validate-token --token-kind "$kind" --value "$value" >/dev/null
 done
if [ -n "$ROOT_CAUSE_HINT" ]; then
    "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" \
        validate-token --token-kind root-cause --value "$ROOT_CAUSE_HINT" >/dev/null
fi
if [ -n "$SUMMARY_OUTCOME" ]; then
    "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" \
        validate-token --token-kind outcome --value "$SUMMARY_OUTCOME" >/dev/null
fi
case "$EXIT_CODE" in
    unknown) ;;
    ''|*[!0-9]*) fail '--exit-code must be an integer or unknown' ;;
    *) ;;
esac

if [ -n "$FAILURE_DETAIL_LOG" ]; then
    case "$FAILURE_DETAIL_LOG" in "$DESIGN_TMPDIR"/*) ;;
        *) fail '--failure-detail-log must be under --design-tmpdir' ;;
    esac
    [ -f "$FAILURE_DETAIL_LOG" ] || fail '--failure-detail-log must be a regular file'
    [ ! -L "$FAILURE_DETAIL_LOG" ] || fail '--failure-detail-log must not be a symlink'
    [ -r "$FAILURE_DETAIL_LOG" ] || fail '--failure-detail-log must be readable'
fi
case "$EVIDENCE_REF" in *$'\n'*|*$'\r'*|http://*|https://*|/*|*'..'*|*' '*|*'`'*) fail '--evidence-ref is not a safe token' ;; esac

STATE_FILE="$DESIGN_TMPDIR/design-failure-terminal-state.env"
if [ -e "$STATE_FILE" ]; then
    if [ -L "$STATE_FILE" ] || [ ! -f "$STATE_FILE" ]; then
        fail 'existing terminal state is unsafe'
    fi
    old_outcome=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$STATE_FILE" --key FAILURE_OUTCOME --default '')
    old_site=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$STATE_FILE" --key SITE --default '')
    old_trigger=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$STATE_FILE" --key TRIGGER --default '')
    if [ "$old_outcome" != "$OUTCOME" ] || [ "$old_site" != "$SITE" ] || [ "$old_trigger" != "$TRIGGER" ]; then
        emit_kv STAGED false
        emit_kv PRESERVED true
        emit_kv TERMINAL_STATE_FILE "$STATE_FILE"
        exit 0
    fi
fi

candidate="$DESIGN_TMPDIR/design-failure-terminal-state.env.candidate.$$"
{
    printf 'DESIGN_FAILURE_VERSION=1\n'
    printf 'DESIGN_FAILURE_KIND=terminal\n'
    printf 'FAILURE_OUTCOME=%s\n' "$OUTCOME"
    printf 'STALL_STEP=%s\n' "$STEP"
    printf 'PHASE=%s\n' "$PHASE"
    printf 'SITE=%s\n' "$SITE"
    printf 'TRIGGER=%s\n' "$TRIGGER"
    printf 'BAIL_REASON=%s\n' "$BAIL_REASON"
    printf 'EXIT_CODE=%s\n' "$EXIT_CODE"
    printf 'FAILURE_DETAIL_LOG=%s\n' "$FAILURE_DETAIL_LOG"
    printf 'SOURCE_SCRIPT=%s\n' "$SOURCE_SCRIPT"
    [ -z "$ROOT_CAUSE_HINT" ] || printf 'ROOT_CAUSE_HINT=%s\n' "$ROOT_CAUSE_HINT"
    [ -z "$SUMMARY_OUTCOME" ] || printf 'SUMMARY_OUTCOME=%s\n' "$SUMMARY_OUTCOME"
    printf 'OCCURRED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    [ -z "$EVIDENCE_REF" ] || printf 'EVIDENCE_REF=%s\n' "$EVIDENCE_REF"
} >"$candidate"

"$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" \
    validate-terminal-state --primary-state-file "$candidate" >/dev/null
mv -f "$candidate" "$STATE_FILE"
emit_kv STAGED true
emit_kv TERMINAL_STATE_FILE "$STATE_FILE"
