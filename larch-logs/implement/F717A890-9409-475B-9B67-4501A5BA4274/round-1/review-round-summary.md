# Review Round 1

- Mode: `diff`
- 15 accepted, 11 rejected (11 exonerated)

## Accepted Findings

### FINDING_11: open-pr resume bypasses OOS gates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Open-PR resume can skip or clear pending OOS/security-OOS disposition state, allowing CI/merge to proceed without re-running required OOS gates after handback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: state_file path is not constrained to the implement tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-branch-guard-output.txt
- **Severity**: important
- **Concern**: The Python ship driver validates `tmpdir` but not `state_file`, unlike bash parity; a caller-controlled state path outside the session tree can redirect resume reads/writes and forge durable flags.
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


### FINDING_3: resume acceptance matrix coverage is largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The new tests cover only a small subset of the plan’s resume matrix; branch/head routing, gh failures, rebase-continuation refusal, cap 49/50 semantics, terminal counter round-trips, protected-branch refusal, Part B modes, and ship-level monitor seams can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


