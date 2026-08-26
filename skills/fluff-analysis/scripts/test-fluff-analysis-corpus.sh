#!/usr/bin/env bash
# Smoke-check committed corpus post-v49 low-value acceptance when corpus exists.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SCRIPT_DIR/../../.." && pwd)}"
export CLAUDE_PLUGIN_ROOT
LOG_ROOT="$ROOT/larch-logs"

if [[ ! -d "$LOG_ROOT/implement" ]]; then
    echo "SKIP: no committed implement corpus at $LOG_ROOT" >&2
    exit 0
fi
# Skip on sparse checkouts where the larch-logs/ tree is present but the
# implement subdirectory is empty (no runs committed in this checkout).
# A full checkout should have at least one run directory under implement/.
_impl_count=0
while IFS= read -r _d; do
    [[ -d "$_d" ]] || continue
    _impl_count=$((_impl_count + 1))
    break
done < <(find "$LOG_ROOT/implement" -mindepth 1 -maxdepth 1 -type d 2>/dev/null || true)
if [[ "$_impl_count" -eq 0 ]]; then
    echo "SKIP: implement corpus directory is empty (sparse checkout?)" >&2
    exit 0
fi

REPORT_FILE=$(mktemp "${TMPDIR:-/tmp}/fluff-corpus-report.XXXXXX")
trap 'rm -f "$REPORT_FILE"' EXIT
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" fluff-analysis analyze --log-root "$LOG_ROOT" --since-version 49.0.0 --min-group 1 --post-only-tags > "$REPORT_FILE"
REPORT=$(cat "$REPORT_FILE")
if [[ "$REPORT" == *"| post | nit | 0 |"* || "$REPORT" != *"| post | nit |"* ]]; then
    echo "SKIP: no v>=49 post nit corpus slice" >&2
    exit 0
fi
acc="$(sed -nE 's/.*\| post \| nit \| [0-9]+ \| ([0-9.]+).*/\1/p' "$REPORT_FILE" | head -n 1)"
[[ -n "$acc" ]] || { echo "post nit row missing" >&2; exit 1; }
awk -v acc="$acc" 'BEGIN { if ((acc + 0) > 0.1 || (acc + 0) < -0.1) exit 1 }'
