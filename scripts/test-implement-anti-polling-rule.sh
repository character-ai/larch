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

# (2) skills/implement/SKILL.md: inline reminder at BOTH Step 5.3 sites.
# A global count is insufficient — duplicating the literal under one heading
# while dropping it under the other would still pass. Extract each
# heading-bounded block separately and grep within.
SITE_LITERAL='Do NOT add a Bash polling loop to wait'

# Block extraction: from "**5.3-<id>" up to (but not including) the next
# "**5.3" or "**5.4" boundary. The closing boundaries match the literal
# section markers in SKILL.md ("**5.3-generic", "**5.3.a", "**5.4 —").
extract_block() {
    local start_re="$1" file="$2"
    awk -v start="$start_re" '
        $0 ~ start { in_block=1; print; next }
        in_block && /^\*\*5\.(3|4)/ { in_block=0 }
        in_block { print }
    ' "$file"
}

ROUNDS_BLOCK=$(extract_block '^\*\*5\.3-rounds1to3' "$IMPL_MD")
GENERIC_BLOCK=$(extract_block '^\*\*5\.3-generic' "$IMPL_MD")

if [[ -z "$ROUNDS_BLOCK" ]]; then fail "SKILL.md Step 5.3-rounds1to3 block extraction" "**5.3-rounds1to3 heading"; fi
if [[ -z "$GENERIC_BLOCK" ]]; then fail "SKILL.md Step 5.3-generic block extraction"   "**5.3-generic heading"; fi

if grep -qF -- "$SITE_LITERAL" <<<"$ROUNDS_BLOCK"; then
    PASS=$((PASS + 1)); echo "  PASS: SKILL.md Step 5.3-rounds1to3 carries inline reminder"
else
    fail "SKILL.md Step 5.3-rounds1to3 missing inline reminder" "$SITE_LITERAL"
fi

if grep -qF -- "$SITE_LITERAL" <<<"$GENERIC_BLOCK"; then
    PASS=$((PASS + 1)); echo "  PASS: SKILL.md Step 5.3-generic carries inline reminder"
else
    fail "SKILL.md Step 5.3-generic missing inline reminder" "$SITE_LITERAL"
fi

check "$IMPL_MD" \
    "SKILL.md cites collect-agent-results.sh as the wait point" \
    'collect-agent-results.sh` foreground call'

echo ""
echo "All $PASS assertions passed."
