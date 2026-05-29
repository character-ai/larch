### FINDING_1: Cleanup activity scan misses nested live writes
- **Reviewer(s)**: Cursor-Arch, Codex-Edge
- **Severity**: important
- **Concern**: The planned cleanup age check only considers the session directory and immediate children, so live nested writes under paths such as `design-export/`, `larch-logs/`, or `breadcrumbs/` may not refresh the observed mtime and an active session can be deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define newest-activity with a shallow recursive max (e.g. `find "$entry" -mindepth 1 -maxdepth 2` files/dirs via the existing dual-`stat` helper) or another bounded depth that covers `design-export/` and `larch-logs/`; extend `test-cleanup.sh` with a stale parent + fresh grandchild fixture
  - From Codex-Edge: Make the activity check include known nested breadcrumb files, or use a bounded recursive max-mtime scan for session dirs before deletion

### FINDING_2: Already-latest prune lacks a concrete target version
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The already-latest upgrade path is planned to stamp and prune before `ACTUAL_VERSION` is assigned, so pruning may run with an unset or empty target and fail to force-retain the currently installed version.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before the already-latest prune call, bind the prune target explicitly, for example ACTUAL_VERSION="$CURRENT_INSTALLED_VERSION", or make the prune function accept a target-version argument and call it with CURRENT_INSTALLED_VERSION on this path.
  - From Cursor-Pragmatic: In the already-latest branch set the prune target from CURRENT_INSTALLED_VERSION (or assign ACTUAL_VERSION there) before calling the shared prune helper; update the plan wording accordingly
  - From Codex-Pragmatic: Revise the plan to set a concrete target before the already-latest prune, e.g. ACTUAL_VERSION="${CURRENT_INSTALLED_VERSION:-$INSTALLED_VERSION}", or make the prune helper take the target version as an explicit argument

### FINDING_3: SECURITY.md keeps stale upgrade pin contract
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan removes upgrade active-session pinning, but `SECURITY.md` would still describe session-env and fallback-root protections that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Replace the paragraph with the new install-stamp and max-8 retention trust model, or delete it and explicitly state that upgrade pruning no longer scans session env files or fallback session roots.

### FINDING_4: upgrade-larch script behavior docs still promise no side effects
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `skills/upgrade-larch/scripts/upgrade-larch.md` can still say the already-latest path exits without touching plugin state, even though the plan adds stamp and prune side effects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the upgrade-larch.md rewrite step to explicitly update Behavior step 2: run keep-8 prune and best-effort .larch-installed-at stamp before exit 0 when already at latest stable

### FINDING_5: Identity-record rename adds unnecessary compatibility risk
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Renaming `.larch-keepalive` to `.larch-session` broadens a cleanup/prune change into writer, reader, docs, and compatibility behavior where a mismatch could break session binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the existing .larch-keepalive filename for this PR, slim its contents if desired, remove cleanup's sentinel skip, and update wording to describe it as an identity record. Defer any filename rename to a separate compatibility PR only if the name itself causes a real user-facing problem.

### FINDING_6: cleanup SKILL prompt update is too narrow
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The cleanup skill prompt and metadata may continue to describe singleton-session verification and abort behavior after cleanup becomes age-based and always-runnable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Expand the `skills/cleanup/SKILL.md` edit scope: refresh frontmatter `description`, the intro paragraph, NEVER #1, and Step 1 verification (relay counts; do not stop on SESSION_COUNT>1 or script non-zero solely for concurrency)
  - From Codex-Requirements: Expand the skills/cleanup/SKILL.md plan item to update the frontmatter description as well as the body, removing singleton-verification wording

### FINDING_7: upgrade-larch SKILL prompt is missing from the plan
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The runtime `/upgrade-larch` skill prompt may still claim already-latest makes no changes and may retain active-session harness wording after active-session pins are removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED skills/upgrade-larch/SKILL.md to the plan; revise Step 2 to say no reinstall/restart is needed but cache prune/stamp may run, and replace the active-session harness wording with install-stamp keep-8 prune validation

### FINDING_8: cleanup tests omit invalid retention value coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan requires invalid `LARCH_CLEANUP_RETENTION_DAYS` values to warn and fall back to 7, but the proposed cleanup harness cases do not test that acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one minimal test-cleanup case with an invalid value, asserting the warning and default-7 behavior; no broad matrix needed

### FINDING_9: Unstamped fallback mtimes can outrank stamped installs
- **Reviewer(s)**: Cursor-dyn-retention-algorithm, Codex-dyn-retention-algorithm
- **Severity**: important
- **Concern**: Sorting by install stamp or fallback directory mtime can allow legacy unstamped directories with bumped mtimes to outrank stamped versions and consume one of the retained slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-retention-algorithm: Make stamp presence part of the sort key so stamped dirs sort before un-stamped fallback dirs, then sort by timestamp descending and deterministic version-string tiebreak; keep the seeded ACTUAL_VERSION invariant unchanged

### FINDING_10: Legacy identity fallback tests do not cover all resolver arms
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: important
- **Concern**: A single legacy `.larch-keepalive` fixture may miss resolver bugs across the distinct eligibility arms for `design-export/manifest.env`, `review-round-summary.md`, and `.bump-version-armed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-identity-transition: Revise the test step to exercise legacy .larch-keepalive binding for each resolver arm, preferably by parameterizing the existing SessionStart fixture helper rather than adding broad new harnesses.

### FINDING_11: Missing both-files precedence fixture
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: latent
- **Concern**: The plan does not require a fixture where both `.larch-session` and `.larch-keepalive` exist, so an implementation could incorrectly bind through stale legacy data or produce ambiguous resolver output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-identity-transition: Add one minimal mixed-state fixture: .larch-session has the expected CLONE_PATH/SESSION_ID, .larch-keepalive has conflicting values, and resolution must bind only through .larch-session without duplicate or ambiguous output.

### FINDING_12: Temporary legacy fallback has no removal trigger
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: latent
- **Concern**: The planned read-only `.larch-keepalive` compatibility fallback has no expiry or removal condition, so it may become permanent compatibility code and hide future `.larch-session` regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-identity-transition: Update the planned resolver doc/comment to name a concrete removal trigger, such as after one release window or after no supported in-flight sessions can predate this rollout.
