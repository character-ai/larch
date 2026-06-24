#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011 /
# issue #2749 (FINDING_24 inversion), issue #4268, and the /design
# background-wait shared-anchor extraction.
#
# Pins the anti-polling-loop, Monitor-ban, and recovery-contract literals
# in five files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops, plus the
#       foreground-terminal-sentinel-probe primary recovery guidance and the
#       background-recovery-waiter ban (#4725).
#   (2) skills/implement/SKILL.md: Step 5 delegates reviewer waiting to
#       skills/implement/scripts/step-5-review.sh (no ad-hoc polling loops), and
#       the NEVER list bans Monitor fallback for one-shot completion while
#       keeping implement premature-notification recovery notification-driven.
#   (3) skills/shared/design-background-wait.md: the /design Step 3
#       result-file sleep-loop ban, task-notification boundary, and compact
#       table post-notification sequence live in the shared anchor.
#   (4) skills/design/SKILL.md: each /design background wait hot path carries
#       an imperative Read-and-apply load contract for the shared anchor while
#       retaining local sentinel and routing guards.
#   (5) skills/shared/orchestrator-never.md: the shared NEVER list carries the
#       run_in_background result-file sleep-loop ban, foreground-terminal-
#       sentinel-probe primary recovery guidance, and the background-recovery-
#       waiter ban (#4725).
#
# Wired into `make lint` via the `test-implement-anti-polling-rule` target.
# Runtime enforcement is the model-level reading of the prose; this harness
# is a CI guard against accidental literal removal or boilerplate drift.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AGENTS_MD="$REPO_ROOT/AGENTS.md"
IMPL_MD="$REPO_ROOT/skills/implement/SKILL.md"
DESIGN_MD="$REPO_ROOT/skills/design/SKILL.md"
SHARED_DESIGN_WAIT_MD="$REPO_ROOT/skills/shared/design-background-wait.md"
ORCH_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"

STEP3_LITERAL='NEVER poll `.step3-review-result.env` with a sleep loop.'
ORCH_NEVER_LITERAL='NEVER poll a `run_in_background` result file with a Bash sleep loop.'
SHARED_REF='skills/shared/design-background-wait.md'
LOAD_LITERAL='Read and apply ##'
CONFIRMATION_COMPLETION='confirmation purpose: completion'

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
check_count() {
    local file="$1" label="$2" literal="$3" expected="$4" actual
    actual=$(grep -cF -- "$literal" "$file" || true)
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "  PASS: $label"
    else
        fail_count "$label" "$expected" "$actual"
    fi
}
context_after() {
    local file="$1" anchor="$2" lines="$3"
    awk -v anchor="$anchor" -v max="$lines" '
        !seen && index($0, anchor) { found = 1; seen = 1; count = 0 }
        found && count < max { print; count++; if (count >= max) exit }
    ' "$file"
}
check_context() {
    local file="$1" label="$2" anchor="$3" lines="$4" literal="$5" context
    context=$(context_after "$file" "$anchor" "$lines")
    if printf '%s\n' "$context" | grep -qF -- "$literal"; then
        PASS=$((PASS + 1))
        echo "  PASS: $label"
    else
        fail "$label" "$literal"
    fi
}

[[ -f "$AGENTS_MD" ]] || { echo "ERROR: AGENTS.md not found: $AGENTS_MD" >&2; exit 1; }
[[ -f "$IMPL_MD"   ]] || { echo "ERROR: SKILL.md not found: $IMPL_MD" >&2; exit 1; }
[[ -f "$DESIGN_MD" ]] || { echo "ERROR: SKILL.md not found: $DESIGN_MD" >&2; exit 1; }
[[ -f "$SHARED_DESIGN_WAIT_MD" ]] || { echo "ERROR: design-background-wait.md not found: $SHARED_DESIGN_WAIT_MD" >&2; exit 1; }
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

# (3)/(4) /design shared wait extraction and load contracts.
check_count "$DESIGN_MD" \
    "/design no longer carries the Step 3 result-file polling literal" \
    "$STEP3_LITERAL" \
    "0"
check_count "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor carries the Step 3 result-file polling literal once" \
    "$STEP3_LITERAL" \
    "1"

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor bans Step 3 result-file sleep-loop polling" \
    "$STEP3_LITERAL"
check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'
check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor pins the compact-table missing warning" \
    '**⚠ Reviewer status table omitted: pre-rendered table not found.**'

check_context "$DESIGN_MD" \
    "/design Verbosity Control references the shared wait anchor" \
    '**Post-notification for Step 3 waits**' \
    "8" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Verbosity Control uses the Step 3 post-notification load contract" \
    '**Post-notification for Step 3 waits**' \
    "8" \
    "$LOAD_LITERAL Step 3 post-notification sequence"

check_context "$DESIGN_MD" \
    "/design Final summary block references the shared wait anchor" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Final summary block uses the immediate-background load contract" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$LOAD_LITERAL Immediate-background wait rule"
check_context "$DESIGN_MD" \
    "/design Final summary block pins completion confirmation purpose" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$CONFIRMATION_COMPLETION"

STEP3_LAUNCH_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh'
STEP3_RESUME_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh --starting-round'
STEP5C_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh'

check_context "$DESIGN_MD" \
    "/design Step 3 launch references the shared wait anchor" \
    "$STEP3_LAUNCH_ANCHOR" \
    "20" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Step 3 launch loads the task notification boundary" \
    "$STEP3_LAUNCH_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Step 3 task notification boundary"
check_context "$DESIGN_MD" \
    "/design Step 3 launch loads the immediate-background rule" \
    "$STEP3_LAUNCH_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Immediate-background wait rule"
check_context "$DESIGN_MD" \
    "/design Step 3 launch loads the post-notification sequence" \
    "$STEP3_LAUNCH_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Step 3 post-notification sequence"
check_context "$DESIGN_MD" \
    "/design Step 3 launch keeps the terminal sentinel parameter" \
    "$STEP3_LAUNCH_ANCHOR" \
    "20" \
    '.completed/step-3-terminal'

check_context "$DESIGN_MD" \
    "/design Step 3 resume references the shared wait anchor" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Step 3 resume loads the task notification boundary" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Step 3 task notification boundary"
check_context "$DESIGN_MD" \
    "/design Step 3 resume loads the immediate-background rule" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Immediate-background wait rule"
check_context "$DESIGN_MD" \
    "/design Step 3 resume loads the post-notification sequence" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    "$LOAD_LITERAL Step 3 post-notification sequence"
check_context "$DESIGN_MD" \
    "/design Step 3 resume keeps the terminal sentinel parameter" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    '.completed/step-3-terminal'

check_context "$DESIGN_MD" \
    "/design Step 5c references the shared wait anchor" \
    "$STEP5C_ANCHOR" \
    "18" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Step 5c uses the immediate-background load contract" \
    "$STEP5C_ANCHOR" \
    "18" \
    "$LOAD_LITERAL Immediate-background wait rule"
check_context "$DESIGN_MD" \
    "/design Step 5c pins completion confirmation purpose" \
    "$STEP5C_ANCHOR" \
    "18" \
    "$CONFIRMATION_COMPLETION"

check_count "$DESIGN_MD" \
    "/design no longer carries full immediate-background boilerplate paragraphs" \
    '**Immediate-background wait rule**:' \
    "0"
check_count "$DESIGN_MD" \
    "/design no longer carries the full Step 3 post-notification numbered sequence" \
    '1. **Completion gate**:' \
    "0"

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
