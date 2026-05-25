#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011 /
# issue #2749 (FINDING_24 inversion).
#
# Pins the anti-polling-loop literals in two files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops.
#   (2) skills/implement/SKILL.md: Step 5 uses the background+monitor pair
#       (run-step5-review.sh background, breadcrumb-monitor.sh foreground in
#       the same Bash message). Every `run_in_background: true` line in the
#       Step 5 block MUST be paired with a `breadcrumb-monitor.sh` invocation
#       in the same Step 5 fenced sequence — keeps rejection of unpaired
#       polling loops while supporting the new Family-B background+propagate
#       contract.
#
# Wired into `make lint` via the `test-implement-anti-polling-rule` target.
# Runtime enforcement is the model-level reading of the prose; this harness
# is a CI guard against accidental literal removal.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AGENTS_MD="$REPO_ROOT/AGENTS.md"
IMPL_MD="$REPO_ROOT/skills/implement/SKILL.md"

PASS=0
fail() { echo "  FAIL: $1" >&2; echo "    missing literal: $2" >&2; exit 1; }
check() {
    local file="$1" label="$2" literal="$3"
    if grep -qF -- "$literal" "$file"; then
        PASS=$((PASS + 1))
        echo "  PASS: $label"
    else
        fail "$label" "$literal"
    fi
}

[[ -f "$AGENTS_MD" ]] || { echo "ERROR: AGENTS.md not found: $AGENTS_MD" >&2; exit 1; }
[[ -f "$IMPL_MD"   ]] || { echo "ERROR: SKILL.md not found: $IMPL_MD" >&2; exit 1; }

echo "Asserting anti-polling-rule literals (issue #1011)..."

# (1) AGENTS.md: extended bullet covers both forms.
check "$AGENTS_MD" \
    "AGENTS.md mentions Monitor in the rule" \
    "Don't spawn a Monitor or a Bash"
check "$AGENTS_MD" \
    "AGENTS.md cites Bash run_in_background polling loop" \
    'Bash `run_in_background` polling loop'
check "$AGENTS_MD" \
    "AGENTS.md cites the for/while/until + sleep pattern" \
    '`for`/`while`/`until` + `sleep`'

check "$IMPL_MD" \
    "SKILL.md Step 5 uses background+monitor pair" \
    'Step 5 invokes **one** background+monitor'
check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`'

STEP5_BLOCK=$(awk '
    /^<!-- step:5 / { in_block=1 }
    /^<!-- step:6 / { in_block=0 }
    in_block { print }
' "$IMPL_MD")
# FINDING_24 inversion: each `run_in_background: true` line in Step 5 must be
# paired with a `breadcrumb-monitor.sh` invocation in the same Step 5 block.
# Count instances of each literal; pairing requires monitor_count >= bg_count
# and bg_count > 0 (i.e. Step 5 actually launches via background+monitor).
BG_COUNT=$(printf '%s\n' "$STEP5_BLOCK" | grep -cF 'run_in_background: true' || true)
MON_COUNT=$(printf '%s\n' "$STEP5_BLOCK" | grep -cF 'breadcrumb-monitor.sh' || true)
if [[ "${BG_COUNT:-0}" -eq 0 ]]; then
    echo "  FAIL: SKILL.md Step 5 missing background+monitor pair (no 'run_in_background: true' line found)" >&2
    exit 1
fi
if [[ "${MON_COUNT:-0}" -lt "${BG_COUNT:-0}" ]]; then
    echo "  FAIL: SKILL.md Step 5 has ${BG_COUNT} background launch line(s) but only ${MON_COUNT} breadcrumb-monitor reference(s)" >&2
    echo "    every 'run_in_background: true' line must be paired with a 'breadcrumb-monitor.sh' invocation in the Step 5 block" >&2
    exit 1
fi
PASS=$((PASS + 1))
echo "  PASS: SKILL.md Step 5 background+monitor pair (${BG_COUNT} background, ${MON_COUNT} monitor references)"

echo ""
echo "All $PASS assertions passed."
