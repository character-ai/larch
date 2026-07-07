### FINDING_2: [OUT_OF_SCOPE] main-health flap heuristic is too broad
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-main-health
- **Severity**: major
- **Concern**: `_has_named_repository_failure` treats any failed named job as repository failure, so infra-only failures, cancelled jobs, or timed-out workflow rows can be misread as repo defects and block merge/post-merge or route a same-SHA rerun into repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] forked main-health queries ignore upstream_repo
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-main-health
- **Severity**: minor
- **Concern**: Forked main-health queries still read `repo=working.repo` and never pass `upstream_repo`, so they can inspect fork push runs instead of the upstream default-branch CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] pre-merge main-health merge tests are missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-main-health
- **Severity**: major
- **Concern**: The planned tests for the pre-merge main-health gate are missing, so regressions in red-main routing, repair-marker allowance, and pending/error stall behavior can slip through unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] postmerge sentinel is written before push watch completes
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `run_postmerge_phase` writes the postmerge sentinel before the push-watch work is complete, so a direct caller can make run-log commits look blocked even though the actual post-merge watch has not finished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_9: main-health repair markers and handoff fields are not preserved
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The ship result / route-exit handoff path drops `MAIN_HEALTH_HEAD_SHA` and related repair-state fields, so repaired red-main failures cannot propagate the markers needed to allow the next merge or post-merge repair step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_10: [OUT_OF_SCOPE] CI pass after a fix push can still be reported as success too early
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-main-health
- **Severity**: major
- **Concern**: After a pushed fix, `_run_cycle` can return `passed` without checking for a durable fix or whether the original failure still looks flaky, so a no-op rerun can exit as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] main-CI error status does not block admission
- **Reviewer(s)**: dyn-dyn-main-health
- **Severity**: minor
- **Concern**: A main-CI error status does not block admission, so degraded `gh` reads can still let the run proceed instead of stalling for operator attention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] emergency repair remains prompt-only
- **Reviewer(s)**: dyn-dyn-main-health
- **Severity**: minor
- **Concern**: Emergency repair is still a prompt-only flow with no Python driver, so an interrupted repair session cannot mechanically resume branch/PR automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_16: same-SHA flap detection can miss failures behind the 20-row window
- **Reviewer(s)**: dyn-dyn-main-health
- **Severity**: major
- **Concern**: Same-SHA flap detection only inspects the first `gh run list` page, so an older failure can fall off the window while the latest row is `success` and `main_health` returns `pass` instead of repair-needed `fail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-main-health: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

