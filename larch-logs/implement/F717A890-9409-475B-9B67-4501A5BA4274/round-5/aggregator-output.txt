### FINDING_1: manifest_status reads manifests from ctx.run_id instead of effective_run_id
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-ci-cap-loop-output.txt
- **Severity**: important
- **Concern**: `manifest_status()` resolves and validates the manifest path using `ctx.run_id` instead of `effective_run_id(ctx)`, so resumes where persisted state `RUN_ID` differs from argv `ctx.run_id` can miss or read the wrong manifest and misroute gh-skipped merged/open-pr/done handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-ci-cap-loop-output.txt: Address the concern above.

### FINDING_2: _try_current_branch duplicates git.try_current_branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_try_current_branch()` reimplements existing branch-probe behavior with a broad exception path instead of using `git.try_current_branch()`, increasing the chance of divergent detached-HEAD or checkout handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Counter persistence is repeated across many state-write call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Many `_write_ship_state()` / `_write_terminal_state()` calls repeat counter kwargs manually even though `ResumeCounters` exists, making it easy for future writes to omit a counter and reset session-wide caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: _resume_plan is too large and centralizes too much classification logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` is a large classifier embedded in an already large driver module, making future resume edge cases and bash-parity precedence harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Resume tests duplicate large fixtures and monkeypatch stacks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: New resume tests duplicate substantial state-file fixtures and common monkeypatch setup, increasing maintenance cost and drift risk as more acceptance cases are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] _fresh_resume_plan exposes an unused counters parameter
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-resume-fsm-output.txt
- **Severity**: nit
- **Concern**: `_fresh_resume_plan()` accepts `counters` but always discards it, creating misleading API surface about whether stale counters can affect fresh routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-resume-fsm-output.txt: Address the concern above.

### FINDING_7: Iteration-cap stall handling is duplicated in CI-loop branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two CI-loop branches duplicate the same iteration-cap stall write/result handling, so future cap-semantics changes could diverge between paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: ResumePlan duplicates ResumeCounters scalar fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ResumePlan` repeats counter fields instead of composing `ResumeCounters`, requiring coordinated edits across multiple types/factories when counters change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Resume state lookups repeatedly reread the state file
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Resume classification performs many per-key `read_state_kv()` calls, each reparsing the full state file; this is inefficient on the hot resume path and overlaps with a broader pre-existing `read_state_kv()` design issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Boolean state parsing is duplicated across modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Boolean parsing exists separately in `ship.py` and `run_logs.py`, risking inconsistent strictness between hydration and write/read behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Conflict handoff is surfaced as a generic stalled outcome
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PrePushConflictHandoff` subclasses `Stalled`, so orchestrators must infer conflict-handoff intent from persisted state rather than a distinct outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Gh-skipped local_merged treats manifest DONE as a standalone merged signal
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-postmerge-idempotence-output.txt
- **Severity**: important
- **Concern**: In gh-skipped resumes, `local_merged` can classify a run as merged based on manifest `DONE` plus a PR number without requiring agreeing state such as `PR_CLOSED`, `PHASE=postmerge/done`, or post-merge `MERGE_RESULT`, allowing premature postmerge/done routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt, dyn-state-persistence-output.txt, dyn-postmerge-idempotence-output.txt: Address the concern above.

### FINDING_13: Missing ITERATION=50 non-pass cap stall coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the plan-required case where an open-pr resume at `ITERATION=50` receives a wait/non-pass monitor outcome and should stall after monitor handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Missing two-invocation terminal counter round-trip coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not verify that counters persisted across an exit-3/exit-6 handback survive a second `run_ship()` invocation and are reused on the next monitor entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Missing open-pr resume coverage with leftover OOS artifacts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover open-pr resume when OOS/security sidecar artifacts are present, so accidental re-enabling of OOS gates on open-pr resume would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Missing no-state-file plus argv PR-number fresh-routing coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover the plan-required case where no state file exists but `ctx.pr_number` is set; the expected route is fresh checks rather than open-pr resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt: Address the concern above.

### FINDING_17: Missing two-invocation blocked-rebase marker preservation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Tests do not verify that blocked-rebase continuation markers such as `RESUME_PHASE`, `CALLER_KIND`, and counters remain intact across a second refusal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Missing transient_rerun_attempted counter persistence coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover terminal handback with `transient_rerun_attempted=True`, leaving `TRANSIENT_RETRIES` persistence unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] test_manifest_status encodes the old ctx.run_id precedence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: `test_manifest_status` currently expects `ctx.run_id`-only lookup behavior, so fixing `manifest_status()` to use `effective_run_id(ctx)` requires rewriting this test contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-fsm-output.txt: Address the concern above.

### FINDING_20: Durable state flags can override argv and force gh-skipped routing
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-state-injection-output.txt
- **Severity**: important
- **Concern**: State-file durable flags such as `REPO_UNAVAILABLE` and `FORKED_TARGET` can override argv/context, disable normal GitHub/branch verification, and steer resume into gh-skipped open-pr/merged paths based on tampered state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-state-injection-output.txt: Address the concern above.

### FINDING_21: State content is trusted after path confinement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Although the state file path is confined under tmpdir, the content is still fully trusted for counters, durable flags, and classification before stronger integrity/session binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: Additional plan-mandated resume acceptance scenarios are missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Beyond separately identified gaps, the plan-fidelity review reports missing acceptance coverage for invalid PR identity fresh routing, stale merged flags routing OPEN, and repo-unavailable identity preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: Fresh no-state-file routing lacks an early branch-safety guard
- **Reviewer(s)**: dyn-resume-fsm-output.txt
- **Severity**: important
- **Concern**: When no state file exists, `_resume_plan()` returns fresh without probing the current branch or applying the main/master guard, allowing checks and initial state writes before later postbump safety checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-fsm-output.txt: Address the concern above.

### FINDING_24: Corrupt state metadata is collapsed into checkout-mismatch refusal
- **Reviewer(s)**: dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: Invalid persisted metadata such as bad `BRANCH_NAME`, `PR_URL`, `MERGE_RESULT`, or `REPO` is surfaced as `checkout-mismatch`, conflating corrupt-state repair with real checkout mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-fsm-output.txt: Address the concern above.

### FINDING_25: RUN_ID is not hydrated from persisted state before rewriting state
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state()` writes `RUN_ID=ctx.run_id`, while resume hydration does not restore `run_id` from state, so a resumed write can overwrite the persisted session `RUN_ID` with stale argv data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Normal gh.pr_view failures can reset counters through fresh fallback
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: A transient `gh.pr_view` failure after handback can route to fresh and reset CI counters even when branch/PR identity in state is otherwise valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_27: CI loop increments ITERATION for fix-only and transient-rerun paths
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: important
- **Concern**: Python increments `iteration` for `monitor.did_fixing` and `monitor.transient_rerun_attempted`, while bash only bumps `ITERATION` on rebase-consuming paths, potentially hitting iteration caps earlier than bash parity allows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Terminal fixer handbacks may increment FIX_ATTEMPTS differently from bash
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: latent
- **Concern**: `_monitor_persisted_counters()` increments `fix_attempts` for terminal handbacks such as `first-fixer-non-health`, while bash exits without bumping that counter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] monitor.action == wait branch appears dead on the real poll_ci path
- **Reviewer(s)**: dyn-ci-cap-loop-output.txt
- **Severity**: nit
- **Concern**: The iteration-increment guard includes `monitor.action == "wait"`, but real `poll_ci()` spins until a non-wait decision, making that branch misleading outside stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-cap-loop-output.txt: Address the concern above.

### FINDING_30: PR_URL validation permits command-substitution-shaped payloads
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: latent
- **Concern**: `_PR_URL_RE` allows characters such as `$`, `(`, and `)`, so tampered state can preserve command-substitution-looking URLs for future consumers even if current bash readers quote safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Some write-path state fields lack format validation
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: latent
- **Concern**: Existing write validation only constrains selected fields, while fields such as `REPO`, `PR_TITLE`, `IMPLEMENT_TMPDIR`, and `MANIFEST_PATH` are written without equivalent format checks; current bash usage mitigates execution risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Open-pr OOS gate skip is an intentional workflow trade-off
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: nit
- **Concern**: Open-pr resume deliberately bypasses OOS/security sidecar gates per plan; the reviewer framed this as a workflow-integrity trade-off rather than a new shell-injection issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Positive hardening observations
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: nit
- **Concern**: The reviewer noted existing hardening in this branch, including tmpdir state confinement, repo agreement checks, state value validation, conflict-file traversal checks, blocked-rebase PR_URL sanitization, and newline rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.

### FINDING_34: Merged-resume path can write PHASE=done after skipped postmerge
- **Reviewer(s)**: dyn-postmerge-idempotence-output.txt
- **Severity**: important
- **Concern**: The merged resume path writes `PHASE=done` whenever `run_postmerge_phase` returns OK, but `finalize.postmerge` can return OK for `merge=false` without substantive postmerge work, allowing incomplete runs to be marked done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-idempotence-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] finalize.postmerge can return OK despite main verification or cleanup problems
- **Reviewer(s)**: dyn-postmerge-idempotence-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `finalize.postmerge` behavior reports OK even when main verification is unexpected or cleanup is partial, which can still let callers persist `PHASE=done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-idempotence-output.txt: Address the concern above.
