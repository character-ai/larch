#!/usr/bin/env bash
# test-rate-assertions.sh — Verify default rate values and cost_vendor outputs in run-analysis.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/run-analysis.sh"

fail=0
check() {
    local label="$1" pattern="$2"
    grep -qE "$pattern" "$SCRIPT" || { echo "FAIL: $label" >&2; fail=1; }
}
check "codex input 5.00"          'LARCH_RATE_CODEX_INPUT.*5\.00'
check "codex output 30.00"        'LARCH_RATE_CODEX_OUTPUT.*30\.00'
check "codex aggregate 5.00"      'LARCH_RATE_CODEX_AGGREGATE.*5\.00'
check "codex cache_read 0.50"     'LARCH_RATE_CODEX_CACHE_READ.*0\.50'
check "cursor input 0.50"         'LARCH_RATE_CURSOR_INPUT.*0\.50'
check "cursor output 2.50"        'LARCH_RATE_CURSOR_OUTPUT.*2\.50'
check "cursor aggregate 0.20"     'LARCH_RATE_CURSOR_AGGREGATE.*0\.20'
check "gemini vendor key"          '"gemini"'
check "gemini input 1.25"         'LARCH_RATE_GEMINI_INPUT.*1\.25'
check "gemini output 10.00"       'LARCH_RATE_GEMINI_OUTPUT.*10\.00'
check "gemini aggregate 1.25"     'LARCH_RATE_GEMINI_AGGREGATE.*1\.25'

TMPFILE=$(mktemp /tmp/test-rate-assertions.XXXXXX.py)
trap 'rm -f "$TMPFILE"' EXIT

# Extract the embedded Python from the heredoc, drop the __main__ guard (last 2 lines).
# SC2016: dollar-signs inside single-quoted sed patterns are intentional (not variable refs).
# shellcheck disable=SC2016
sed -n '/^cat > "\$ANALYZER" <<'"'"'PY'"'"'$/,/^PY$/{
    /^cat > "\$ANALYZER" <<'"'"'PY'"'"'$/d
    /^PY$/d
    p
}' "$SCRIPT" | awk 'NR>2{print p2} {p2=p1; p1=$0}' > "$TMPFILE"

cat >> "$TMPFILE" <<'ASSERTIONS'

import sys
failures = []

def _check(label, actual, expected):
    if abs(actual - expected) > 1e-9:
        failures.append(f"{label}: got {actual}, expected {expected}")

expected_rates = [
    ("codex", "input",       5.00),
    ("codex", "output",     30.00),
    ("codex", "aggregate",   5.00),
    ("codex", "cache_read",  0.50),
    ("cursor", "input",      0.50),
    ("cursor", "output",     2.50),
    ("cursor", "aggregate",  0.20),
    ("gemini", "input",      1.25),
    ("gemini", "output",    10.00),
    ("gemini", "aggregate",  1.25),
]
for vendor, field, expected in expected_rates:
    if vendor not in RATES:
        failures.append(f"RATES missing vendor {vendor!r}")
    elif field not in RATES[vendor]:
        failures.append(f"RATES[{vendor!r}] missing field {field!r}")
    else:
        _check(f"RATES[{vendor!r}][{field!r}]", RATES[vendor][field], expected)

_check("codex agg 1M",      cost_vendor("codex",  {"input": 0, "output": 0, "total": 1_000_000}), 5.00)
_check("cursor input 1M",   cost_vendor("cursor", {"input": 1_000_000, "output": 0, "total": 1_000_000}), 0.50)
_check("gemini input 1M",   cost_vendor("gemini", {"input": 1_000_000, "output": 0, "total": 1_000_000}), 1.25)
_check("gemini output 1M",  cost_vendor("gemini", {"input": 0, "output": 1_000_000, "total": 1_000_000}), 10.00)
_check("gemini agg 1M",     cost_vendor("gemini", {"input": 0, "output": 0, "total": 1_000_000}), 1.25)

if failures:
    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    sys.exit(1)
print("All rate assertions passed.")
ASSERTIONS

python3 "$TMPFILE" || fail=1

[[ $fail -eq 0 ]] && echo "All checks passed." || exit 1
