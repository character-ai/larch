### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate carryover predicate in manifest builder
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `path_is_pre_coder_carryover` was extracted but `round_coder_delta_paths` still inlines the same carryover `cmp` logic. A later carryover rule change updates only the predicate; the manifest builder keeps excluding or including different paths than the guard, reviving false positives/negatives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Call `path_is_pre_coder_carryover` from `round_coder_delta_paths` instead of duplicating the grep/cmp block.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: No direct unit test for round_has_non_carryover_tracked_residue
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Post-commit gate regressions might only surface through heavier orchestrator paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add sed-extracted residue helper test with carryover-only vs hook-residue fixtures.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Carryover dirt may accumulate across Step 5 rounds
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Rounds may complete `applied` with warned carryover dirt left in the tree. Later Step 5 rounds or ship-pr assume a clean tree; carryover accumulates across rounds with only stderr warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit carryover path KVs or document/implement Step 5 cleanup expectations in implement SKILL.md.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Duplicate carryover warnings from guard and residue helper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Duplicate carryover warnings from guard and residue helper. Operators see duplicate breadcrumbs per path per round; noisy logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Warn once per path per round or only in the pre-commit guard.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: outside-manifest-break-carryover stub diverges from plan-specified append
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `outside-manifest-break-carryover` stub uses git add/restore instead of plan-specified append to `other.txt`. Plan D says append during dispatch; impl uses index/worktree manipulation. Literal append would likely put `other.txt` in coder-stage-paths.txt and skip the outside-manifest guard via manifest continue, weakening fail-closed coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a short comment that the stub breaks carryover match while keeping other.txt outside the manifest; optional align plan text—no production change required.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Near-duplicate carryover loops emit duplicate warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two near-identical loops differ only by manifest grep; both emit the same carryover warning. Carryover-only rounds log duplicate warnings per path (pre-commit then post-commit residue), adding noise without changing outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared pre_head load + carryover iteration; parameterize manifest filtering and downstream action.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Repeated carryover test fixture setup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: New orchestrator tests copy the same carryover repo setup. Future fixture tweaks require editing three blocks; one miss desynchronizes integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a `bootstrap_carryover_repo` helper used by all three cases.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: No test for multi-round re-entry after manual commits (#3227)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No test for multi-round re-entry after main-agent manual commits (#3227 narrative). Production failure was described as manual commits between rounds with overlapping files; new tests only cover pre-dispatch carryover dirt, not clean-tree overlap after committed manual fixes. Production #3227 failure mode may differ from pre-dispatch carryover; fix could ship without covering that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a step5-starting-round or dispatch integration case: manual commit between rounds, then coder success on overlapping manifest paths.
  - From cursor-specialist-edge-cases-output.txt: Add multi-round resume integration test or document remaining gap vs issue narrative.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: outside-manifest-break-carryover stub lacks worktree mutation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `outside-manifest-break-carryover` uses index/worktree split, not worktree mutation. Fail-closed coverage may not match a coder that actually edits a snapshotted path in the worktree; behavior also depends on git diff index vs worktree semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stub that mutates `other.txt` in the worktree, or assert manifest excludes `other.txt` in setup.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: carryover-orchestrator omits commit-count assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Erroneous follow-up commit might not be detected if assertions on file list still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert rev-list count from initial HEAD is exactly 1.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

