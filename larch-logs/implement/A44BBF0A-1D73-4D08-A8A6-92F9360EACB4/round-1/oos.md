### FINDING_7: [OUT_OF_SCOPE] `LARCH_CODEX_MODEL` documentation does not explain the TRIVIAL Step 2 override
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `LARCH_CODEX_MODEL` still implies that Step 2 uses the generic untagged Codex default gpt-5.6-sol, while TRIVIAL Step 2 Codex uses gpt-5.6-terra through `CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a Step 2 pointer to CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY or narrow the LARCH_CODEX_MODEL example list (follow-up; not in this diff).


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] CI recovery waterfall documentation disagrees with the registry
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The CI recovery row documents Claude→Codex→Cursor, while `implement.ci_recovery_fixer` is ordered codex→cursor→claude, creating misleading operator expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align the CI recovery row with config.ROLE_DEFAULTS implement.ci_recovery_fixer order.
  - From cursor-specialist-edge-cases: Align the table with implement.ci_recovery_fixer in config.py.
  - From cursor-specialist-testing: Pre-existing; fix in a separate docs/registry sync change.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Merge contract documentation links to a nonexistent file
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The merge contract link points to nonexistent `python/merge.py`, preventing readers from following the stated script-level contract reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Replace it with the actual merge module or canonical documentation path.
  - From cursor-specialist-edge-cases: Retarget to python/larch/git/merge.py.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Omitted `--coder` documentation is stale for difficulty-aware routing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The skill documents the omitted-`--coder` behavior as a fixed Codex→Cursor→Claude waterfall, which can mislead operators about MODERATE Cursor-first routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update the SKILL.md waterfall sentence to match difficulty-aware routing or link to docs/configuration-and-permissions.md.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Implementer dispatch reference is not synchronized with tier-specific routing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The implementer dispatch reference is not swept for tier-specific waterfall behavior and may drift from the updated public documentation and configuration maps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Mirror CODER_TOOL_ORDER_BY_DIFFICULTY and model maps from config.py.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Coder selection tests lack direct Claude coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The coder selection matrix lacks `requested=claude` coverage, so a direct `--coder claude` regression could slip through without a targeted test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pre-existing; add a matrix row when touching bootstrap coder tests.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Composer-2.5 pricing documentation omits the Teams surcharge
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The documented Composer-2.5 rates omit the Teams surcharge applied in code, so token cost estimates may appear lower than runtime pricing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pre-existing pricing-doc issue; out of scope for this routing diff.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
