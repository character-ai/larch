### FINDING_12: [OUT_OF_SCOPE] LARCH_PLAN_REVIEW_REVISE_SH override can point at arbitrary code
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `LARCH_PLAN_REVIEW_REVISE_SH` test hook can redirect the revise path to arbitrary code with tmpdir access if not documented or cleared in production paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] Gate B copy omits ok-fallback distinction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate B operator-facing copy does not distinguish `ok-fallback`, so operators may not notice that tier 4 performed a full replacement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Unified-diff cases 14-16 match current implementation
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that cases 14-16 align with the current first-fenced / last-unfenced extraction implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] Unfenced trailing narration becomes invalid-patch
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: Unfenced unified-diff extraction keeps trailing lines until EOF, which can classify trailing narration as `invalid-patch` rather than silently misapplying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] merge_tier4_status rank merge matches documented severity order
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports that the rank merge matches the documented severity order after the round-1 refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Implement-run artifacts are unrelated noise
- **Reviewer(s)**: dyn-patch-extraction-output.txt, dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Implement-run artifacts under `larch-logs/implement/3F2B5CF2-.../` are operational noise rather than part of the revise logic or #3146 fix surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt, dyn-artifact-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] Tier-4 artifact names are internally consistent
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Tier-4 fallback artifact names are internally consistent across implementation, allowlists, docs, and tests, though they deliberately diverge from the issue plan’s reuse strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] prompt.txt overwrite is documented
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Tier 4 overwrites published `prompt.txt` with the file-replacement prompt, and the reviewer reports this is documented and included in snapshot/publish by design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] revise-plan doc uses generic candidate patch name
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.md` lists `<tier>-candidate.patch`, while tier 4 writes names like `codex-fallback-output-candidate.patch` covered by `*-candidate.patch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_27: [OUT_OF_SCOPE] Acceptance notes missing REVISE_TIER_4_STATUS test coverage
- **Reviewer(s)**: dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: Out-of-scope reviewers also noted acceptance required `REVISE_TIER_4_STATUS` assertions in all cases, while only a subset assert it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Tier-4 absent-tools path lacks harness coverage
- **Reviewer(s)**: dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: When CodeX and Cursor are absent and Claude returns empty, tier 4 reports `no-patch` rather than `skipped-not-present`; this follows severity ordering but lacks a dedicated harness case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tier4-state-machine-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] Regression provenance identified in branch commits
- **Reviewer(s)**: dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: The reviewer attributes the `printf|tee` finalize regression and separate fallback artifacts to commit `e9490962`, not the initial tier-4 design commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tier4-state-machine-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] REVISE_WINNING_TIER missing from documented KV list
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `REVISE_WINNING_TIER` is emitted but not listed in the sibling documentation’s numbered KV contract, creating doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Missing original unfenced preamble regression case
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: There is no harness case for an unfenced prose preamble before `--- a/plan.txt`, leaving the original Cursor-shaped bug scenario under-covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

