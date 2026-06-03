### OOS_1: [OUT_OF_SCOPE] CI harness shards vs local relevant-checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness shards are the CI gate; local `relevant-checks` may skip them on script-only edits. Developer merges without running shard 5/16 locally; CI still catches failures on PR. Pre-existing; run `make test-oos-disposition-gate` when touching checkpoint/gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — reviewer provided concern only; generic “Address the concern above” omitted)


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] Python OOS parity with bash gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python OOS parity with bash gate not in this diff scope. Python cutover could pass disposition while bash checkpoint fails. Track separately from bash Phase 3 extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — reviewer provided concern only)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `RUN_ID` slug validation before ndjson path build
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_ID` from `session-id` is interpolated into `_oos_ndjson` without the slug rules `larch_log_slug_is_valid` / `larch_log_validate_slug` use in `scripts/larch-log.sh`. A corrupted or hand-edited `session-id` containing `..` segments could resolve paths outside `larch-logs/implement/<RUN_ID>/`. Same pattern existed in the removed inline SKILL block; not introduced by this refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse `larch_log_slug_is_valid` (or `^[A-Za-z0-9._-]+$` with rejection of `..` and `/`) before building the ndjson path; fail validation exit 2 on mismatch.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Arbitrary `--implement-tmpdir` / `--design-tmpdir` without session guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--implement-tmpdir` and `--design-tmpdir` are accepted as arbitrary directory strings with no check that they lie under the active session cache or match `expected-tmpdir-basename-prefix` semantics used elsewhere (e.g. `ship-pr.sh`). Mis-invoked CLI could read/write marker files and append redacted stderr from paths outside the intended session tmpdir. Pre-existing orchestrator trust model; not new to the checkpoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional prefix/canonicalization guard (compare realpath to `IMPLEMENT_TMPDIR` from env or session sentinel), aligned with other implement helpers if adopted repo-wide.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] `FORKED_TARGET` / `REPO_UNAVAILABLE` from unauthenticated `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `FORKED_TARGET` / `REPO_UNAVAILABLE` are read from `ship-pr-state.sh` without authentication; any writer of that file in the tmpdir can force gate skip (exit 0). Unchanged from inline behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Treat as intentional carve-out under session-tmpdir trust; document that tmpdir integrity is part of the single-runner invariant.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Non-canonical boolean strings in `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `FORKED_TARGET` / `REPO_UNAVAILABLE` require exact `true` string (pre-existing). Non-canonical state values run full gate/precondition paths unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Normalize booleans when reading ship-pr-state.sh (separate change).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_7: [OUT_OF_SCOPE] No harness for SKILL.md orchestrator checkpoint wrapper / fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-exit-site-mapping-output.txt
- **Severity**: nit
- **Concern**: Checkpoint unit tests can pass while the SKILL.md fence (bash wrapper, grep guards, fallback `--site`, rc propagation) regresses. No structure or harness test exercises the orchestrator block; mis-site fallback (FINDING_4) would not be caught by `make test-oos-disposition-gate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a small structure or harness test for the SKILL fence block.

---

**Subsumed / omitted (not emitted as findings):** FINDING_11–14 and FINDING_35 are positive security/consistency attestations with no actionable defect. FINDING_30, FINDING_31, FINDING_32, and FINDING_36 are informational context (acceptable child-script grep, documented ndjson contract change, commit list) without distinct fix direction beyond FINDING_1 documentation.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

