#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011 /
# issue #2749 (FINDING_24 inversion), and issue #4268.
#
# Pins the anti-polling-loop, Monitor-ban, and recovery-contract literals
# in four files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops, plus the
#       foreground-terminal-sentinel-probe primary recovery guidance and the
#       background-recovery-waiter ban (#4725).
#   (2) skills/implement/SKILL.md: Step 5 delegates reviewer waiting to
#       skills/implement/scripts/step-5-review.sh (no ad-hoc polling loops), and
#       the NEVER list bans Monitor fallback for one-shot completion while
#       keeping implement premature-notification recovery notification-driven.
#   (3) skills/design/SKILL.md: both Step 3 immediate-background fences carry
#       the result-file sleep-loop ban and consequence prose, and the
#       Anti-patterns list bans Monitor fallback for one-shot completion.
#   (4) skills/shared/orchestrator-never.md: the shared NEVER list carries the
#       run_in_background result-file sleep-loop ban, foreground-terminal-
#       sentinel-probe primary recovery guidance, and the background-recovery-
#       waiter ban (#4725).
#
# Wired into `make lint` via the `test-implement-anti-polling-rule` target.
# Runtime enforcement is the model-level reading of the prose; this harness
# is a CI guard against accidental literal removal.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AGENTS_MD="$REPO_ROOT/AGENTS.md"
IMPL_MD="$REPO_ROOT/skills/implement/SKILL.md"
DESIGN_MD="$REPO_ROOT/skills/design/SKILL.md"
ORCH_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"

STEP3_LITERAL='NEVER poll `.step3-review-result.env` with a sleep loop.'
ORCH_NEVER_LITERAL='NEVER poll a `run_in_background` result file with a Bash sleep loop.'

PASS=0
fail() { echo "  FAIL: $1" >&2; echo "    missing literal: $2" >&2; exit 1; }
fail_count() {
    echo "  FAIL: $1" >&2
    echo "    expected count: $2" >&2
    echo "    actual count: $3" >&2
    exit 1
}
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
[[ -f "$DESIGN_MD" ]] || { echo "ERROR: SKILL.md not found: $DESIGN_MD" >&2; exit 1; }
[[ -f "$ORCH_NEVER_MD" ]] || { echo "ERROR: orchestrator-never.md not found: $ORCH_NEVER_MD" >&2; exit 1; }

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
check "$AGENTS_MD" \
    "AGENTS.md bans per-turn output-file polling while a run_in_background task runs" \
    'poll the task output file once per turn'

check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes **one** `skills/implement/scripts/step-5-review.sh`'

step3_count=$(grep -cF -- "$STEP3_LITERAL" "$DESIGN_MD" || true)
if [[ "$step3_count" == "2" ]]; then
    PASS=$((PASS + 1))
    echo "  PASS: /design Step 3 initial and resume --starting-round fences ban result-file sleep-loop polling"
else
    fail_count "/design Step 3 literal must appear at both required sites: initial Step 3 and resume --starting-round" "2" "$step3_count"
fi

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER bans result-file sleep-loop polling" \
    "$ORCH_NEVER_LITERAL"

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins foreground-probe primary recovery guidance" \
    'the sanctioned recovery path is one foreground terminal-sentinel probe per explicit recovery turn'

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$AGENTS_MD" \
    "AGENTS.md pins foreground-probe primary recovery guidance" \
    'the sanctioned recovery path is one foreground non-sleeping'

check "$AGENTS_MD" \
    "AGENTS.md bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$AGENTS_MD" \
    "AGENTS.md documents the notification-refire platform assumption" \
    'the backgrounded task reliably re-fires a `<task-notification>` on completion'

check "$AGENTS_MD" \
    "AGENTS.md pins foreground terminal-sentinel probe form" \
    'one foreground non-sleeping `[ -f … ]` or `test -f …` probe against the relevant terminal completion sentinel'

check "$IMPL_MD" \
    "SKILL.md NEVER list explicitly bans Monitor tool in /implement orchestrator" \
    'NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator'

check "$IMPL_MD" \
    "SKILL.md NEVER list keeps implement premature-notification recovery notification-driven" \
    'end the turn and wait for the next `<task-notification>`; do not probe `$DESIGN_TMPDIR` or design-only sentinels'

check "$IMPL_MD" \
    "SKILL.md NEVER list documents absent implement terminal sentinels" \
    '/implement` does not write `$IMPLEMENT_TMPDIR/.completed/*-terminal` sentinels today'

check "$IMPL_MD" \
    "SKILL.md NEVER list pins intentional /implement vs /design recovery asymmetry" \
    '/implement` notification-only recovery and `/design` foreground terminal-sentinel probing are intentionally different contracts, not contradictory guidance.'

check "$IMPL_MD" \
    "SKILL.md NEVER list bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$IMPL_MD" \
    "SKILL.md NEVER list tells /implement not to fall back to Monitor" \
    'Do NOT fall back to Monitor'

check "$DESIGN_MD" \
    "/design Anti-patterns explicitly bans Monitor tool" \
    'NEVER use the `Monitor` tool anywhere within the `/design` orchestrator'

check "$DESIGN_MD" \
    "/design Anti-patterns pins foreground-probe primary recovery guidance" \
    'the sanctioned recovery path is one foreground, non-sleeping terminal-sentinel probe per recovery turn'

check "$DESIGN_MD" \
    "/design Anti-patterns bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$DESIGN_MD" \
    "/design Anti-patterns pins Step 3 terminal sentinel for the foreground recovery probe" \
    'Step 3-specific recovery note: the completion condition MUST be `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`; it MUST NOT be `.step3-review-result.env`.'

check "$DESIGN_MD" \
    "/design Anti-patterns pins foreground terminal-sentinel probe" \
    'Foreground terminal-sentinel probe: after a premature notification with non-empty task output'

check "$AGENTS_MD" \
    "AGENTS.md pins DESIGN_TMPDIR prefix for foreground probes" \
    'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins DESIGN_TMPDIR prefix for foreground probes" \
    'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$DESIGN_MD" \
    "/design Anti-patterns pins DESIGN_TMPDIR prefix for foreground probes" \
    'prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$DESIGN_MD" \
    "/design Step 3 requires terminal sentinel before envelope parse" \
    'Before parsing the envelope after notification, require `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`'

check "$DESIGN_MD" \
    "/design Step 3 requires step-3 sentinel before Step 3b routing" \
    'Before routing to Step 3b or later, additionally require `[ -f "$DESIGN_TMPDIR/.completed/step-3" ]`'

check "$DESIGN_MD" \
    "/design Anti-patterns tells orchestrator not to fall back to Monitor" \
    'Do NOT fall back to Monitor'

echo ""
echo "All $PASS assertions passed."
