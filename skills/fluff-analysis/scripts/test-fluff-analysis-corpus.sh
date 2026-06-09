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

REPORT_FILE=$(mktemp "${TMPDIR:-/tmp}/fluff-corpus-report.XXXXXX")
trap 'rm -f "$REPORT_FILE"' EXIT
python3 "$ANALYZER" --log-root "$LOG_ROOT" --since-version 49.0.0 --min-group 1 > "$REPORT_FILE"
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
row = re.search(r"\| post \| latent \| \d+ \| ([0-9.]+)", text)
if row and float(row.group(1)) > 2.0:
    raise SystemExit("post latent acc above 2.0%")
low = re.search(r"post accepted-low-value: ([0-9.]+)%", text)
if not low:
    raise SystemExit("post accepted-low-value line missing")
if float(low.group(1)) >= 1.0:
    raise SystemExit("post accepted-low-value is not <1.0%")
PY
