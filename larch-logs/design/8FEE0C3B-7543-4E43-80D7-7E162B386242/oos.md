### FINDING_2: Pool appends need deduplication
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Pool sidecar writes can duplicate blocks across rounds, inflating trigger counts and causing repeated promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify and implement pool writes with the same unique-block append helper used for `oos-accepted-design.md`, and make trigger counting operate on deduped pool entries.
  - From Cursor-Pragmatic: Reuse `_append_unique_artifact_blocks` (or equivalent block-key dedupe) when accumulating pool sidecars; keep promotion idempotent by skipping chunks already present in the accepted sink.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: emit_tally needs an explicit session pool path
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The session-level aggregate pool path is not threaded into production `emit_tally` calls, so trigger evaluation cannot reliably read or persist the parent pool.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the implement pool to `$IMPLEMENT_TMPDIR/oos-aggregate-pool.md` (written from `tally_code_votes` via `session_env_path.parent`), and have `emit_tally` resolve it from `Path(args.review_tmpdir).parent` or an explicit `--session-env-path` before trigger evaluation and sink promotion.
  - From Codex-Innovation: Add `### UPDATED: python/larch/review/review_core_body.py` and forward `--session-env-path` plus `--implement-tmpdir` on every `emit_tally` invocation, mirroring the zero-findings branch.
  - From Codex-Innovation: Thread --session-env-path into the review_core_body emit_tally calls that follow tally-code-votes, especially the normal and main-agent-vote-required branches.
  - From Codex-Requirements: Add python/larch/review/review_core_body.py to the firm changes and thread --session-env-path, or an explicit aggregate-pool path from the tally env, through every production emit-tally call that evaluates aggregate OOS.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_8: /implement promotion must run at filing time
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: If promotion only happens in per-round tallying, later round-copy steps can still overwrite promoted blocks before Step 9a.1 filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin symmetric promotion to filing time: add an `oos_filer.py` (or shared helper) step before `_working_batch` that reads `$IMPLEMENT_TMPDIR/oos-aggregate-pool.md`, evaluates the trigger, normalizes headers, and appends into `oos-accepted-review.md`. Keep tally rounds append-only to the pool file.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Add `retry-file-and-annotate` to the canonical Step 5b dispatch reference
- **Description**: Add `retry-file-and-annotate` to the canonical Step 5b dispatch reference. Scenario: The new retry action will be defined only in finalize-step5 prose unless the dispatch reference is updated, leaving degraded prepare/annotate routing undocumented alongside existing `skip-pipeline` / `file-issues` / `label-only` rows.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/oos-step5b-dispatch.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

