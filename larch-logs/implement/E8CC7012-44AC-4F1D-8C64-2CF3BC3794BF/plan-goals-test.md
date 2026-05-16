## Goal
Fix audit-trail collapse: timing-ledger stops recording after Step 0.5, code-review-tally and review-findings-full batches not flushed. (Issue #2219)

## Implementation Plan
## Feature Description

Fix audit-trail collapse: timing-ledger stops recording after Step 0.5,
code-review-tally and review-findings-full batches not flushed, phantom
timing-task-kinds. (Issue #2219)

## Root Cause

SKILL.md preamble Bash blocks that call `timing-ledger.sh mark "Step N"` and
write larch-log batches fail silently. The pattern:

    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
    export IMPLEMENT_TMPDIR
    ...
    "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step N — ..." || true

fails when the orchestrator emits it verbatim in a fresh subshell — `$IMPLEMENT_TMPDIR`
expands to empty, `CLAUDE_PLUGIN_ROOT` resolution fails, `timing-ledger.sh mark`
is a no-op via `|| true`. Worker script calls (review-and-fix.sh, step2-implement.sh,
run-relevant-checks-captured.sh) are NOT affected because the orchestrator passes
`--implement-tmpdir "$IMPLEMENT_TMPDIR"` with the real value substituted.

Symptoms (from issue):
1. Timing-ledger stops after Step 0.5 (Steps 2, 3, 5, 6 marks never fire)
2. code-review-tally and review-findings-full batches absent from run logs
3. Phantom timing-task-kinds "codex-review"/"cursor-review" — ALREADY FIXED
   (both are in TIMING_TASK_KINDS_ALLOWED in scripts/lib-timing-kinds.sh)


### Fix A: Add timing marks to worker scripts

**A1: skills/implement/scripts/step2-implement.sh**
- Add `"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 2 — implementation" || true`
  after the cursor/claude fallback gates, right before `REQUIRES_HEAD_UNCHANGED=false`
  (between the cursor health gate and the external implementer dispatch section).
- Only fires on the real external-implementer path (codex or cursor-healthy).
  The claude_fallback and cursor-fallback early-returns exit before reaching this line.
- `PLUGIN_ROOT` is already set at script top (line 9); `IMPLEMENT_TMPDIR` is exported
  at line 148, so timing-ledger.sh resolves the ledger via `IMPLEMENT_TMPDIR` env.
- Update sibling step2-implement.md.

**A2: skills/review-and-fix/scripts/review-and-fix.sh**
- In `run_implement_round()`, add after validation block (around line 415):
    if (( round_num_dec == 1 )); then
        IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" \
            "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 5 — code review" || true
    fi
- Only fires on the first round to avoid double-marking. Subsequent rounds are
  within Step 5 and do not reset the step boundary.
- `PLUGIN_ROOT` is set at line 7. `IMPLEMENT_TMPDIR` is local to the function
  but must be passed inline (the subprocess needs it in env).
- Update sibling review-and-fix.md.

**A3: scripts/run-relevant-checks-captured.sh**
- Add site-based timing marks after TMPDIR_CANONICAL is set and validated:
    case "$SITE" in
        step3) IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" \
                   "$SCRIPT_DIR/timing-ledger.sh" mark "Step 3 — checks first pass" || true ;;
        step6) IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" \
                   "$SCRIPT_DIR/timing-ledger.sh" mark "Step 6 — checks second pass" || true ;;
    esac
- `SCRIPT_DIR` is the scripts/ directory containing timing-ledger.sh.
- `TMPDIR_CANONICAL` is the validated session tmpdir (contains timing-ledger.tsv).
- The step5-review-fixes site is intentionally NOT marked here; Step 5's mark
  is placed in review-and-fix.sh (A2 above).
- Update sibling run-relevant-checks-captured.md.

### Fix B: Write tally batches from review-and-fix.sh

**B1: skills/review-and-fix/scripts/review-and-fix.sh**
- Add `flush_review_batches()` helper function that composes and writes:
  a) code-review-tally batch via write-tally.sh
  b) review-findings-full batch via compose-review-findings.sh + larch-log.sh write
- Call it on the exit_code=0 path in run_implement_round(), before `exit "$exit_code"`.
- Function signature: flush_review_batches <impl_tmpdir> <run_id> <panel>
                                             <rounds> <accepted> <rejected>
- Best-effort: all internal failures are trapped with `|| true` / `|| return 0`.
- Body-file composition for write-tally.sh:
  1. Header: "Rounds: N | Accepted: M | Rejected: K"
  2. review-round-summary.md content (if present; headings are all in allowed set)
  3. rejected-findings.md under "## Rejected Code Review Findings" (if present)
  4. round-N/voting-tally.md under "## Voting Tally" (if present)
- compose-review-findings.sh uses --issue 0 (issue number not available in the
  script; 0 is the established fallback per SKILL.md line 1436).
- larch-log.sh write for review-findings-full: replace-mode batch.
- Update sibling review-and-fix.md.

### Files NOT changed

- skills/implement/SKILL.md — root cause is the SKILL.md preamble pattern, but
  changing SKILL.md to fix the preamble would re-introduce the same fragility on
  the next SKILL.md edit. Moving logic to scripts is the durable fix.
- scripts/lib-timing-kinds.sh — Symptom 3 is already fixed (codex-review and
  cursor-review are in TIMING_TASK_KINDS_ALLOWED).


## Test plan

- Run relevant-checks after changes.
- `set -euo pipefail` — all scripts use strict mode; no new bare || true chains
  except the best-effort timing/batch writes (established pattern in SKILL.md).
- Idempotency: timing marks are append-only (TSV) and naturally idempotent
  for distinct step names. flush_review_batches uses larch-log.sh write
  (atomic replace with cmp de-dup) and write-tally.sh (atomic compose+write).
- Double-mark risk: step5 mark fires only when round_num_dec==1; step2 and step3/step6
  marks fire at single natural entry points per step. If the SKILL.md preamble
  also fires (orchestrator correctly substitutes IMPLEMENT_TMPDIR), both marks
  record; timing-report.sh deduplicates by taking the first mark per step name.
