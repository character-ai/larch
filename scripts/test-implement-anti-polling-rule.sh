#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011.
#
# Pins the anti-polling-loop literals in two files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops.
#   (2) skills/implement/SKILL.md: the Step 5.3-rounds1to3 launch site AND
#       the Step 5.3-generic launch site each carry an inline reminder that
#       collect-agent-results.sh is the wait point — contributors must NOT
#       add a Bash polling loop to wait on the launched reviewers.
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

# (2) skills/implement/SKILL.md: inline reminder at both Step 5.3 sites.
# Both sites must contain the exact phrase identifying collect-agent-results.sh
# as the wait point. We assert at least two occurrences (one per site).
SITE_LITERAL='Do NOT add a Bash polling loop to wait'
COUNT=$(grep -cF -- "$SITE_LITERAL" "$IMPL_MD" || true)
if [[ "$COUNT" -ge 2 ]]; then
    PASS=$((PASS + 1))
    echo "  PASS: SKILL.md Step 5.3-rounds1to3 + Step 5.3-generic carry inline reminder ($COUNT occurrences)"
else
    fail "SKILL.md Step 5.3 inline reminder count >= 2 (found $COUNT)" "$SITE_LITERAL"
fi

check "$IMPL_MD" \
    "SKILL.md cites collect-agent-results.sh as the wait point" \
    'collect-agent-results.sh` foreground call'

echo ""
echo "All $PASS assertions passed."
