### OOS_1: [OUT_OF_SCOPE] Branch bundles Phase 5 with unrelated commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: PR mixes Phase 5 Python ship-pr work with rebase, `upgrade-larch`, and `larch-logs` changes, increasing review/CI blast radius and mis-attribution risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Rebase `has_bump=False` / `defer_push` / `apply_bump` defaults behave as designed
- **Reviewer(s)**: dyn-rebase-parity-inputs-output.txt
- **Severity**: latent
- **Concern**: `has_bump=False` skips rebump but still syncs main; `defer_push=True` skips force-push; keyword defaults on `apply_bump` remain valid—documented control-flow, not regressions from this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-parity-inputs-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] Rebase fork / classify_bump / force-push remote parity follow-ups
- **Reviewer(s)**: dyn-rebase-parity-inputs-output.txt
- **Severity**: latent
- **Concern**: `classify_bump` hardcodes `origin`/`main` while rebase can use other bases; `_force_push_branch` always pushes `origin`; same splits as bash—fork end-to-end parity deferred, not introduced by new flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-parity-inputs-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] `validate_base_remote_ref` charset parity with bash
- **Reviewer(s)**: dyn-rebase-parity-inputs-output.txt
- **Severity**: latent
- **Concern**: `^[A-Za-z0-9._/-]+$` validation matches `rebase-push.sh` argv-safety; intentional shared rejection of out-of-charset branch names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-parity-inputs-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] No timing aggregation despite plan mention (correctness slot)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Timing scrape deferred vs plan wording; may stay empty until explicitly documented in README.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Bash merge path lacks pre-merge already-MERGED probe
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `merge-pr.sh` may double-attempt merge if driver forgets `already_merged` remap; pre-existing bash gap deferred to Phase 7 driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Missing existing-PR `force_push_recovery` escalation test
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance test for existing-PR push failure → `force_push_recovery` not mirrored in `test_pr.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] gh checks text fallback gap lower severity than OOS gate
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Empty JSON arrays match bash “not ready”; missing text fallback when JSON is unparseable is a smaller divergence than the OOS markdown-count bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Flush-recoverable predicates align when git succeeds
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Subject prefix, count ≤5, `larch-logs/`-only paths, and `merge-base --is-ancestor` match bash when git commands succeed; divergence is mainly the `log_subjects` exception path (covered in FINDING_27).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Merge test / bash parity depth below plan (dyn parity pass)
- **Reviewer(s)**: dyn-bash-python-parity-output.txt, dyn-flush-split-invariant-output.txt
- **Severity**: latent
- **Concern**: Exhaustive merge-variant and K1/P1/N1/N2a parity called for in plan are thin in CI; does not negate functional bugs but leaves flush-recovery parity unverified (overlaps in-scope FINDING_1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.
  - From dyn-flush-split-invariant-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Large `refresh-run-logs.sh` surfaces omitted as expected Phase 5 stubbing
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: latent
- **Concern**: Execution-issue flushes, `write-final-report.sh`, real token/timing scripts, full transcript capture, and richer `step9a1` heuristics are intentionally stubbed for this pass—not a flush-split invariant violation per se (functional gap remains in-scope FINDING_2).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] `flush_logs_post` post-merge no-git invariant satisfied
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: latent
- **Concern**: `flush_logs_post` avoids Runner/git usage; `test_flush_logs_post_no_git_commit` covers the invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

