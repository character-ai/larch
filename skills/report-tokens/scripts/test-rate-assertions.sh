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
check "codex input 0.44"          'LARCH_RATE_CODEX_INPUT.*0\.44'
check "codex output 3.50"        'LARCH_RATE_CODEX_OUTPUT.*3\.50'
check "codex aggregate 2.00"      'LARCH_RATE_CODEX_AGGREGATE.*2\.00'
check "codex cache_read 0.04"     'LARCH_RATE_CODEX_CACHE_READ.*0\.04'
check "cursor input 1.25"         'LARCH_RATE_CURSOR_INPUT.*1\.25'
check "cursor output 6.00"        'LARCH_RATE_CURSOR_OUTPUT.*6\.00'
check "cursor aggregate 1.50"     'LARCH_RATE_CURSOR_AGGREGATE.*1\.50'

TMPFILE=$(mktemp /tmp/test-rate-assertions.py.XXXXXX)
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
    ("codex", "input",       0.44),
    ("codex", "output",     3.50),
    ("codex", "aggregate",   2.00),
    ("codex", "cache_read",  0.04),
    ("cursor", "input",      1.25),
    ("cursor", "output",     6.00),
    ("cursor", "aggregate",  1.50),
]
for vendor, field, expected in expected_rates:
    if vendor not in RATES:
        failures.append(f"RATES missing vendor {vendor!r}")
    elif field not in RATES[vendor]:
        failures.append(f"RATES[{vendor!r}] missing field {field!r}")
    else:
        _check(f"RATES[{vendor!r}][{field!r}]", RATES[vendor][field], expected)

_check("codex agg 1M",      cost_vendor("codex",  {"input": 0, "output": 0, "total": 1_000_000}), 2.00)
_check("cursor input 1M",   cost_vendor("cursor", {"input": 1_000_000, "output": 0, "total": 1_000_000}), 1.25)

if failures:
    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    sys.exit(1)
print("All rate assertions passed.")
ASSERTIONS

python3 "$TMPFILE" || fail=1

[[ $fail -eq 0 ]] && echo "All checks passed." || exit 1
