## Goal
Implement issue #4724: [IMPLEMENTING] [BUG] design Step 3 reviewer aggregation fails silently: TSV outputs present but findings.md stays empty and .completed/step-3 sentinel not written.

## Implementation Plan
## Summary

During a `/design` run, the `plan-review run` subprocess (invoked by `design-step3-review.sh`) dispatched all 12 reviewer slots and they produced TSV findings output, but the collection/aggregation phase failed silently. `findings.md` stayed empty, `reviewer-status.tsv` was never written to `plan-review/round-1/`, and `.step3-review-result.env` was never written. The `.completed/step-3` sentinel was also absent after the background task exited, meaning the guarantee EXIT trap in `design-step3-review.sh` did not fire or was bypassed. The orchestrator had to invoke the Gate B bypass path manually to recover.

## Original report

Reviewer aggregation failed: `design-step3-review.sh` background task completed, all reviewer slots (8 static Cursor + Codex slots, plus 4 dynamic Codex slots = 12 total) produced TSV output files in `$DESIGN_TMPDIR`, but `findings.md` was 0 bytes, `voting-tally.md` was empty, and `.completed/step-3` was absent. The orchestrator treated the review as `degraded-empty-collector` but real findings (47+ TSV rows) existed in the raw reviewer output files.

## Reproduction scenario

1. Run `/design <issue-number>` through to Step 3 with both Cursor and Codex available.
2. All 12 reviewer slots launch successfully and produce TSV output files at `$DESIGN_TMPDIR/<vendor>-plan-*-output.txt`.
3. Observe: `$DESIGN_TMPDIR/findings.md` is 0 bytes, `$DESIGN_TMPDIR/plan-review/round-1/reviewer-status.tsv` does not exist, `$DESIGN_TMPDIR/.step3-review-result.env` does not exist, `$DESIGN_TMPDIR/.completed/step-3` does not exist.
4. The `design-step3-review.sh` background task (the one invoked by the orchestrator's `run_in_background: true` Bash call) exits with approximately 1 line of output (nearly empty stdout).

Observed on a macOS Darwin host during a `/design` run for issue #4675 (a sh-to-py migration issue).

## Expected behavior

- After all reviewer slots complete, the embedded `plan-review-loop.sh` (materialized from `python/plan_review.py::_LEGACY_ASSETS`) aggregates TSV outputs into `findings.md` and writes `reviewer-status.tsv` under `plan-review/round-1/`.
- `.step3-review-result.env` is written with `STEP3_REVIEW_LOOP_STATUS=complete` (or `degraded-empty-collector` if zero parseable findings).
- The guarantee EXIT trap in `design-step3-review.sh` at line 425 writes `.completed/step-3` on any exit path.

## Observed behavior

- `$DESIGN_TMPDIR/findings.md`: 0 bytes.
- `$DESIGN_TMPDIR/plan-review/round-1/reviewer-status.tsv`: absent. Only `prune-decision.env` and `round-start-s` are present — indicating the round was STARTED and reviewers were DISPATCHED, but the COLLECTION phase never completed.
- `$DESIGN_TMPDIR/.step3-review-result.env`: absent.
- `$DESIGN_TMPDIR/.completed/step-3`: absent after background task notification.
- Background task stdout: 1 line (nearly empty; content unverified).
- `review-round-count.txt`: `1` (round consumed/persisted at pre-launch per the persist contract).
- All 12 reviewer output files present with real TSV findings (47+ rows across slots).
- Recovery waiter (`until [ -f "$DESIGN_TMPDIR/.completed/step-3" ]; do sleep 30; done`) completed without finding the sentinel, confirming it was never written.

## Root cause analysis

There are two separate failures: (A) the collection/aggregation failure — reviewers produced output but their TSV rows were not parsed into `findings.md`, and (B) the missing sentinel — the guarantee EXIT trap did not write `.completed/step-3`.

---

### Failure A: Collection/aggregation silent failure

**What should happen**: after reviewers produce output files at `$DESIGN_TMPDIR/<vendor>-plan-*-output.txt`, the embedded `plan-review-loop.sh` (or `run-step3-review.sh`) collects and parses them. Collection writes `plan-review/round-1/reviewer-status.tsv` and aggregated findings into `$DESIGN_TMPDIR/findings.md`.

**What happened**: `plan-review/round-1/` has only `prune-decision.env` and `round-start-s`. There is no `reviewer-status.tsv`. This means the collection phase was never entered OR crashed before writing any artifacts.

**Most likely cause — TSV format divergence**: Cursor reviewer output files include a preamble prose line before the TSV header, while Codex reviewer output files begin directly with the TSV header and have no trailing newline:

Cursor format (`cursor-plan-arch-output.txt`, 65 lines):
```
Reading the plan and tracing the cited codebase paths to validate contracts and integration points.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	blocking	correctness	...
```

Codex format (`codex-primary-plan-arch-output.txt`, 2 lines, no trailing newline):
```
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	...
```

If the collection script uses a line-count or format probe that fails on the Codex output (no trailing newline, 2 lines instead of 3+), it may abort early — before writing `reviewer-status.tsv` or `findings.md` — causing the aggregation step to produce no output and exit non-zero.

The `plan-review run` subprocess captures nothing to its stdout pipe (`>"$_plan_review_stdout_file"` redirect in `design-step3-review.sh:408`), so the failure is completely invisible to the parent. The parent at lines 465–528 detects the empty result env and stdout, and falls through to `STEP3_REVIEW_LOOP_STATUS=panel-failed` — which IS emitted — but the silent aggregation failure means no findings are ever available to apply.

**What needs to be fixed**:
1. Add explicit error logging in the embedded collection phase when `reviewer-status.tsv` is not written despite reviewer output files existing. The current failure produces no stderr or diagnostic artifact.
2. Validate that the TSV parser handles both Codex format (no preamble, no trailing newline) and Cursor format (preamble + trailing newline) correctly. Specifically: confirm the parser does not require a trailing newline and does not error on output files that begin with the header line directly.
3. Add an explicit post-collection assertion: after collection completes, if reviewer output files exist but `reviewer-status.tsv` is absent, write a diagnostics artifact and emit a clear error rather than silently exiting.

---

### Failure B: Missing `.completed/step-3` sentinel

**What should happen**: `design-step3-review.sh` sets a guarantee EXIT trap at line 425:
```bash
trap '_step3_review_guarantee_completed_sentinels' EXIT
```
This trap should write `.completed/step-3` on any exit (except SIGKILL which bypasses EXIT traps).

**The trap window problem**: there is a 5-line window between the cleanup trap removal and the guarantee trap installation where NO EXIT trap is active:
```bash
_loop_pid=""
trap - EXIT                                           # line 420 — trap REMOVED
# lines 421-424: comment block only, no executable statements
trap '_step3_review_guarantee_completed_sentinels' EXIT  # line 425 — trap SET
```

If the `design-step3-review.sh` process receives SIGKILL during this window — or if the bash process crashes between lines 420 and 425 due to `set -e` on a failing command — the EXIT trap never runs and `.completed/step-3` is never written. The orchestrator then cannot confirm Step 3 completion.

Additionally, the guarantee function itself returns early when `DESIGN_TMPDIR` is empty:
```bash
_step3_review_guarantee_completed_sentinels() {
  [ -n "${DESIGN_TMPDIR:-}" ] && [ -d "${DESIGN_TMPDIR:-}" ] || return 0
  ...
}
```
If `DESIGN_TMPDIR` were unset at trap invocation time (e.g., due to an unexpected exit before sourcing), the sentinel would silently not be written.

**What needs to be fixed**:
1. **Eliminate the trap window**: set the guarantee trap BEFORE removing the cleanup trap. Change the order to:
   ```bash
   trap '_step3_review_guarantee_completed_sentinels' EXIT   # set FIRST
   trap - EXIT   # then clear — but this REMOVES the guarantee trap too
   ```
   Actually the correct fix is to NOT remove the cleanup trap and NOT set a second trap — instead, restructure `_step3_review_cleanup` to call `_step3_review_guarantee_completed_sentinels` first (it already does at line 352), and keep that single trap in place for the entire post-loop phase. There should be no window where no trap is active.
2. **Alternative simpler fix**: move the guarantee trap setup to immediately BEFORE the `trap - EXIT` removal so the guarantee trap is already in place when the cleanup trap is removed:
   ```bash
   trap '_step3_review_guarantee_completed_sentinels' EXIT   # line 424.5 NEW
   trap - EXIT                                                # line 420 repurposed — now clears cleanup trap, but guarantee is already set
   ```
   Wait, this doesn't work because `trap - EXIT` clears ALL traps including the guarantee trap just set. The correct fix is to use a single combined trap function from the outset.
3. **Correct approach**: Replace the two-phase trap pattern with a single trap that covers both cleanup AND sentinel guarantee throughout the entire post-launch phase. The cleanup function (`_step3_review_cleanup`) already calls `_step3_review_guarantee_completed_sentinels` as its first step (line 352), so a single persistent trap would eliminate the window.

## Evidence

- `$DESIGN_TMPDIR/plan-review/round-1/` contains only `prune-decision.env` (`PRUNE_ACTIVE=false`, `ELIGIBLE=0`, `PRUNED_COUNT=0`, `PANEL_FULL=12`) and `round-start-s` — no `reviewer-status.tsv`.
- Round started at epoch recorded in `round-start-s`. Reviewers launched (12 output files present). Collection never completed.
- Reviewer output files present with real findings (47+ TSV data rows across slots):
  - `cursor-plan-arch-output.txt`: 65 lines, 8 TSV findings (has preamble + trailing newline)
  - `cursor-plan-dyn-closeout-integration-output.txt`: 36 lines, 9 TSV findings
  - `cursor-plan-dyn-port-parity-output.txt`: 21 lines, 12 TSV findings
  - `cursor-plan-innovation-output.txt`: 22 lines, 5 TSV findings
  - `cursor-plan-pragmatic-output.txt`: 21 lines, 6 TSV findings
  - `cursor-plan-requirements-output.txt`: 55 lines, 7 TSV findings
  - `codex-primary-plan-arch-output.txt`: 2 lines, 2 findings (NO preamble, NO trailing newline)
  - `codex-primary-plan-dyn-closeout-integration-output.txt`: 2 lines, 2 findings (same format)
  - `codex-primary-plan-dyn-port-parity-output.txt`: 3 lines, 3 findings
  - `codex-primary-plan-innovation-output.txt`: 2 lines, 2 findings
  - `codex-primary-plan-pragmatic-output.txt`: 6 lines, 4 findings
  - `codex-primary-plan-requirements-output.txt`: 27 lines, 6 findings
- `$DESIGN_TMPDIR/findings.md`: 0 bytes. All findings files empty: `findings-in-scope.md`, `findings-oos.md`, `oos.md`, `ballot.txt`, `voting-tally.md`, `rejected-findings.md`.
- `review-round-count.txt`: `1`.
- `.step3-review-cap.env`: `STEP3_REVIEW_CAP_REACHED=false`, `STEP3_REVIEW_ROUND_NUM=1`.
- `design-step3-review.sh` lines 420 and 425: the trap window where no EXIT trap is registered.

## Affected files

- `python/plan_review.py` — `_run_legacy` materializes the embedded `run-step3-review.sh` and runs it. The embedded script's collection phase (reading TSV outputs into `findings.md` and writing `reviewer-status.tsv`) needs defensive logging and TSV format tolerance.
- `skills/design/scripts/design-step3-review.sh` (lines 420–425) — the trap window between `trap - EXIT` and the guarantee trap installation. The fix is to restructure so only one EXIT trap covers the entire post-loop phase.
- The embedded `plan-review-loop.sh` gzip asset in `python/plan_review.py::_LEGACY_ASSETS` — the collection step that parses reviewer TSV outputs. This is the embedded script that needs the logging and format-tolerance improvements.

## Suggested fix(es)

**Fix 1 — eliminate the sentinel trap window (design-step3-review.sh)**:

Remove the two-phase trap pattern. Instead of removing the cleanup trap and then setting a new guarantee trap, keep a single persistent trap that handles both. The current `_step3_review_cleanup` already calls `_step3_review_guarantee_completed_sentinels` as its first action (line 352), so the cleanup trap already guarantees the sentinel. The problem is that `trap - EXIT` at line 420 removes that protection for 5 lines.

Simplest fix: do not call `trap - EXIT` at line 420. Instead, replace the cleanup trap with the guarantee-only trap directly without a removal step:
```bash
# Before (has window):
trap - EXIT
trap '_step3_review_guarantee_completed_sentinels' EXIT

# After (no window):
trap '_step3_review_guarantee_completed_sentinels' EXIT
```
This single assignment replaces the cleanup trap atomically (bash trap assignment is not a two-step remove+set). No window exists.

**Fix 2 — add collection-phase diagnostics (embedded plan-review-loop.sh)**:

After the reviewer dispatch-and-collect phase, add an explicit check:
```bash
if [ ! -f "$DESIGN_TMPDIR/plan-review/round-$ROUND/reviewer-status.tsv" ]; then
  printf 'COLLECTION_FAILURE=true\nREASON=reviewer-status-tsv-missing\n' \
    >"$DESIGN_TMPDIR/plan-review-collection-failure.env"
  printf '**⚠ Step 3: collection failed: reviewer-status.tsv not written despite reviewer output files existing\n' >&2
  exit 1  # triggers panel-failed path with visible diagnostics
fi
```

**Fix 3 — harden TSV parser for Codex output format (embedded plan-review-loop.sh)**:

Ensure the TSV parser handles output files that:
- Have no trailing newline (Codex format)
- Start directly with the header line (no prose preamble)
- Have as few as 2 lines total (header + 1 data row)

Test the parser against synthetic Codex-format fixture files. A parsing failure on these edge cases could cause silent collection abort.

## Open questions

- Does the embedded `plan-review-loop.sh` TSV parser require a trailing newline? A `while IFS= read -r line` loop in bash will silently drop the final line if it has no trailing newline.
- Was the `design-step3-review.sh` process killed externally (SIGKILL) during the trap window? If so, the sentinel absence is due to the kill, not the lack of a trap — both need fixing.
- Does the `plan-review run` subprocess exit non-zero when collection fails? If so, `_plan_review_rc` in `design-step3-review.sh` would be non-zero, but the script doesn't treat this as an immediate abort — it just falls through to the result-env read path.
- Is there a race between reviewer output file creation and the collection phase? If the collection phase starts before all reviewer output files are fully flushed, some files may be incomplete.

## Test plan
(no test plan section in plan-file)
