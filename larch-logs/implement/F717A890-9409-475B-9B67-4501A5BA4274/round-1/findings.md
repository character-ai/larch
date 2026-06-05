### FINDING_1: manifest_status helper is unused in resume routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_logs.manifest_status()` is implemented and tested but `_resume_plan()` never consults it, so gh-skipped merged classification cannot use manifest `DONE` even under the plan’s restricted “agreeing predicate” semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: duplicate branch-probe helper diverges from shared git helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_try_current_branch` duplicates `git.try_current_branch` with different failure semantics, risking drift in resume classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: resume acceptance matrix coverage is largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The new tests cover only a small subset of the plan’s resume matrix; branch/head routing, gh failures, rebase-continuation refusal, cap 49/50 semantics, terminal counter round-trips, protected-branch refusal, Part B modes, and ship-level monitor seams can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: state bool parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_state_bool_text` duplicates run-log bool parsing, creating parallel strict-bool implementations that can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: _resume_plan is a large monolith
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_resume_plan` is large and embedded in an already large `ship.py`, making precedence and future resume changes harder to reason about and test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: ResumePlan duplicates ResumeCounters fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ResumePlan` repeats counter fields already represented by `ResumeCounters`, risking schema drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: ResumePlan.start lacks a constrained type
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ResumePlan.start` is a plain `str`, so invalid resume start tokens are caught only at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: repeated counter kwargs make state writes error-prone
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Many state write sites repeat the same counter keyword arguments, increasing boilerplate and omission risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] ship.py is a pre-existing large orchestrator
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ship.py` was already a large orchestrator before this resume work; broader module splitting is a follow-up concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] broader acceptance matrix remains thin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt
- **Severity**: latent
- **Concern**: Several plan-listed or pre-existing acceptance cases remain uncovered beyond this diff’s core scope, including cap behavior, stale local/GitHub routing, branch guards, marker preservation, and other Phase 7 scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt: Address the concern above.

### FINDING_11: open-pr resume bypasses OOS gates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Open-PR resume can skip or clear pending OOS/security-OOS disposition state, allowing CI/merge to proceed without re-running required OOS gates after handback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: terminal handback does not persist iteration consistently
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Terminal monitor handback persists some counters but not `ITERATION`, so resumed runs near the cap can repeat the same cap/decision cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] done resume can skip postmerge for legacy state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Legacy state with `PHASE=done` and GitHub `MERGED` can return OK without a postmerge flush; reviewers marked this out of scope because new forward paths write `done` only after postmerge succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: state_file path is not constrained to the implement tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-branch-guard-output.txt
- **Severity**: important
- **Concern**: The Python ship driver validates `tmpdir` but not `state_file`, unlike bash parity; a caller-controlled state path outside the session tree can redirect resume reads/writes and forge durable flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-branch-guard-output.txt: Address the concern above.

### FINDING_15: gh-skipped routing trusts durable state without enough verification
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-branch-guard-output.txt
- **Severity**: latent
- **Concern**: State-first durable flags such as `REPO_UNAVAILABLE`/forked modes can force gh-skipped resume and route through local `PHASE`/merge predicates without GitHub verification, creating a trust-boundary/parity risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-branch-guard-output.txt: Address the concern above.

### FINDING_16: ship-state values are not newline-rejected
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state` does not reject CR/LF in values, so fields like `PR_URL` or merge results could inject extra state assignments consumed on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: resume uses ctx.repo instead of hydrated state REPO
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-gh-authority-output.txt
- **Severity**: important
- **Concern**: GitHub-authoritative resume uses argv/context `ctx.repo` while PR number, branch, and counters come from persisted state, so stale or missing repo context can validate or resume against the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-gh-authority-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] SECURITY.md overstates ship-state newline rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` claims newline rejection coverage that currently applies to finalize-state but not ship-pr-state; reviewers marked this doc/impl gap out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] manifest_status unused observation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers separately noted out-of-scope that `manifest_status()` is unused outside tests and may be a plan-only completeness gap rather than an immediate defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt: Address the concern above.

### FINDING_20: gh-skipped resume can proceed without a validated branch anchor
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt
- **Severity**: important
- **Concern**: For gh-skipped resumes, if persisted and contextual branch hints are empty, `_resume_plan` can skip branch reconciliation and classify `open-pr`/`merged`/`done` on an arbitrary checkout instead of failing closed like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt: Address the concern above.

### FINDING_21: terminal state writes detail strings into PHASE
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_write_terminal_state` can write monitor detail text into `PHASE`, leaving non-canonical phase values that confuse resume/debug tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: broad exception handling hides actionable resume failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Broad `except` blocks around branch probing and `gh.pr_view` make permanent auth/config failures hard to distinguish from transient failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] merge stall paths do not persist CI-loop counters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Merge stall returns may not persist iteration/rebase/fix counters, so re-invocation can reset budgets depending on resume classification; reviewers marked this as follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: pre-push conflict handback does not persist continuation tokens
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Python-native pre-push conflict handback can return a generic stalled result without persisting `RESUME_PHASE`, `CALLER_KIND`, or conflict metadata, so the next resume may enter CI instead of refusing unsupported continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_25: routine state writes erase handoff markers
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state()` rewrites `RESUME_PHASE` and `CALLER_KIND` as empty on routine writes, which can destroy bash continuation markers and make later resume look like a normal open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_26: stale ctx.forked can override persisted FORKED_TARGET=false
- **Reviewer(s)**: dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt
- **Severity**: important
- **Concern**: `read_durable_flags()` computes `forked=ctx.forked or forked_target`, so stale argv/env forked mode can survive state hydration, skip GitHub validation, and weaken main/master branch protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] gh.pr_view exception fresh fallback is an intentional trade-off
- **Reviewer(s)**: dyn-gh-authority-output.txt
- **Severity**: nit
- **Concern**: The broad `gh.pr_view` exception path trades transient handback for a fresh restart; reviewer marked this as an intentional plan trade-off rather than an accidental bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-authority-output.txt: Address the concern above.

### FINDING_28: fix_attempts can be over-counted from did_fixing
- **Reviewer(s)**: dyn-counter-durability-output.txt
- **Severity**: important
- **Concern**: `_monitor_persisted_counters` increments `fix_attempts` whenever `monitor.did_fixing` is true, including terminal outcomes that did not successfully push a fix, causing premature cap exhaustion versus bash semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-durability-output.txt: Address the concern above.

### FINDING_29: iteration increments after every non-merge monitor cycle
- **Reviewer(s)**: dyn-counter-durability-output.txt
- **Severity**: important
- **Concern**: The CI loop increments `iteration` after every non-merge monitor cycle, while bash only increments on specific outer-cycle/rebase advances, risking premature merge-loop cap exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-durability-output.txt: Address the concern above.

### FINDING_30: merge retry paths increment iteration without durable state parity
- **Reviewer(s)**: dyn-counter-durability-output.txt
- **Severity**: latent
- **Concern**: `ci_not_ready` and `main_advanced` merge retries increment `iteration` and continue without writing counters, diverging from bash and creating inconsistent in-memory vs persisted budget behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-durability-output.txt: Address the concern above.

### FINDING_31: counter increments can be stale on disk before handback
- **Reviewer(s)**: dyn-counter-durability-output.txt
- **Severity**: important
- **Concern**: Rebase/fix/transient/iteration counters are updated in memory, but the next state write happens later; any intervening orchestrator handback can leave consumed budget unstored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-durability-output.txt: Address the concern above.

### FINDING_32: fresh fallback does not hydrate durable mode flags from state
- **Reviewer(s)**: dyn-mode-hydration-output.txt
- **Severity**: important
- **Concern**: When `_resume_plan` falls back to `fresh` despite an existing state file, `run_ship()` uses argv defaults instead of persisted durable flags such as `MERGE=false`, `DRAFT=true`, or `REPO_UNAVAILABLE=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mode-hydration-output.txt: Address the concern above.

### FINDING_33: fresh fallback terminal writes can wipe persisted counters
- **Reviewer(s)**: dyn-mode-hydration-output.txt
- **Severity**: important
- **Concern**: The fresh checks-failure path writes terminal state with default zero counters, so degraded fresh fallback after a resume classification failure can erase session-wide caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mode-hydration-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] commit list observation
- **Reviewer(s)**: dyn-mode-hydration-output.txt
- **Severity**: nit
- **Concern**: Reviewer recorded the branch commits reviewed; this is an out-of-scope observation rather than a behavioral defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mode-hydration-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] no-state path lacks entry-level protected-branch check
- **Reviewer(s)**: dyn-branch-guard-output.txt
- **Severity**: latent
- **Concern**: With no state file, `_resume_plan()` returns fresh without probing the current branch, so checks can run before later protected-branch guards; reviewer marked this defense-in-depth gap as largely pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-branch-guard-output.txt: Address the concern above.
