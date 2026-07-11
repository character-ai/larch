### FINDING_1: Step 6 production launcher is outside the identity-aware rejoin contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Stale Bgjob Identity Auditor, Codex-dyn-Stale Bgjob Identity Auditor
- **Severity**: major
- **Concern**: Step 6 uses `step-6-entry.sh`, which has its own live and completed rejoin logic. If only `run-step-checks.sh` is updated, Step 6 can still reuse stale `implement-step6-checks` results after repository drift, including failed results and live jobs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/scripts/step-6-entry.sh (and step-6-entry.md) applying the same identity seeding classifier live/completed rejoin and fail-closed mismatch behavior or delegate Step 6 foreground launch to the shared checks launcher
  - From Cursor-Innovation: Add `### UPDATED: skills/implement/scripts/step-6-entry.sh` wiring the same `checks_result_identity` classifier, identity seeding, live mismatch fail-closed, and stale clear path; include `skip-to-7a` in the Step 6 terminal-action allowlist
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/step-6-entry.sh (and step-6-entry.md) wiring the shared checks_result_identity classifier live/completed rejoin paths. Mirror run-step-checks fail-closed live mismatch stale-clear and REPO_ROOT-from-session-env behavior.
  - From Codex-Pragmatic: Add step-6-entry.sh to the firm update set and apply the identity computation, merge-env seeding, live-row validation, stale-result cleanup, and completed-result validation to both Step 6 rejoin branches
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/scripts/step-6-entry.sh (and step-6-entry.md) to wire the shared checks_result_identity classifier, seed/preserve identity in the merge envelope, and mirror the live-mismatch fail-closed and stale-clear paths from run-step-checks.sh
  - From Codex-Requirements: Update `step-6-entry.sh` to compute and persist the same identity, validate it for live and completed rejoin, fail closed on live mismatches, and clear stale completed state before launching. Extend the planned wrapper regression to cover this launcher path.
  - From Cursor-dyn-Stale Bgjob Identity Auditor: Add ### UPDATED: skills/implement/scripts/step-6-entry.sh (and step-6-entry.md) and wire the shared checks_result_identity classifier for live/completed rejoin, stale clear, and live mismatch fail-closed.
  - From Codex-dyn-Stale Bgjob Identity Auditor: Add `skills/implement/scripts/step-6-entry.sh` to the firm updates, or make it call the shared identity-aware wrapper. Apply matching-identity checks to both live and completed rejoin branches, fail closed on active mismatches, and extend the Step 6 regression to cover committed, staged, unstaged, and untracked drift.


### FINDING_2: Step 6 regression coverage targets the wrong launcher
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Stale Bgjob Identity Auditor, Codex-dyn-Stale Bgjob Identity Auditor
- **Severity**: major
- **Concern**: Parameterizing `run-step-checks.sh --site step6` does not exercise production Step 6, which invokes `step-6-entry.sh`. Tests could pass while the actual Step 6 stale-result rejoin path remains broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a subprocess regression against step-6-entry.sh (including --force-checks true repair argv) or fold Step 6 into the shared launcher before parametrizing tests
  - From Cursor-Innovation: Parameterize wrapper regression against `step-6-entry.sh` for Step 6 (and keep `run-step-checks.sh` cases for Step 3 and Step 5 self-review only)
  - From Cursor-Pragmatic: Add a subprocess regression for skills/implement/scripts/step-6-entry.sh (initial and --force-checks true repair re-entry) or refactor Step 6 to delegate launcher rejoin to the shared helper and test that path.
  - From Cursor-Requirements: Add a subprocess regression against skills/implement/scripts/step-6-entry.sh (normal and --force-checks true repair re-entry) for implement-step6-checks; keep run-step-checks coverage for step3 and step5-self-review only
  - From Codex-Requirements: Update `step-6-entry.sh` to compute and persist the same identity, validate it for live and completed rejoin, fail closed on live mismatches, and clear stale completed state before launching. Extend the planned wrapper regression to cover this launcher path.
  - From Cursor-dyn-Stale Bgjob Identity Auditor: Add a step-6-entry.sh subprocess regression (or shared launcher harness) for drift-after-checks-failed, matching live rejoin, and live identity mismatch; do not treat run-step-checks --site step6 alone as Step 6 coverage.
  - From Codex-dyn-Stale Bgjob Identity Auditor: Add `skills/implement/scripts/step-6-entry.sh` to the firm updates, or make it call the shared identity-aware wrapper. Apply matching-identity checks to both live and completed rejoin branches, fail closed on active mismatches, and extend the Step 6 regression to cover committed, staged, unstaged, and untracked drift.


### FINDING_6: Validated REPO_ROOT is not explicitly propagated to child checks
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Identity may be computed from one persisted repository root while child checks resolve their repository from inherited cwd or `CLAUDE_PROJECT_DIR`, allowing checks to run against a different tree and associate results with the wrong inputs.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_7: Structure harness still references the retired inline classifier
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: minor
- **Concern**: Replacing `step_checks_result_env_state` with the shared identity classifier without updating `scripts/test-implement-structure.sh` will cause structure assertions and lint checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: scripts/test-implement-structure.sh pins for the identity classifier integration and drop step_checks_result_env_state requirement
  - From Cursor-Requirements: Add ### UPDATED: scripts/test-implement-structure.sh to the plan and testing strategy, pinning the new identity integration instead of the retired inline helper name


### FINDING_8: Shared terminal-action handling must preserve Step 6 `skip-to-7a`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Step 6 currently accepts `NEXT_ACTION=skip-to-7a` as a terminal completion. A shared classifier limited to `continue`, `stall`, and `checks-failed` could classify valid Step 6 results as incomplete or stale and force an unnecessary rerun.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: skills/implement/scripts/step-6-entry.sh` wiring the same `checks_result_identity` classifier, identity seeding, live mismatch fail-closed, and stale clear path; include `skip-to-7a` in the Step 6 terminal-action allowlist
  - From Cursor-Pragmatic: Include skip-to-7a in the shared terminal-action set or pass a step-specific allowlist into the classifier for implement-step6-checks.
  - From Codex-Pragmatic: Enumerate terminal actions per wrapper or include `skip-to-7a` in the Step 6 action set, and test identity-valid rejoin and routing for that action
  - From Cursor-Requirements: Define the recognized terminal-action set as the union used by all checks wrappers (include skip-to-7a for Step 6) in config.py and pass it into classification


### FINDING_1: Composite checks do not propagate persisted `REPO_ROOT`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Composite checks invoked through `implement checks-commit-route` and `checks-step5-resume` do not pass the validated session `REPO_ROOT` to `checks run-relevant`. Because `default_repo_root` prefers `CLAUDE_PROJECT_DIR` over the persisted root, checks can execute against a different tree than the one used to compute and persist the run identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/implement/dispatch_commit_route.py: resolve validated REPO_ROOT from session-env.sh (mirror step-8-assessment.sh), pass --repo-root to every checks run-relevant argv in _run_relevant_checks_for_site, and run the leg with cwd set to that root. Extend python/tests/implement/test_implement_dispatch.py to pin the passthrough and add a regression where CLAUDE_PROJECT_DIR points elsewhere but checks still execute against persisted REPO_ROOT.
  - From Cursor-Innovation: Mirror step-8-assessment.sh: pass --repo-root "$REPO_ROOT" in build_child_command and in checks-commit-route legs; add a subprocess regression where CLAUDE_PROJECT_DIR differs from persisted REPO_ROOT
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/implement/dispatch_commit_route.py` (and pin `--repo-root` from session `REPO_ROOT` in `_run_relevant_checks_for_site`, or teach `default_repo_root()` to prefer persisted `REPO_ROOT`) plus a regression that `CLAUDE_PROJECT_DIR` differs from session `REPO_ROOT`.


### FINDING_2: Child mode publishes launch identity without revalidation
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The child can run checks against a repository that changed after the parent computed the launch identity, then publish the parent-computed identity as though it described the checked inputs. This permits the foreground caller or later rejoin logic to consume or reuse a result whose recorded identity does not match the inputs actually checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: After entering the validated repository root and before invoking the checks CLI, recompute the identity and fail without publishing a terminal result if it differs from the seeded identity. Preserve the verified identity only after this check passes.
  - From Codex-Requirements: Recompute identity in child mode before checks and before terminal publication. Require both values to match the immutable launch identity. On mismatch, publish a non-reusable integrity failure. Add a subprocess regression that mutates the repository between identity seeding and child execution.


