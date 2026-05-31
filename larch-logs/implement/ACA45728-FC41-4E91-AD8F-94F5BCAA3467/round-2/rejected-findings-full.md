### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: lint-fix-loop: unconditional codex stderr-tail rewrite
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_codex` unconditionally rewrites stderr-tail after `run-external-agent` already wrote it via `--stderr-sink`. A failed codex lint-fix run can double-invoke `write_failed_agent_stderr_tail` from the same wrapper log; usually harmless but can mask divergent source selection if `run-external-agent` and the explicit write ever disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Only backfill when `${run_dir}/codex.log.stderr-tail` is missing, or drop the explicit write and rely on `--stderr-sink`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: test gap: `run_lint_fix_loop_capture` empty-with-failure `LINT_FIX_STATUS` trigger
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_lint_fix_loop_capture` omits plan empty-with-failure `LINT_FIX_STATUS` trigger. Malformed capture with rc=0 and empty status might skip `_surface_lint_fix_stderr_tail` while a tail file exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Align implementation with plan or prove unreachable; add harness if real.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: test gap: wrapper_rc=2 CI validation stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `wrapper_rc=2` CI validation surfacing path has no dedicated test. Validation failures might stop emitting tier stderr-tail to chat after future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub launcher exit 2 with seeded `${tier_out}.stderr-tail`; assert caller stderr before rollback.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: ship-pr vs Step 5: duplicated stderr-tail stem parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_surface_lint_fix_stderr_tail` duplicates `step5_surface_lint_stderr_tail` stem parsing. Future edits to fallback order could update ship-pr but not Step 5 (or vice versa), surfacing tails in one lane only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared parse-and-surface helper used by both callers.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: lint-fix-loop: `STDERR_TAIL_PATH` last-wins hides earlier agent tail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `STDERR_TAIL_PATH` keeps only the last failed stem. Codex dispatch fails (`codex.log.stderr-tail` written) then Cursor preflight fails; chat surfaces Cursor preflight via `STDERR_TAIL_PATH` while the Codex agent tail stays on disk only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer first non-empty agent tail for KV/chat, or document and test last-wins if intentional.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: ship-pr recovery waterfall: surfaces stderr tail on every failed tier
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall surfaces stderr tail on every failed tier before `continue`. Cursor CI fix fails (tail emitted) then Codex tier runs; operator sees multiple tails for reverted work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface only on terminal waterfall failure or summarize prior-tier tails.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: ship-pr recovery waterfall: orphan `${output}.stderr-tail` with `launcher_exit=0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier failure treats orphan `${output}.stderr-tail` as failure when `launcher_exit=0`. Stale tail file with `LAUNCHER_EXIT=0` could skip a tier that actually succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require `launcher_exit!=0` (or parsed failure class) before honoring `-s ${output}.stderr-tail` alone.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: ship-pr recovery waterfall: split failure continue blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall uses two separate failure `continue` blocks after one surfacing call. Readers must reason about `tier_rc` vs `launcher_exit` separately even though both paths surface then revert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Combine failure conditions into one block that surfaces, reverts, and continues.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: recovery waterfall: launcher stdout capture files accumulate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Per-tier `recovery-*-launcher-$$.out` (and related launcher stdout capture files) are never removed. Long `/implement` runs accumulate launcher captures under `IMPLEMENT_TMPDIR` until session cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: `rm -f` after parsing or reuse one capture path per waterfall.
  - From cursor-specialist-edge-cases-output.txt: `rm -f` after awk parse or reuse one `mktemp` per waterfall invocation.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Step 5: stderr-tail surfacing on lint-fix attempt-cap after applied
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `step5_surface_lint_stderr_tail` on lint-fix-attempt-cap after `applied` status may attempt emit using `CODER_LOG_FILE` from a successful applied capture when no failure tail exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Skip surfacing on attempt-cap or gate on terminal failure statuses only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: implement Step 3/6: orchestrator does not surface lint-fix stderr tails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 3/6 orchestrator lint-fix invocations do not parse `STDERR_TAIL_PATH` or emit tails to chat. Codex lint-fix can fail at Step 3 with tail file and KV emitted, but orchestrator never surfaces it—only ship-pr RCC and Step 5 loop consumers do.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend Step 3/6 SKILL/bash surfacing, or narrow acceptance to implemented consumers (step2, ship-pr, step5).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

