## Plan

confidence: high

## Approach

Add a checks-input identity that covers both committed and uncommitted repository state. Persist it with each checks bgjob result. Validate it before rejoining any live or completed job, and revalidate it in the child immediately before checks run and before terminal publication.

The identity will contain:

- The current `HEAD` SHA.
- A deterministic fingerprint of the index, tracked worktree changes, untracked paths, and untracked file contents.
- A version marker so the fingerprint grammar can evolve without accepting an older shape.

Resolve the repository from persisted `REPO_ROOT`, not the launcher’s current directory. After validating that root, explicitly propagate it to every checks execution path through immutable launch inputs and execution cwd so identity computation and checks execution use the same repository. This includes direct `checks run-relevant` invocations from the commit-route dispatcher, where `CLAUDE_PROJECT_DIR` must not redirect composite checks to a different tree.

Update both checks launchers—`run-step-checks.sh` for Step 3 and Step 5 self-review, and `step-6-entry.sh` for production Step 6—to:

1. Compute the live identity before inspecting bgjob state.
2. Seed the merge-result env with that identity before starting the child.
3. Preserve the identity only after the child verifies it still matches the repository immediately before checks execution and again before terminal publication.
4. Rejoin a live registry row only when its seeded identity matches the live repository.
5. Rejoin a completed result only when `STEP`, `BGJOB_RC`, a recognized terminal `NEXT_ACTION`, and both identity fields match.
6. Clear a stale completed result and launch fresh checks.
7. Fail closed on a live identity mismatch. Do not start a competing checks job.
8. Keep the existing symlink and non-regular-file refusals.

A child whose repository changes after launch must not publish a terminal envelope that represents the parent’s stale identity. Before invoking checks, child mode will recompute and compare identity against the immutable launch identity. It will repeat that comparison immediately before publishing a terminal merge envelope. A mismatch will produce a non-reusable integrity failure and will not publish a normal terminal checks result for reuse.

Use explicit terminal-action sets rather than truthiness. The shared set will include the union required by the checks wrappers: `continue`, `stall`, `checks-failed`, and Step 6’s `skip-to-7a`. An unchanged failed result may be rejoined, but any repository drift forces a new checks run.

Step 6 retains its existing change gate and `--force-checks true` behavior. Its independent live and completed rejoin branches receive the same identity-aware contract; `--force-checks true` bypasses only the change gate, not identity validation.

## Files to modify/create

### NEW: python/larch/implement/checks_result_identity.py

- Add a frozen identity type for checks launch inputs.
- Compute `HEAD` and the working-tree fingerprint through the injected runner.
- Include binary unstaged and staged diffs plus untracked path and content hashes.
- Reject unresolved, symlinked, non-regular, or non-repository roots.
- Fail closed when a Git command or required file read fails.
- Parse checks result and merge env files through `larch.io` policy helpers.
- Classify envelopes as matching, stale, incomplete, or unsafe.
- Require exact identity fields and an explicit terminal `NEXT_ACTION` value for completed-result reuse.
- Accept a caller-provided or shared terminal-action set so every production wrapper validates its supported terminal routes consistently.
- Provide child-launch validation helpers that compare a recomputed repository identity with the immutable seeded identity before checks execution and before terminal-result publication.
- Represent an identity drift during child execution as a non-reusable integrity failure rather than a normal reusable checks envelope.

### UPDATED: python/larch/core/config.py

- Define the checks identity KV names, fingerprint schema marker, and recognized checks terminal-action set once.
- Include `skip-to-7a` in the shared set used by the Step 6 production launcher.
- Define the non-reusable child identity-integrity failure route or wire literal once, if a shared literal is required.
- Keep these wire literals shared by the identity helper, launcher integrations, and tests.

### UPDATED: python/larch/implement/dispatch_commit_route.py

- Resolve and validate the persisted session `REPO_ROOT` for composite checks dispatch, following the existing validated-root pattern used by comparable implement entry points.
- Update `_run_relevant_checks_for_site` so every `checks run-relevant` invocation receives `--repo-root <validated REPO_ROOT>`.
- Execute each composite checks leg with cwd set to the same validated root.
- Ensure the commit-route and Step 5-resume paths cannot allow `CLAUDE_PROJECT_DIR`, inherited cwd, or another ambient project setting to select a repository different from the persisted session root.
- Preserve existing site routing, output grammar, and checks-command arguments other than the explicit root binding.

### UPDATED: skills/implement/scripts/run-step-checks.sh

- Replace the current truthy-`NEXT_ACTION` completion test and retired inline result classifier with the shared identity classifier.
- Resolve `REPO_ROOT` from `session-env.sh`, validate it, and compute the launch identity before live or completed rejoin decisions.
- Seed the merge-result env with the identity before `bgjob start`.
- Pass the validated `REPO_ROOT` and immutable launch identity into child mode, set the child execution directory to that root, and ensure the child uses that same root rather than inherited cwd or unrelated `CLAUDE_PROJECT_DIR`.
- In child mode, recompute identity after entering the validated root and immediately before invoking checks; fail as a non-reusable integrity error if it differs from the immutable seeded identity.
- Recompute identity again immediately before publishing the final merge-result envelope; do not publish a normal terminal result under the original identity if the repository changed while checks ran.
- Include the verified immutable identity in the child’s final merge-result envelope only after both child-side identity checks pass.
- For a matching live row, retain the zero-duration `bgjob wait` rejoin.
- For a live row with missing or mismatched identity, emit a specific error and exit without deleting state or launching a duplicate.
- For a stale completed result with no live row, safely remove the result and merge envs, verify cleanup, then follow the existing fresh-launch path.
- Preserve current Step 3 and Step 5 step slugs, budgets, foreground `BGJOB_STATUS=STARTED` grammar, and Bash 3.2 compatibility.

### UPDATED: skills/implement/scripts/step-6-entry.sh

- Apply the shared identity classifier to both production Step 6 rejoin paths for `implement-step6-checks`; do not rely on `run-step-checks.sh --site step6` as coverage for this launcher.
- Resolve and validate `REPO_ROOT` from `session-env.sh`, compute the live identity before inspecting live or completed Step 6 state, and use that root for child execution.
- Seed the Step 6 merge-result env with the launch identity before starting checks, explicitly propagate the validated root and immutable identity into child checks, and preserve both fields in the terminal merge envelope only after child-side validation.
- Recompute identity in the Step 6 child after entering the validated root and before checks execution, then again before terminal publication; convert either mismatch into a non-reusable integrity failure rather than a normal reusable terminal result.
- Rejoin matching live and completed Step 6 results only when the persisted identity, required envelope fields, and a recognized Step 6 terminal action match.
- Preserve valid `NEXT_ACTION=skip-to-7a` rejoin and routing behavior.
- Fail closed on a live identity mismatch without deleting active state or launching a duplicate.
- Safely clear completed stale Step 6 result and merge env state, verify cleanup, then use the existing fresh-launch path.
- Preserve Step 6’s current change gate and `--force-checks true` semantics; force mode bypasses its change gate but still uses identity-aware rejoin decisions.

### UPDATED: skills/implement/scripts/run-step-checks.md

- Document the persisted identity fields, fingerprint coverage, and validated-root child execution contract.
- State the live-row mismatch fail-closed behavior.
- Clarify that matching failed results may rejoin, while any committed, staged, unstaged, or untracked input drift triggers fresh checks.
- Document the child-side pre-check and pre-publication identity revalidation requirement and the non-reusable integrity-failure behavior on drift during execution.
- Name Step 3 and Step 5 self-review as consumers of this launcher contract.

### UPDATED: skills/implement/scripts/step-6-entry.md

- Document Step 6’s independent identity-aware live and completed rejoin contract.
- Specify that `skip-to-7a` remains a recognized completed terminal action when the identity matches.
- Clarify that `--force-checks true` bypasses the Step 6 change gate only and does not permit stale-result reuse.
- Document validated `REPO_ROOT` propagation to the child checks process.
- Document child-side pre-check and pre-publication identity revalidation and the non-reusable integrity-failure behavior if the repository drifts while checks are running.

### UPDATED: scripts/test-implement-structure.sh

- Replace assertions for the retired inline `step_checks_result_env_state` classifier with assertions for shared identity-classifier integration.
- Pin identity-bearing merge-envelope seeding, child-side identity revalidation, and validated-root propagation in `run-step-checks.sh`.
- Add corresponding structural assertions for `step-6-entry.sh`, including its production live and completed rejoin handling and child-side revalidation.
- Pin `dispatch_commit_route.py` forwarding `--repo-root` and executing relevant checks from the validated persisted root.
- Preserve existing launcher, budget, and continuation-contract assertions that remain valid.

### NEW: python/tests/implement/test_checks_result_identity.py

- Test deterministic identity generation for an unchanged repository.
- Verify identity changes after:
  - a new commit,
  - staged changes,
  - unstaged changes,
  - an untracked file addition,
  - untracked content changes,
  - untracked deletion.
- Test result classification for matching and mismatched step, return code, action, `HEAD`, fingerprint schema marker, and tree fingerprint.
- Test all recognized actions, including Step 6 `skip-to-7a`.
- Test unknown or missing `NEXT_ACTION` values as incomplete rather than reusable.
- Test duplicate keys, malformed values, symlinks, non-regular files, failed Git commands, and unreadable untracked inputs.
- Verify root validation and child-launch inputs bind the same resolved repository root.
- Verify child-side pre-check and pre-publication validation rejects a repository whose identity changed after launch seeding and does not classify that result as reusable.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Extend existing launcher and dispatch structure assertions to pin shared identity-helper integration, identity-bearing merge envelopes, explicit validated-root propagation to child checks, and the commit-route `--repo-root` passthrough.
- Keep the existing budget, step-slug, and zero-duration wait assertions intact.
- Assert neither launcher treats arbitrary non-empty `NEXT_ACTION` values as complete.
- Assert Step 6 preserves `skip-to-7a` as a recognized identity-valid terminal result.
- Add a regression where `CLAUDE_PROJECT_DIR` points at a different repository but `checks-commit-route` and `checks-step5-resume` execute `checks run-relevant` against the persisted, validated session `REPO_ROOT`.

### UPDATED: python/tests/implement/test_run_step_checks.py

- Add subprocess regressions for `run-step-checks.sh` Step 3 and Step 5 self-review showing an old `NEXT_ACTION=checks-failed` result starts a fresh bgjob after committed, staged, unstaged, and untracked repository drift.
- Cover matching completed rejoin, matching live rejoin, and active identity mismatch without duplicate launch.
- Verify the child receives and executes against the persisted validated repository root rather than an inherited alternate cwd.
- Add a regression that mutates the repository after launch identity seeding but before child checks execution; verify checks do not run or publish a normally reusable terminal envelope under the stale launch identity.
- Add a regression that mutates the repository while child checks are running; verify pre-publication revalidation prevents publication of a reusable result under the original identity.

### UPDATED: python/tests/implement/test_step_6_entry.py

- Add subprocess regressions against production `step-6-entry.sh`, not only `run-step-checks.sh --site step6`.
- Cover stale `implement-step6-checks` failed-result replacement after committed, staged, unstaged, and untracked drift.
- Cover matching completed and live rejoin, active identity mismatch without duplicate launch, and stale completed-state cleanup before relaunch.
- Exercise both normal Step 6 entry and repair re-entry with `--force-checks true`.
- Verify identity-valid `NEXT_ACTION=skip-to-7a` rejoins and preserves its existing routing behavior.
- Verify Step 6 child checks receive the validated persisted repository root.
- Add regressions for repository mutation between identity seeding and child execution, and during child checks execution, verifying that neither case publishes a normally reusable result carrying the stale launch identity.

## Edge cases

- A repair edits files without moving `HEAD`.
- A repair stages changes but does not commit them.
- An untracked file keeps the same path but changes contents.
- The repository changes after the parent seeds launch identity but before child checks begin.
- The repository changes while a checks bgjob is still live.
- The repository changes after checks complete but before the child publishes its terminal envelope.
- A legacy result env lacks identity fields.
- A result contains a valid identity but an unknown terminal action.
- A valid Step 6 result contains `NEXT_ACTION=skip-to-7a`.
- The result or merge env is a symlink, directory, or malformed KV file.
- Git cannot resolve `HEAD`, inspect the index, or read an untracked entry.
- The launcher’s inherited cwd or `CLAUDE_PROJECT_DIR` differs from persisted `REPO_ROOT`.
- Composite checks launched by commit-route or Step 5-resume inherit a conflicting `CLAUDE_PROJECT_DIR`.
- A dead registry row remains beside a stale result.

## Failure modes

- Treat identity computation or persisted-root validation failure as a launcher error. Never reuse a result without proven input identity.
- Treat unsafe persisted files as hard errors rather than deleting them.
- Treat an active identity mismatch as an integrity error. Preserve the live job state for diagnosis and avoid a second runner.
- Treat child-side identity mismatch before checks or before terminal publication as a non-reusable integrity failure; do not publish a normal checks terminal envelope claiming the stale launch identity.
- Treat missing or malformed identity on a completed, non-live result as stale. Safely clear it before relaunch.
- Treat an unsupported terminal action as incomplete rather than reusable.
- Preserve the existing bgjob wait and terminal-envelope behavior for identity-valid jobs.
- Ensure direct and composite checks executions run from and target the same validated persisted `REPO_ROOT` used for identity calculation.

## Testing strategy

Run targeted tests only:

- `python3 -m pytest python/tests/implement/test_checks_result_identity.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/implement/test_run_step_checks.py`
- `python3 -m pytest python/tests/implement/test_step_6_entry.py`
- Run targeted Ruff, Pyright, and Pylint checks for the changed Python files.
- Run `bash -n skills/implement/scripts/run-step-checks.sh skills/implement/scripts/step-6-entry.sh`.
- Run ShellCheck and the Bash 3.2 compatibility check against both changed shell launchers.
- Run `bash scripts/test-implement-structure.sh`.
- Run `bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` to confirm the existing caller and continuation contract remains intact.

## Acceptance

Run targeted tests only:

- `python3 -m pytest python/tests/implement/test_checks_result_identity.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/implement/test_run_step_checks.py`
- `python3 -m pytest python/tests/implement/test_step_6_entry.py`
- Run targeted Ruff, Pyright, and Pylint checks for the changed Python files.
- Run `bash -n skills/implement/scripts/run-step-checks.sh skills/implement/scripts/step-6-entry.sh`.
- Run ShellCheck and the Bash 3.2 compatibility check against both changed shell launchers.
- Run `bash scripts/test-implement-structure.sh`.
- Run `bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` to confirm the existing caller and continuation contract remains intact.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 535
diff_deleted: 105
mechanical_churn: false
oversize_override: operator
diff_lines: 640
