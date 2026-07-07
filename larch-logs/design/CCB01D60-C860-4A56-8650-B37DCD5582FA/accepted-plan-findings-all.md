### FINDING_1: Step 6 in-flight gate still misses live Step 5c bgjobs
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `design_step6.py` still treats `.bg-wait-active` as the only in-flight signal. Once Step 5c moves to bgjob and stops holding that marker, Step 6 can see an active publish as idle and run cleanup before publish/final-summary finish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/design/design_step6.py`: replace `_step6_in_flight` with bgjob registry/result-env liveness for `design-step5c`, keep terminal-sentinel precedence, and update the stale `<task-notification>` diagnostics
  - From Codex-Innovation: Add `python/larch/design/design_step6.py` to UPDATED and make `_step6_in_flight` key off the Step 5c bgjob result or terminal contract instead of the removed marker.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/design/design_step6.py`. Replace the marker-only branch with bgjob in-flight detection (live registry entry or absent `bgjob` result env for `design-step5c` while terminal sentinel absent). Keep terminal-sentinel precedence. Update diagnostics to reference bgjob wait, not `<task-notification>`. Extend the existing `test_design_lifecycle.py` Step 6 matrix accordingly.


### FINDING_2: Abandoned checks stall recovery still depends on `.bg-wait-active`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The abandoned-checks signal still comes from `.bg-wait-active`, so dead Step 3 / Step 5 self-review bgjobs no longer trigger the transient-infra retry path and stall recovery misclassifies killed checks legs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/state/_tokens.py` (and list `python/tests/state/test_stall_recovery.py`): detect abandoned bgjob registry rows for `implement-step3-checks` and `implement-step5-self-review` via identity-checked owner/PGID death instead of `.bg-wait-active`
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/state/_tokens.py` (and any `_state_mgmt.py` clear helper) plus targeted `python/tests/state/test_stall_recovery.py` / `python/tests/implement/test_implement_dispatch.py` updates. Detect abandoned bgjob registry rows for the checks steps with identity-checked dead owner/daemon, not bare `.bg-wait-active`.
  - From Cursor-Requirements: Retire or narrow _abandoned_checks_marker_stall_step to bgjob registry/result-env signals; update python/larch/state/_classify.py, _state_mgmt.py, and python/tests/state/test_stall_recovery.py accordingly


### FINDING_4: Inverted bg-wait lint scope still misses research coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The inverted lint rule still does not cover the full intended `skills/` surface, especially research markdowns and seeded allowlist coverage, so `make lint` can diverge from the acceptance grep and leave `run_in_background` regressions uncaught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Seed the new allowlist with `skills/shared/design-background-wait.md` (reason: issue-2 deletion) and any other skills paths intentionally left unchanged this PR; pin in `python/tests/lint/test_lint_bg_wait_coverage.py`
  - From Cursor-Innovation: Extend SCOPE_PATTERNS (or the inverted linter) to include skills/research/**/*.md when flipping to reject run_in_background
  - From Cursor-Requirements: Add skills/research/**/*.md to the inverted lint scope (or an equivalent all-skills glob) when repurposing the rule


### FINDING_9: Derived bgjob paths need slug and symlink containment checks
- **Reviewer(s)**: Codex-dyn-Process Safety
- **Severity**: major
- **Concern**: The new registry, result, and log paths interpolate untrusted names directly, so a crafted step/run-id or a symlinked TMPDIR can escape the intended job root unless every derived path is validated and resolved safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Process Safety: Validate each name against a strict slug, resolve every derived path, reject `..` and separators, and refuse symlinked registry, result, and log paths on read and write.


### FINDING_10: Deny hook must fail closed and define active-run identity
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The new PreToolUse deny hook can be bypassed if parse errors or payload-shape errors fall open, and the active-run test still needs an explicit identity rule so same-clone background launches are reliably blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the hook fail closed whenever `run_in_background` cannot be ruled out, and reserve fail-open only for cases that are definitely unrelated to Bash background launches
  - From Cursor-Innovation: Define the hook contract in the plan: treat an active run as an identity-valid row under ~/.cache/larch/daemons/ whose CLONE_PATH matches canonical cwd (reuse session_env keepalive matching); document fail-open only when clone identity is unprovable


### FINDING_1: Finalize-step5 still binds abort/success parsing to task-notification stdout
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 5 finalize contract still teaches abort/success handling to read `FINAL_SUMMARY_PATH` from completed task-notification stdout, so the migrated Step 5c path can miss the summary source and skip required final-summary emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/references/finalize-step5.md. Replace task-notification stdout bindings with bgjob DONE result-env or captured bgjob wait stdout, aligned with the updated final-summary-emit.md profile.
  - From Codex-Arch: Add this file to UPDATED and rewrite the Step 5c / 5d contract around bgjob start, bgjob wait, result envs, and terminal-sentinel precedence.
  - From Codex-Innovation: Update this file to read the bgjob result env or the new shared bgjob-wait contract instead of task-notification stdout
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/finalize-step5.md: rebind abort and success parsing to bgjob wait DONE output and/or $TMPDIR/bgjob/design-step5c.result.env via design read-result-env; remove task-notification wording


### FINDING_3: bgjob wait does not gate DONE on BGJOB_RC
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The shared bgjob wait contract treats `BGJOB_STATUS=DONE` as normal continuation without checking `BGJOB_RC`, so timeout/orphaned results could be mistaken for successful completion instead of failure or stall routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In skills/shared/bgjob-wait.md require that DONE with BGJOB_RC in {timeout, orphaned} or missing required step KVs routes through the step existing failure or stall handling, not normal continuation. Pin the rule in scripts/test-implement-structure.sh or scripts/test-design-structure.sh.
  - From Cursor-Requirements: In bgjob-wait.md require parsing BGJOB_RC on DONE and routing timeout/orphaned/non-zero values through each step's existing failure or stall path; mirror in python/tests/bgjob/test_wait.py and prompt-shape harnesses


### FINDING_6: Step 4 tail contract still teaches the retired background fence
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The loaded Step 4 tail contract still describes the orchestrator backgrounding the fence and arming `.bg-wait-active`, so the skill surface remains stale even if the shell wrapper changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the markdown contract to UPDATED and replace the Step 4 launch text with the shared bgjob wait contract.


### FINDING_7: step-8-ship.md still contains the legacy run_in_background relaunch contract
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: `step-8-ship.md` still describes the old relaunch path, so the new bg-wait lint will flag the untouched contract doc and block acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `skills/implement/scripts/step-8-ship.md` to the migration set and replace the legacy relaunch wording with the shared bgjob start/wait contract


