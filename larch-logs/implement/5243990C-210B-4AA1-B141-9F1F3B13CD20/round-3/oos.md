### OOS_1: [OUT_OF_SCOPE] Pre-existing monolithic stall-recovery-report surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing monolithic classify/report/attempt surface amplified by this branch; not introduced by E1/E2 design choice alone—track as follow-up modularization.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Intentional plan deltas (classify empty state, Step 18 stdout)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Scout notes deliberate deltas: Step 18 drops `--print-stdout`; classify skips key load on empty `ship-pr-state.sh` and uses session fallback—appear deliberate and tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] case22-classify-empty-state exercises classify guard (no defect)
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: nit
- **Concern**: `case22-classify-empty-state` correctly exercises classify guard for key-empty present file and session fallback; case name slightly misleading (file exists but key-empty).
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] classify hard-exits on syntax error without classification KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Classify still hard-exits via `validate_ship_pr_state` on syntax errors without classification KVs; malformed line aborts classify with bare exit 3—pre-existing, not introduced by clear-stall/seed extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Doc references check_ship_pr_state_format vs split helper exit matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Documentation references `check_ship_pr_state_format` but clear-stall/seed use split syntax/has_keys checks with different exit codes for zero-key files; documentation/implementation drift for edge-case exit semantics not exercised by current tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Future caller could pass arbitrary keys into rewrite_ship_pr_state_keys
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` accepts arbitrary caller-supplied key names; only current callers pass fixed names—no key allowlist or escaping, so a future caller could introduce key-side awk injection. Hardening (allowlisted keys + `awk -v`) would close the footgun; not introduced by a bad caller in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] E2 step-18b has no awk usage for this safety pass
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: nit
- **Concern**: Branch adds no awk usage in `step-18b-final-report.sh`; E2 is out of scope for this awk-safety pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Branch commit inventory (dyn-awk meta)
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: nit
- **Concern**: Commits on branch since `main` listed for context (`4d3623378` extract, `828ae39de` larch-logs, review/relevant-checks rounds, etc.)—informational only.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] cmd_seed_terminal_state lifecycle scout (no defect)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Scout attestation: empty/comment-only seed path, `tmp` guard, and failure paths emit promised `SEEDED=false` KVs—no unreachable path or bare `set -e` skip identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] STEP17_EMITTED_PRESENT informational-only (scout)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Parsed in SKILL.md but unused; emit gating fully in `EMIT_BODY`—informational-only, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Orphan temp files on mv failure (acceptable)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: On `mv` failure or noop-mv dest-assert failure, orphan `ship-pr-state.sh.tmp.*` may remain; on-disk state unchanged and KVs correct per harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

