#!/usr/bin/env bash
# step-16-17.sh — /implement Steps 16-17 composed best-effort wrapper.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    if [ ! -d "$CLAUDE_PLUGIN_ROOT" ]; then
        printf 'step-16-17.sh: CLAUDE_PLUGIN_ROOT not found: %s\n' "$CLAUDE_PLUGIN_ROOT" >&2
        exit 2
    fi
    export CLAUDE_PLUGIN_ROOT
}

append_slack_warning() {
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "Step 16a — notify" \
        --tool "python/cli.py slack issue-announce" \
        --exit-code "$1" \
        --category "Warnings" \
        --output-file "$2" \
        --redact >/dev/null 2>&1 || true
}

print_summary_markers() {
    summary_path="$IMPLEMENT_TMPDIR/summary-final.md"
    printf '%s\n' '---LARCH-SUMMARY-FINAL-BEGIN---'
    if ! cat "$summary_path"; then
        return 1
    fi
    last_hex=$(tail -c 1 "$summary_path" 2>/dev/null | od -An -t x1 | tr -d ' \n')
    if [ "$last_hex" != "0a" ]; then
        printf '\n'
    fi
    printf '%s\n' '---LARCH-SUMMARY-FINAL-END---'
    touch "$IMPLEMENT_TMPDIR/.step17-printed"
}

rehydrate_plugin_root

set +e
"$SCRIPT_DIR/step-16.sh"

slack_log="$IMPLEMENT_TMPDIR/step16a-slack-issue-announce.log"
: >"$slack_log" 2>/dev/null
slack_rc=0
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" slack issue-announce --implement-tmpdir "$IMPLEMENT_TMPDIR" --best-effort >"$slack_log" 2>&1 || slack_rc=$?
if command grep -Fq 'STATUS=failed' "$slack_log"; then
    append_slack_warning "$slack_rc" "$slack_log"
fi

STEP17_RC=0
"$SCRIPT_DIR/step-17.sh" --no-print-stdout || STEP17_RC=$?
if [ "$STEP17_RC" -eq 0 ] && [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]; then
    print_summary_markers
fi

exit 0
