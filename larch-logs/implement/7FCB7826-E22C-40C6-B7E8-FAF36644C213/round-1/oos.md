### OOS_1: [OUT_OF_SCOPE] Branch bundles unrelated upgrade-larch / logs / version work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Branch bundles upgrade-larch, larch-logs, and version bumps with Step 5c extraction, widening PR scope beyond the feature; process suggestion, not a driver logic defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split or note in PR summary (process, not code fix).


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Dropped architecture diagram banner is accepted UX
- **Reviewer(s)**: dyn-prune-invariants-output.txt
- **Severity**: nit
- **Concern**: Dropping the `> **🔶 /design 5c.5: larch:diagrams (architecture)**` banner while keeping orchestrator `⏩ 5c.5:` was flagged acceptable in design run logs; not a functional regression.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Unrelated `scripts/lib-net.sh` executable bit change
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Unrelated executable bit change in a relevant-checks fix commit with no identified impact on the design-publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Leave as-is or isolate in separate commit.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Bundled upgrade-larch prune/stamp lacks automated tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bundled `upgrade-larch` prune/stamp changes lack automated tests; mid-upgrade cache deletion or wrong retention ranking is unguarded by CI on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a focused offline harness for prune retention/backfill (separate from design-publish work).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `composed-plan.redacted.md` checked with `-s` only, not regular file
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `composed-plan.redacted.md` is checked with `-s` only, not as a regular file; a symlink in tmpdir could point plan-block-write at non-redacted content (broader hardening, pre-existed inline Step 5c).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require regular file or reject symlinks before plan-block-write (broader hardening).


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: [OUT_OF_SCOPE] `add_warn` → result-env → `emit_kv WARN` chain is intentional
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: nit
- **Concern**: The `add_warn` → `phase_driver_write_result_env` → `emit_kv WARN` chain in `design-publish.sh` matches `design-init-runparams.sh` and the quiet-driver contract; no defect there.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Step 0b undeduped WARN replay predates this branch
- **Reviewer(s)**: dyn-warn-replay-output.txt
- **Severity**: nit
- **Concern**: Step 0b `design-init-runparams.sh` parsing uses the same undeduped `WARN=$_value` replay pattern; predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_7: [OUT_OF_SCOPE] Symlink refusal on `.design-publish-result.env` warns but does not abort
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: Symlink refusal on `.design-publish-result.env` prints a warning but does not abort (same pattern as Step 0b); pre-existing, not introduced by this extraction.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] Step 0b clarify sub-step still describes inline log publish
- **Reviewer(s)**: dyn-driver-exit-contract-output.txt
- **Severity**: nit
- **Concern**: Step 0b clarify sub-step 3 (~349) still describes inline `design-log-publish.sh` capture; stale prose outside Step 5c’s new driver surface.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] upgrade-larch prune path reviewed—no defect found
- **Reviewer(s)**: dyn-prune-invariants-output.txt
- **Severity**: nit
- **Concern**: On this branch, `INSTALLED_VERSION` / `prune_cached_versions` / retention caps / `version_is_retained` for duplicate target—no correctness defect found in that path.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

