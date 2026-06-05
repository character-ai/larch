### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Merge parity lacks a fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no merge parity gate analogous to finalize parity, so missing `merge-pr.sh` or all-skipped merge parity tests can still leave `py-test` green despite the Part B requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: CI-fix push/pending lifecycle coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: CI-fix tests omit plain push, lease-failure mapping, and full pending-rebase monitor lifecycle set/clear propagation, so non-rebase force-push mistakes or pending-state regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Timing harness shard may become unbalanced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Three timing harnesses were added to `test-harnesses-16`, which may push shard 16 beyond CI rebalance targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Run-log commit gate only refuses main/master literals
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_larch_log_commit` lacks the bash default-branch refusal beyond literal `main`/`master`, so repos with another default branch may commit teardown or pre-push refresh logs from the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Ship pre-rebase recovery skip lacks warning breadcrumb
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase `flush_logs_pre` recovery failure is allowed to proceed without a warning, unlike the postbump path, leaving no audit trail before `rebase_and_push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: When `pre_rebase.skipped` and `pre_rebase.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED`, call `_breadcrumb("warning", ...)` (and/or record a Warnings execution issue) before continuing, matching postbump refresh behavior.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Implement/design timing round idempotency contracts diverge
- **Reviewer(s)**: dyn-timing-ledger-output.txt, dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: Implement round timing short-circuits on any existing `(skill, step, round)` row while design fingerprints the full tuple and allows superseding rows, so implement cannot correct premature or partial ledger rows and the shared round schema has inconsistent semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Unify idempotency across both helpers (either round-keyed last-writer-wins matching `timing-report.sh`’s `emit_round_array` dedupe, or full-tuple skip with explicit supersede on changed `end_s`/counts) and document the single contract in `scripts/timing-ledger.md`; align harnesses so both workflows test deferred re-emit with updated duration.
  - From dyn-shell-portability-output.txt: Align the implement pre-check with the design fingerprint (round + step + start + end + accepted + rejected), or drop the coarse pre-check and rely only on the post-write verification already at lines 118–122.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: Step 5 resume split mark makes round attribution fragile
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: Step 5 resume emits a second timing mark for `--starting-round > 1`, splitting one logical review session into multiple mark intervals and making deferred round attribution dependent on fragile ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Either emit the Step 5 mark only once per session (update/resume sentinel instead of a second mark) or centralize round recording so all rows for a logical Step 5 session share one mark window; document the ordering invariant beside `review-implement-step5-loop.md` / `run-step5-review.md`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: design-route accepts empty session IDs
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `validate_session_id_arg` rejects embedded newlines but allows an explicitly empty `--session-id`, allowing blank session IDs to flow into run-params and timing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Reject empty values in `validate_session_id_arg` (mirror `validate_plain_scalar`) or add `[[ -n "$SESSION_ID_ARG" ]] || fail '--session-id must be non-empty'` before calling it.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Postbump preflight runs twice on the happy path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `postbump_preflight` is invoked both from ship and postbump, duplicating git probes and risking future side effects running twice instead of having one authoritative preflight site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: CI-fix and finalize rebase/push logic is duplicated and can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Postbump and CI-fix paths duplicate no-push rebase / rebase+force-push behavior across inline Python and shell helpers, so fetch retry, conflict abort, fork-base, lease, and dirty-tree handling can drift between code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: finalize_postmerge_logs alias contract is unclear and inconsistently routed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `finalize_postmerge_logs` is currently only a passthrough to `flush_logs_post`, while callers such as merge route directly to `flush_logs_post`; if the alias later becomes the centralized recovery/manifest/report contract, behavior can diverge or ordering assumptions can be obscured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: ship-pr-state writer preserves stale keys and lacks newline sanitization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state` merges existing unknown keys and writes unsanitized KV values, allowing stale or tampered bash-consumed keys — and newline-containing values — to survive or split the state file and skew resume behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

