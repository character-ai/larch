#!/usr/bin/env bash
# generate-code-flow-diagram.sh — generate and validate Step 7a code-flow Mermaid.
# shellcheck disable=SC2016

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: generate-code-flow-diagram.sh --implement-tmpdir PATH [--model claude-sonnet-4-6]"
}

fail_usage() {
    usage
    emit_kv STATUS failed
    emit_kv DIAGRAM_FILE ""
    emit_kv SKIP_REASON "$1"
    exit 2
}

IMPLEMENT_TMPDIR=""
MODEL="claude-sonnet-4-6"
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --model) [ $# -ge 2 ] || fail_usage "--model requires a value"; MODEL=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"
case "$IMPLEMENT_TMPDIR" in /*) ;; *) fail_usage "--implement-tmpdir must be absolute" ;; esac

"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 7a — code flow diagram" || true
"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7a — code flow diagram" || true
mkdir -p "$IMPLEMENT_TMPDIR" || {
    emit_kv STATUS failed
    emit_kv DIAGRAM_FILE ""
    emit_kv SKIP_REASON "tmpdir-unavailable"
    exit 1
}

prompt="$IMPLEMENT_TMPDIR/code-flow-prompt.md"
raw="$IMPLEMENT_TMPDIR/code-flow-diagram.raw.md"
candidate="$IMPLEMENT_TMPDIR/code-flow-diagram.candidate.md"
diagram="$IMPLEMENT_TMPDIR/code-flow-diagram.md"
sanitize_log="$IMPLEMENT_TMPDIR/code-flow-sanitizer.failure.log"

{
    printf '%s\n' 'Generate a concise Mermaid code-flow diagram for the committed implementation diff.'
    printf '%s\n' 'Return markdown containing exactly one `## Code Flow Diagram` heading and one mermaid fence.'
    printf '%s\n' 'Focus on runtime calls, data flow, and control flow. Avoid structural architecture duplication.'
    printf '\nChanged files:\n'
    git diff --name-only "$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD~1 2>/dev/null || printf HEAD)"..HEAD 2>/dev/null || true
} > "$prompt"

if ! "$PLUGIN_ROOT/scripts/launch-claude-subprocess.sh" \
    --model "$MODEL" \
    --prompt-file "$prompt" \
    --output-file "$raw" \
    --timeout 600 \
    --allow-root "$(pwd -P)" \
    --timing-task-kind implement-code-flow >"$IMPLEMENT_TMPDIR/code-flow-launch.out" 2>"$IMPLEMENT_TMPDIR/code-flow-launch.err"; then
    emit_kv STATUS failed
    emit_kv DIAGRAM_FILE ""
    emit_kv SKIP_REASON "generation-failed"
    exit 1
fi

if [ ! -s "$raw" ]; then
    emit_kv STATUS failed
    emit_kv DIAGRAM_FILE ""
    emit_kv SKIP_REASON "empty-generation"
    exit 1
fi

cp "$raw" "$candidate" || {
    emit_kv STATUS failed
    emit_kv DIAGRAM_FILE ""
    emit_kv SKIP_REASON "candidate-write-failed"
    exit 1
}

if "$PLUGIN_ROOT/scripts/sanitize-mermaid-fragment.sh" \
    --input "$candidate" \
    --from-md \
    --warnings-step "7a" >"$sanitize_log" 2>&1; then
    mv -f "$candidate" "$diagram"
    emit_kv STATUS ok
    emit_kv DIAGRAM_FILE "$diagram"
    emit_kv SKIP_REASON ""
    exit 0
fi

rm -f "$candidate"
emit_kv STATUS skipped
emit_kv DIAGRAM_FILE ""
emit_kv SKIP_REASON "$(awk -F= '$1=="REASON_TOKEN"{print $2; exit}' "$sanitize_log" 2>/dev/null || printf 'sanitizer-rejected')"
exit 0
