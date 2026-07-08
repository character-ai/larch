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
#   (4) skills/design/SKILL.md: /design background wait hot paths carry
#       shared-anchor contracts, with first-time Step 3 keeping the full
#       inline contract and Step 3 resume using a pinned back-reference.
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
SHARED_REF='skills/shared/bgjob-wait.md'
FINAL_SUMMARY_BGJOB_LITERAL='Use the shared bgjob wait contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/bgjob-wait.md` for Final summary launch, rejoin, `WAIT`, `DEAD`, and `DONE`.'
FINAL_SUMMARY_RESULT_ENV_LITERAL='result env `$DESIGN_TMPDIR/bgjob/design-step-final-summary.result.env`'
FINAL_SUMMARY_DONE_LITERAL='Only after `BGJOB_STATUS=DONE` with `BGJOB_RC=0` may Final summary parse `$DESIGN_TMPDIR/bgjob/design-step-final-summary.result.env`.'
RESUME_BACKREF_LITERAL='Use the same Step 3 bgjob start/rejoin, chunked `bgjob wait`, `BGJOB_RC=0`, result-env, and terminal-sentinel compatibility contract as the first-time Step 3 review fence above.'
DESIGN_EMPTY_OUTPUT_ANCHOR='5. **NEVER continue from bgjob transport success alone.'
SHARED_IMMEDIATE_WAIT_ANCHOR='After the background launch ack'

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
check_absent() {
    local file="$1" label="$2" literal="$3"
    if grep -qF -- "$literal" "$file"; then
        echo "  FAIL: $label" >&2
        echo "    forbidden literal present: $literal" >&2
        exit 1
    fi
    PASS=$((PASS + 1))
    echo "  PASS: $label"
}
context_after() {
    local file="$1" anchor="$2" lines="$3"
    awk -v anchor="$anchor" -v max="$lines" '
        !seen && index($0, anchor) { found = 1; seen = 1; count = 0 }
        found && count < max { print; count++; if (count >= max) exit }
    ' "$file"
}
context_before() {
    local file="$1" anchor="$2" lines="$3"
    awk -v anchor="$anchor" -v max="$lines" '
        { buf[NR] = $0 }
        END {
            for (i = 1; i <= NR; i++) {
                if (index(buf[i], anchor)) {
                    start = i - max
                    if (start < 1) start = 1
                    for (j = start; j < i; j++) print buf[j]
                    exit
                }
            }
        }
    ' "$file"
}
context_before_step3_launch() {
    local file="$1" lines="$2"
    awk -v max="$lines" '
        { buf[NR] = $0 }
        END {
            for (i = 1; i <= NR; i++) {
                if (index(buf[i], "design-run-$PPID.sh\" design-step3-review.sh") && index(buf[i], "--starting-round") == 0) {
                    start = i - max
                    if (start < 1) start = 1
                    for (j = start; j < i; j++) print buf[j]
                    exit
                }
            }
        }
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
check_context_before() {
    local file="$1" label="$2" anchor="$3" lines="$4" literal="$5" context
    context=$(context_before "$file" "$anchor" "$lines")
    if printf '%s\n' "$context" | grep -qF -- "$literal"; then
        PASS=$((PASS + 1))
        echo "  PASS: $label"
    else
        fail "$label" "$literal"
    fi
}
check_context_before_step3_launch() {
    local file="$1" label="$2" lines="$3" literal="$4" context
    context=$(context_before_step3_launch "$file" "$lines")
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
check "$AGENTS_MD" \
    "AGENTS.md pins /design empty-output no-probe clause with issue reference" \
    'For `/design`, missing or whitespace-only task-output bytes mean silent yield (spurious notification, #5240)'
check "$AGENTS_MD" \
    "AGENTS.md pins /design prefix-identical repeat silent-yield clause" \
    'prefix-identical repeat non-empty task-output bytes (first 200 chars) for the same wait with the relevant terminal sentinel absent also mean silent yield.'
check "$AGENTS_MD" \
    "AGENTS.md pins /implement Steps 3 and 5 notification-only recovery" \
    'For `/implement` Steps 3 and 5, premature notifications remain notification-only'
check "$AGENTS_MD" \
    "AGENTS.md pins /implement Step 8 rc-probe recovery" \
    'For `/implement` Step 8, run one foreground non-sleeping `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time'

check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes **one** `skills/implement/scripts/step-5-review.sh`'
check "$IMPL_MD" \
    "SKILL.md bgjob WAIT repeats identical wait" \
    'after `BGJOB_STATUS=WAIT`, run the identical `bgjob wait` again with no intervening prose or tools'
check "$IMPL_MD" \
    "SKILL.md bgjob DONE uses result env" \
    'after final `DONE`, parse required KVs from the last `DONE` stdout and `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`'

check_context "$DESIGN_MD" \
    "/design Anti-pattern #5 pins bgjob result-env gate" \
    "$DESIGN_EMPTY_OUTPUT_ANCHOR" \
    "2" \
    '`BGJOB_STATUS=DONE` is not success unless `BGJOB_RC=0` and required route KVs are present in the final wait stdout and/or `$DESIGN_TMPDIR/bgjob/<step>.result.env`.'
check_context "$DESIGN_MD" \
    "/design Anti-pattern #5 pins failure statuses" \
    "$DESIGN_EMPTY_OUTPUT_ANCHOR" \
    "2" \
    'Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, non-zero `BGJOB_RC`, or missing KVs as the step'"'"'s existing failure or stall branch.'

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
    "shared /design wait anchor documents same-batch silent yield" \
    'If several notifications are already queued in the same batch, ignore the rest of that batch after the first denial or clamp: no more tools, no prose, and no extra reads until a later `<task-notification>` arrives.'
check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor pins the compact-table missing warning" \
    '**⚠ Reviewer status table omitted: pre-rendered table not found.**'
check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor pins prefix-identical repeat fingerprint" \
    'If non-empty task-output bytes are prefix-identical to the prior non-empty bytes in the same wait over the first 200 chars'
check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor pins first-200-char fingerprint definition" \
    'The fingerprint is the first 200 chars.'
check_absent "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait anchor removes byte-identical fingerprint wording" \
    'byte-identical'
check_context "$SHARED_DESIGN_WAIT_MD" \
    "shared /design immediate wait pins empty-output condition" \
    "$SHARED_IMMEDIATE_WAIT_ANCHOR" \
    "2" \
    '(1) missing or whitespace-only task-output bytes -> silent yield'
check_context "$SHARED_DESIGN_WAIT_MD" \
    "shared /design immediate wait pins no-tool action" \
    "$SHARED_IMMEDIATE_WAIT_ANCHOR" \
    "2" \
    'Silent yield means no prose/tools or "still empty"/"waiting" status'
check_context "$SHARED_DESIGN_WAIT_MD" \
    "shared /design immediate wait pins no-probe turn end" \
    'Foreground terminal-sentinel probe' \
    "2" \
    'end the turn without probing'

check_context "$DESIGN_MD" \
    "/design Verbosity Control references the bgjob wait anchor" \
    '**Step 3 foreground waits**' \
    "8" \
    'shared bgjob wait contract'
check_context "$DESIGN_MD" \
    "/design Verbosity Control uses the Step 3 bgjob wait contract" \
    '**Step 3 foreground waits**' \
    "8" \
    'shared bgjob wait contract'

check_context "$DESIGN_MD" \
    "/design Final summary block references the shared bgjob wait anchor" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$SHARED_REF"
check_context "$DESIGN_MD" \
    "/design Final summary block uses the bgjob wait contract" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$FINAL_SUMMARY_BGJOB_LITERAL"
check_context "$DESIGN_MD" \
    "/design Final summary block names the bgjob result env" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "25" \
    "$FINAL_SUMMARY_RESULT_ENV_LITERAL"
check_context "$DESIGN_MD" \
    "/design Final summary block gates DONE on BGJOB_RC" \
    '**When**: after `DESIGN_TMPDIR` exists' \
    "35" \
    "$FINAL_SUMMARY_DONE_LITERAL"

FINAL_SUMMARY_FENCE_ANCHOR='design-step-final-summary.sh --outcome'
STEP3_RESUME_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh --starting-round'
STEP5C_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh'

check_context_before "$DESIGN_MD" \
    "/design Final summary bgjob contract precedes its launcher fence" \
    "$FINAL_SUMMARY_FENCE_ANCHOR" \
    "20" \
    "$FINAL_SUMMARY_BGJOB_LITERAL"
check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch load contract precedes its bgjob fence" \
    "20" \
    'shared bgjob wait contract'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference precedes its bgjob fence" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    "$RESUME_BACKREF_LITERAL"
check_context_before "$DESIGN_MD" \
    "/design Step 5c bgjob contract precedes its launcher fence" \
    "$STEP5C_ANCHOR" \
    "20" \
    'shared bgjob wait contract'

check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch references the bgjob wait anchor" \
    "20" \
    'shared bgjob wait contract'
check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch loads bgjob-wait contract" \
    "20" \
    'shared bgjob wait contract'
check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch pins BGJOB_RC gate" \
    "35" \
    'BGJOB_RC=0'
check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch names bgjob result env" \
    "35" \
    'bgjob/design-step3-review.result.env'
check_context_before_step3_launch "$DESIGN_MD" \
    "/design Step 3 launch keeps the terminal sentinel parameter" \
    "20" \
    '.completed/step-3-terminal'

check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference names bgjob wait" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'bgjob wait'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference names BGJOB_RC" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'BGJOB_RC=0'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference names result env" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'result-env'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference names rejoin" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'start/rejoin'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference names terminal-sentinel compatibility" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'terminal-sentinel compatibility'
check_context_before "$DESIGN_MD" \
    "/design Step 3 resume back-reference points at first-time fence" \
    "$STEP3_RESUME_ANCHOR" \
    "20" \
    'first-time Step 3 review fence'

check_context_before "$DESIGN_MD" \
    "/design Step 5c references the bgjob wait contract" \
    "$STEP5C_ANCHOR" \
    "18" \
    'shared bgjob wait contract'
check_context_before "$DESIGN_MD" \
    "/design Step 5c names bgjob result env" \
    "$STEP5C_ANCHOR" \
    "18" \
    'bgjob/design-step5c.result.env'
check "$DESIGN_MD" \
    "/design Step 5c documents BGJOB_RC success gate" \
    'Only after `BGJOB_STATUS=DONE` with `BGJOB_RC=0` may Step 5c parse `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`.'

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
    'New or changed non-empty task-output bytes allow one foreground terminal-sentinel probe per explicit recovery turn'

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER splits /design non-empty foreground recovery" \
    'For `/design`, after a premature `<task-notification>`, first run exactly one `Read` of the active `tasks/*.output`'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER splits /design empty no-probe recovery" \
    'Missing or whitespace-only task-output bytes mean silent yield (#5240)'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins /design prefix-identical repeat silent-yield clause" \
    'prefix-identical repeat non-empty task-output bytes (first 200 chars) for the same wait with the relevant terminal sentinel absent also mean silent yield.'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER keeps /implement Steps 3 and 5 notification-only recovery" \
    'For `/implement` Steps 3 and 5, premature notifications remain notification-only'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER documents the /implement live-wait Read carve-out" \
    'The hook may still allow a live `Read` of `tasks/*.output`; treat that as diagnostic only and do not use it to advance the step.'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins Step 3/5 post-denial recovery trigger" \
    'If a read of the just-completed Step 3 or Step 5 task output is denied immediately after that same step'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins retry-on-present guidance" \
    'When the sentinel is present, retry the just-denied output read once.'
check "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER pins /implement Step 8 rc-probe recovery" \
    'For `/implement` Step 8, run one foreground non-sleeping `IMPLEMENT_TMPDIR=$(awk '\''BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null); test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time'
check_absent "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER removes empty-notification-only qualifier" \
    'only after an empty `<task-notification>`'
check_absent "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER removes the-empty-notification-only qualifier" \
    'only after the empty `<task-notification>`'

check "$AGENTS_MD" \
    "AGENTS.md splits /design non-empty foreground recovery" \
    'For `/design`, after a premature `<task-notification>`, first run exactly one `Read` of the active `tasks/*.output`'

check "$AGENTS_MD" \
    "AGENTS.md splits /design empty no-probe recovery" \
    'For `/design`, missing or whitespace-only task-output bytes mean silent yield (spurious notification, #5240)'
check "$AGENTS_MD" \
    "AGENTS.md splits /design repeat no-probe recovery" \
    'prefix-identical repeat non-empty task-output bytes (first 200 chars) for the same wait with the relevant terminal sentinel absent also mean silent yield.'

check "$AGENTS_MD" \
    "AGENTS.md keeps /implement Steps 3 and 5 notification-only recovery" \
    'For `/implement` Steps 3 and 5, premature notifications remain notification-only'
check "$AGENTS_MD" \
    "AGENTS.md documents the /implement live-wait Read carve-out" \
    'The hook may still allow a live `Read` of `tasks/*.output`; treat that as diagnostic only and do not use it to advance the step.'
check "$AGENTS_MD" \
    "AGENTS.md pins /implement Step 8 rc-probe recovery" \
    'For `/implement` Step 8, run one foreground non-sleeping `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time'

check "$AGENTS_MD" \
    "AGENTS.md bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$AGENTS_MD" \
    "AGENTS.md defers recovery mechanics to skill authorities" \
    'skills/shared/orchestrator-never.md'

check "$IMPL_MD" \
    "SKILL.md NEVER list explicitly bans Monitor tool in /implement orchestrator" \
    'NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator'

check "$IMPL_MD" \
    "SKILL.md NEVER list keeps implement Steps 3 and 5 no-probe before notification" \
    'Before the `<task-notification>`, make no progress probes.'
check "$IMPL_MD" \
    "SKILL.md NEVER list documents the /implement live-wait Read carve-out" \
    'The hook may still allow a live `Read` of `tasks/*.output` on the running task; treat that as diagnostic only and do not use it to advance the step.'
check "$IMPL_MD" \
    "SKILL.md NEVER list pins implement Step 8 bgjob route" \
    'Step 8 uses bgjob wait/rejoin; on `DONE`, route through current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` sidecars, not generic `BGJOB_RC=0` success.'
check "$IMPL_MD" \
    "SKILL.md NEVER #8 pins Step 3 same-step probe trigger (Step 5 now uses bgjob)" \
    'If a live `Read` of just-completed Step 3 task output is denied immediately after that step'
check "$IMPL_MD" \
    "SKILL.md NEVER #8 forbids design sentinel probes" \
    'do not use `ps`, Monitor, TaskOutput, or background recovery waiters'
check "$IMPL_MD" \
    "SKILL.md NEVER list lazy-loads orchestrator-never only for premature recovery" \
    'On premature notification while the child is still running, read `${CLAUDE_PLUGIN_ROOT}/skills/shared/orchestrator-never.md` only when that recovery condition is active.'
check_absent "$IMPL_MD" \
    "SKILL.md NEVER list removes routine orchestrator-never wait pointer" \
    'See `skills/implement/references/step2-dispatch.md` orchestrator wait contract and `skills/shared/orchestrator-never.md`.'
check_absent "$IMPL_MD" \
    "SKILL.md NEVER list removes empty-stdout-only implement recovery wording" \
    'prematurely with empty stdout on an `/implement`'
check_absent "$IMPL_MD" \
    "SKILL.md NEVER list removes generic empty-stdout-only premature wording" \
    'fires prematurely with empty stdout'

check_absent "$IMPL_MD" \
    "SKILL.md NEVER list removes stale absent-sentinels disclaimer now that sentinels are built" \
    '/implement` does not write `$IMPLEMENT_TMPDIR/.completed/*-terminal` sentinels today'

check "$IMPL_MD" \
    "SKILL.md NEVER list pins Step 3 exact probe form" \
    'test -f "$IMPLEMENT_TMPDIR/.completed/step-3-terminal"'
check "$IMPL_MD" \
    "SKILL.md NEVER list pins Step 5 bgjob-only recovery (no sentinel probe)" \
    'Step 5 no longer uses task-output reads, detach sidecars, or notification recovery'
check "$IMPL_MD" \
    "SKILL.md NEVER list pins retry-on-present guidance" \
    'When the same-step sentinel is present, retry the just-denied output read once.'
check "$IMPL_MD" \
    "SKILL.md NEVER list pins absent-sentinel no-second-notification guidance" \
    'When it is absent after a genuine completion notification, do not wait for another notification'
check "$IMPL_MD" \
    "SKILL.md NEVER list pins Step 8 terminal bgjob block" \
    'Block `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, missing sidecars, and stale sidecars.'

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
    "/design Anti-patterns keeps legacy recovery compatibility pointer" \
    'Read and apply `${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md` completely for legacy premature recovery compatibility.'

check "$DESIGN_MD" \
    "/design Anti-patterns bans the background recovery waiter (#4725)" \
    'NEVER launch a background recovery waiter'

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait pins Step 3 terminal sentinel for the foreground recovery probe" \
    'Step 3-specific recovery note: the completion condition MUST be `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`; it MUST NOT be `.step3-review-result.env`.'

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait pins foreground terminal-sentinel probe" \
    'Foreground terminal-sentinel probe: after the one classification `Read` finds new or changed non-empty task-output bytes'

check "$DESIGN_MD" \
    "/design Anti-patterns references bgjob wait mechanics" \
    'Use `bgjob start` and chunked foreground `bgjob wait`, not Bash polling loops.'

check "$AGENTS_MD" \
    "AGENTS.md pins DESIGN_TMPDIR prefix for foreground probes" \
    'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait pins DESIGN_TMPDIR prefix for foreground probes" \
    'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait pins DESIGN_TMPDIR prefix for foreground probes with foreground wording" \
    'prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$SHARED_DESIGN_WAIT_MD" \
    "shared /design wait documents notification-refire platform assumption" \
    'the backgrounded `/design` task reliably re-fires a `<task-notification>` on completion'

check_absent "$ORCH_NEVER_MD" \
    "shared orchestrator NEVER no longer owns DESIGN_TMPDIR prefix literal" \
    'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment'

check "$DESIGN_MD" \
    "/design Step 3 pins WAIT foreground-only routing" \
    'If stdout contains `BGJOB_STATUS=WAIT`, the next action is the identical wait command with no intervening prose, reads, Monitor, TaskOutput, or sleep.'
check "$DESIGN_MD" \
    "/design Step 3 documents BGJOB_RC success gate" \
    'Only after `BGJOB_STATUS=DONE` with `BGJOB_RC=0` may Step 3 parse the result env.'
check "$DESIGN_MD" \
    "/design Step 3 rejects non-result success signals" \
    'never continue from launcher stdout, `DONE` alone, `bgjob wait` shell exit 0, notification-time wrapper stdout, or the compatibility sentinel alone'

check "$DESIGN_MD" \
    "/design Step 3 requires step-3 sentinel before Step 3b routing" \
    'Before Step 3b+, require `[ -f "$DESIGN_TMPDIR/.completed/step-3" ]` too'

check "$DESIGN_MD" \
    "/design Anti-patterns tells orchestrator not to fall back to Monitor" \
    'Do NOT fall back to Monitor'

echo ""
echo "All $PASS assertions passed."
