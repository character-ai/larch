### FINDING_12: [OUT_OF_SCOPE] Open-pr resume can bypass leftover security/OOS sidecar material
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: latent
- **Concern**: Open-pr resume skips `_materialize_manifest_oos` and the security sidecar unless `OOS_PENDING` is set, so leftover OOS/security observations from an interrupted fresh run may be bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Terminal CI handbacks may not persist consumed fixing attempts
- **Reviewer(s)**: dyn-ci-caps-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_monitor_persisted_counters()` increments `transient_retries` but not `fix_attempts` for terminal handbacks with `monitor.did_fixing=True`, diverging from the plan language and potentially allowing an extra fixing attempt after resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-caps-output.txt: If parity with bash is intended, document the asymmetry in `_monitor_persisted_counters` and keep tests; if the plan’s “consumed increments” language means all `did_fixing` cycles, increment `fix_attempts` (and persist `rebase_count` when `goto_rebase` completed) in `_monitor_persisted_counters` before `_write_terminal_state`, and extend tests beyond the current failed-fixing case.
  - From cursor-specialist-security-output.txt: Resolve plan-vs-test contradiction; if test is authoritative, update plan description to say terminal handbacks do not count failed fix attempts
  - From cursor-specialist-edge-cases-output.txt: Add `fix_attempts=fix_attempts + (1 if monitor.did_fixing else 0)` as the third tuple element, or document in the helper that terminal handbacks intentionally do not count `did_fixing` and update the plan spec to match.
  - From cursor-specialist-plan-fidelity-output.txt: Either document this deliberate divergence in the plan/code comment and update the acceptance criterion, or increment `fix_attempts` in `_monitor_persisted_counters` (matching `iteration` + `transient_rerun_attempted`) so the terminal and continue paths agree.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] finalize.postmerge OK can still mask partial cleanup
- **Reviewer(s)**: dyn-postmerge-flow-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior allows `finalize.postmerge()` to return `Outcome.OK` despite unexpected main status or partial cleanup, after which the driver writes `PHASE=done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-flow-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Manifest DONE status is implemented but not consumed by resume routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: `run_logs.manifest_status()` exists, but `_resume_plan()` does not use it, leaving gh-skipped merged/done routing under-wired relative to the plan’s qualified manifest predicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fold manifest_status into local_merged only when another merged predicate already agrees
  - From cursor-specialist-testing-output.txt: Wire per plan with guards or add test documenting manifest ignored for merged.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_6: [OUT_OF_SCOPE] Terminal state PHASE loses the specific stall step
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Terminal stall state writes a coarse `PHASE=stalled` instead of preserving the specific step token, reducing operator visibility into stall cause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider preserving step in PHASE or document Python-only coarser PHASE contract


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Fresh fallback can persist stale counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-caps-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Fresh resume paths can carry restored non-zero counters into state writes even though CI locals start at zero, causing inconsistent cap accounting across handbacks or later open-pr resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Force zero counters in `_fresh_resume_plan()` (or zero them at the start of the `fresh` branch) for all state writes on that path; keep counter restoration exclusively for validated `open-pr` / `merged` / terminal handback paths.
  - From dyn-ci-caps-output.txt: When `resume.start == "fresh"`, pass zeros into all `_write_ship_state` / `_write_terminal_state` calls (or build `_fresh_resume_plan` without forwarding read counters except on explicit `open-pr` / `merged` / `done` resumes). Align `test_fresh_fallback_hydrates_modes_and_preserves_counters` with that contract if stale-counter preservation on gh-failure fresh was not intentional.
  - From cursor-specialist-plan-fidelity-output.txt: Consider zeroing counters in the state write for the fresh path (not the open-pr seed, which already uses 0) so stale restored values cannot bleed into the next open-pr CI start


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Additional plan-listed test gaps remain unpinned
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: Out-of-scope reviewer notes identify additional missing regression coverage for acceptance-matrix cases such as wrong PR head, repeated blocked-rebase continuation, cap 49/50, terminal handback round trips, gh/fork/repo-unavailable routing, and main CI postmerge non-OK behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

