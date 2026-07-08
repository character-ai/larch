### FINDING_2: [OUT_OF_SCOPE] step-5-resume can double-start without a live-registry rejoin
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: `step-5-resume.sh` can launch a second daemon on the same step slug because it does not rejoin a live registry row or reuse a completed canonical result before `bgjob start`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Resume launcher lacks live-registry rejoin before bgjob start. Repeated MAV resume while prior resume daemon runs can double-start on shared envs. Add the same registry probe/rejoin pattern used by step-5-review.sh.
  - From cursor-specialist-testing: Resume launcher lacks live-registry rejoin before bgjob start. Repeated MAV/coder resume could start a second implement-step5-resume daemon racing on merge/result envs. Add rejoin logic mirroring step-5-review.sh if resume duplication becomes a observed failure mode.
  - From dyn-dyn-bgjob-flow: Unlike `step-5-review.sh:61-210`, the resume launcher always truncates merge input and calls `bgjob start` for `implement-step5-resume` with no live-registry probe or rejoin. A repeated MAV/coder resume invocation (for example after a premature turn while the first resume daemon is still running) can start a second daemon on the same step slug, clobbering registry rows and racing on `$IMPLEMENT_TMPDIR/bgjob/implement-step5-resume.result.env` and `$IMPLEMENT_TMPDIR/bgjob/implement-step5-resume.merge.env`. Add the same fail-closed registry and canonical-result checks used in `step-5-review.sh` before resume `bgjob start`: rejoin via `bgjob wait` when a live identity-valid `implement-step5-resume` row exists or when a canonical completed result env is already present; clear only stale/dead rows before a fresh start; and add matching cases to `skills/implement/scripts/test-step-5-review.sh` or a sibling resume harness.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] orphan-timeout coverage still relies on the removed detach sidecar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The orphan-timeout / death-coverage path still leans on the removed detach-sidecar behavior, so bgjob-owned Step 5 orphan handling is not being exercised on the active path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Retire or rewire orphan detection to bgjob registry/dead semantics.
  - From cursor-specialist-edge-cases: Rewrite the test against bgjob wait envelopes or drop the legacy --orphan-timeout-s path
  - From cursor-specialist-testing: Add pytest that exercises bgjob-owned step-5-review orphan/death behavior, or update acceptance #4 to reference only test-step-5-review.sh.
  - From cursor-specialist-testing: Rewrite the test against bgjob-owned wrapper behavior or relocate orphan coverage entirely to test-step-5-review.sh.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] step-5-resume parent launcher lacks direct harness coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: The parent-mode `step-5-resume.sh` contract is only indirectly covered, so stdout/argv shape and merge-env cleanup regressions could slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Resume parent launcher contract is not harness-tested. Resume start stdout or merge-env truncation regressions lack CI coverage. Add a sibling harness for step-5-resume.sh parent mode.
  - From cursor-specialist-testing: No executable test-step-5-resume.sh harness covers parent launcher stdout and merge-env truncation. Parent launcher regressions may pass CI while child-only pytest and prose pins remain green. Add a sibling harness modeled on test-step-5-review.sh when resume launcher churn resumes.
  - From codex-specialist-testing: The parent-mode resume launcher has no direct harness coverage in this diff. A regression in the required one-line bgjob launch stdout or `--merge-result-env` plumbing could ship unnoticed because current tests only exercise `--bgjob-child`. Add a shell harness that runs `step-5-resume.sh` in parent mode, asserts the exact stdout line and argv, and checks stale merge-env cleanup and sidecar behavior.
  - From dyn-dyn-bgjob-flow: The wrapper harness exercises parent `step-5-review.sh` rejoin, DEAD, timeout, and orphaned paths, but has no parent-launcher case for `step-5-resume.sh`; regressions in the thin resume start contract can still ship without CI signal.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: Live rejoin can delete the canonical Step 5 result env
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `step-5-review.sh` can delete a freshly written canonical result env during live-registry rejoin, and partial-live registry states can be misclassified as stale in a way that risks duplicate daemon starts or missed success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Do not delete the canonical result env on the live-registry rejoin path. Clear stale result envs only before a fresh start, or make wait ignore stale results using registry identity/start-time.
  - From codex-specialist-edge-cases: Rejoin when the daemon is live; fail closed or identity-cleanup when only the child is live; clear only when both identities are dead.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_6: [OUT_OF_SCOPE] direct shell stall exit semantics diverge from the Python dispatcher
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: The direct shell `--ready-to-commit` path still exits 1 on `NEXT_ACTION=stall` while the Python dispatcher returns 0 for the same routed stall, so stall callers can observe inconsistent semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: If a future chunk reuses direct shell --ready-to-commit, align its routed-stall rc with python/larch/implement/dispatch_commit_route.py:934-948.
  - From dyn-dyn-bgjob-flow: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_7: [OUT_OF_SCOPE] docs still reference the retired checks-commit-route flow
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The step5-self-review docs still point at the retired checks-commit-route flow instead of the bgjob wait path, so the documented repair-loop can drift from the launcher actually invoked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update the site table to run-step-checks.sh plus implement-checks-step5-self-review bgjob wait


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

