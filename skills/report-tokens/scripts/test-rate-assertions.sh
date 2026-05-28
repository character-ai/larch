#!/usr/bin/env bash
# test-rate-assertions.sh — Verify default rate values and cost_vendor outputs in run-analysis.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/run-analysis.sh"
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

fail=0
check() {
    local label="$1" pattern="$2"
    grep -qE -- "$pattern" "$SCRIPT" || { echo "FAIL: $label" >&2; fail=1; }
}
check "codex input 0.44"          'LARCH_RATE_CODEX_INPUT.*0\.44'
check "codex output 3.50"        'LARCH_RATE_CODEX_OUTPUT.*3\.50'
check "codex aggregate 2.00"      'LARCH_RATE_CODEX_AGGREGATE.*2\.00'
check "codex cache_read 0.04"     'LARCH_RATE_CODEX_CACHE_READ.*0\.04'
check "cursor input 1.25"         'LARCH_RATE_CURSOR_INPUT.*1\.25'
check "cursor output 6.00"        'LARCH_RATE_CURSOR_OUTPUT.*6\.00'
check "cursor aggregate 1.50"     'LARCH_RATE_CURSOR_AGGREGATE.*1\.50'
check "skill required guard"      '--skill is required \(allowed: design, implement\)'
check "skill enum guard"          '--skill must be design or implement'

TMPFILE=$(mktemp /tmp/test-rate-assertions.py.XXXXXX)
DESIGN_RUN="$REPO/larch-logs/design/CCCC-rate-assertions-design-fixture"
trap 'rm -f "$TMPFILE"; rm -rf "$DESIGN_RUN"' EXIT

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

rm -rf "$DESIGN_RUN"
mkdir -p "$DESIGN_RUN"
cp "$SCRIPT_DIR/fixtures/recompute-run/manifest.json" "$DESIGN_RUN/manifest.json"
cp "$SCRIPT_DIR/fixtures/recompute-run/token-report.json" "$DESIGN_RUN/token-report-final.json"
printf '%s\n' '{"workflow_path":"HARD"}' > "$DESIGN_RUN/timing-report-final.json"
design_out=$(LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$REPO" LARCH_REPORT_TOKENS_REPO=fixture/local \
    LARCH_REPORT_TOKENS_NO_ISSUE=1 LARCH_REPORT_TOKENS_NO_PLOT=1 \
    "$SCRIPT" --skill design)
case "$design_out" in
    *'#999001'*) ;;
    *) echo "FAIL: design fixture did not surface via -final reports" >&2; fail=1 ;;
esac

[[ $fail -eq 0 ]] && echo "All checks passed." || exit 1
