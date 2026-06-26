#!/usr/bin/env bash
# Smoke-check committed corpus post-v49 low-value acceptance when corpus exists.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ANALYZER="$SCRIPT_DIR/fluff-analysis.py"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
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
python3 "$ANALYZER" --log-root "$LOG_ROOT" --since-version 49.0.0 --min-group 1 --post-only-tags > "$REPORT_FILE"
REPORT=$(cat "$REPORT_FILE")
if [[ "$REPORT" == *"| post | nit | 0 |"* || "$REPORT" != *"| post | nit |"* ]]; then
    echo "SKIP: no v>=49 post nit corpus slice" >&2
    exit 0
fi
python3 - "$REPORT_FILE" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
row = re.search(r"\| post \| nit \| \d+ \| ([0-9.]+)", text)
if not row:
    raise SystemExit("post nit row missing")
if abs(float(row.group(1)) - 0.0) > 0.1:
    raise SystemExit("post nit acc is not 0.0%")
PY
