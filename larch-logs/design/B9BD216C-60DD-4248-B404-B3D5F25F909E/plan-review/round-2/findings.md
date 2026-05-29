### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:26-27
- **Concern**: Plan keys newest-activity to dir plus immediate children only. Scenario: Active `/implement` tmpdirs usually write under `design-export/manifest.env`, `larch-logs/…`, and similar paths two or more levels below the session root; on APFS those writes refresh file mtimes without updating the parent directory mtime, so max(dir, immediate children) can stay older than `LARCH_CLEANUP_RETENTION_DAYS` while the session is live and `/cleanup` deletes it
- **Proposed resolution**: Define newest-activity with a shallow recursive max (e.g. `find "$entry" -mindepth 1 -maxdepth 2` files/dirs via the existing dual-`stat` helper) or another bounded depth that covers `design-export/` and `larch-logs/`; extend `test-cleanup.sh` with a stale parent + fresh grandchild fixture

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:230-238
- **Concern**: Already-latest prune path has no defined ACTUAL_VERSION target. Scenario: The plan routes the already-latest branch through stamp and prune, but the current branch exits before ACTUAL_VERSION is assigned and the plan does not define the target value for that path. Under set -u or an empty target, pruning can fail or skip the invariant that the current installed version is retained while trimming to 8.
- **Proposed resolution**: Before the already-latest prune call, bind the prune target explicitly, for example ACTUAL_VERSION="$CURRENT_INSTALLED_VERSION", or make the prune function accept a target-version argument and call it with CURRENT_INSTALLED_VERSION on this path.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:241
- **Concern**: The plan removes upgrade session-pin machinery but leaves its security contract stale. Scenario: After the proposed change, upgrade-larch no longer reads session-env.sh, LARCH_SESSIONS_DIR, or LARCH_UPGRADE_FALLBACK_SESSION_ROOTS for active-session pins. Leaving this paragraph in SECURITY.md would claim a trust model and active-session protection that no longer exist.
- **Proposed resolution**: Replace the paragraph with the new install-stamp and max-8 retention trust model, or delete it and explicitly state that upgrade pruning no longer scans session env files or fallback session roots.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:46-47
- **Concern**: Newest-activity only checks the session dir and immediate children. Scenario: Active long-running design/review work can write only nested breadcrumb files under $SESSION_TMPDIR/breadcrumbs; appends update the file mtime but not the session dir or breadcrumbs dir mtime, so /cleanup can classify an active session as older than LARCH_CLEANUP_RETENTION_DAYS and rm -rf it
- **Proposed resolution**: Make the activity check include known nested breadcrumb files, or use a bounded recursive max-mtime scan for session dirs before deletion

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.md:12-12
- **Concern**: Behavior step 2 still promises an idempotent exit with no side effects. Scenario: Plan adds already-latest prune+stamp (plan.txt:16,154) but the UPDATED upgrade-larch.md bullet only names rewriting step 8 and Active-session guard (plan.txt:44); implementers can leave step 2 saying "exits 0 without touching any plugin state" while the script deletes cache dirs
- **Proposed resolution**: Extend the upgrade-larch.md rewrite step to explicitly update Behavior step 2: run keep-8 prune and best-effort .larch-installed-at stamp before exit 0 when already at latest stable

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/session-setup.sh:255-270; skills/implement/scripts/lib-resolve-implement-tmpdir.sh:47-65
- **Concern**: Finding 1: Identity-record rename adds avoidable scope to a SIMPLE cleanup/prune fix. Scenario: The plan renames .larch-keepalive to .larch-session, updates writer/reader/tests/docs, and adds a legacy fallback even though the live resolver contract only needs CLONE_PATH and SESSION_ID. A writer/reader mismatch would break Stop/SessionStart binding, while cleanup can stop honoring the existing file without renaming it.
- **Proposed resolution**: Keep the existing .larch-keepalive filename for this PR, slim its contents if desired, remove cleanup's sentinel skip, and update wording to describe it as an identity record. Defer any filename rename to a separate compatibility PR only if the name itself causes a real user-facing problem.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:230-238; plan.txt:16-17
- **Concern**: Already-latest prune is specified to stamp $ACTUAL_VERSION but that variable is only assigned after install (lines 261-263); the early exit at 235-238 runs before ACTUAL_VERSION exists. Scenario: Already-latest /upgrade-larch with an over-cap cache may seed prune with an empty target, skip stamping, or mis-order retention despite the plan’s invariants
- **Proposed resolution**: In the already-latest branch set the prune target from CURRENT_INSTALLED_VERSION (or assign ACTUAL_VERSION there) before calling the shared prune helper; update the plan wording accordingly

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:230-238
- **Concern**: Already-latest prune path does not define the retained target before pruning. Scenario: The current early-exit branch runs before ACTUAL_VERSION is assigned in the existing script; if the implementation follows the plan's ACTUAL_VERSION wording literally, the already-latest prune can run with an empty target and fail to force-retain the installed version
- **Proposed resolution**: Revise the plan to set a concrete target before the already-latest prune, e.g. ACTUAL_VERSION="${CURRENT_INSTALLED_VERSION:-$INSTALLED_VERSION}", or make the prune helper take the target version as an explicit argument

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/SKILL.md:3;skills/cleanup/SKILL.md:9;skills/cleanup/SKILL.md:25-26
- **Concern**: `/cleanup` skill surface update is narrower than the new script contract. Scenario: Plan only rewrites NEVER #1 and a "behavior section" that does not exist; YAML description, intro, and Step 1 still tell the agent to abort on multiple sessions and treat non-zero exit as failure after cleanup.sh becomes always-runnable and age-based
- **Proposed resolution**: Expand the `skills/cleanup/SKILL.md` edit scope: refresh frontmatter `description`, the intro paragraph, NEVER #1, and Step 1 verification (relay counts; do not stop on SESSION_COUNT>1 or script non-zero solely for concurrency)

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/SKILL.md:21-27
- **Concern**: FINDING_1: /upgrade-larch skill prompt is not in the plan despite changed already-latest and prune behavior. Scenario: After the PR, the runtime prompt can still tell the operator that already-latest made no changes, even though the plan now stamps/prunes on that path; it also keeps an active-session prune harness label after active-session pins are removed
- **Proposed resolution**: Add UPDATED skills/upgrade-larch/SKILL.md to the plan; revise Step 2 to say no reinstall/restart is needed but cache prune/stamp may run, and replace the active-session harness wording with install-stamp keep-8 prune validation

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/cleanup/SKILL.md:3
- **Concern**: FINDING_2: cleanup SKILL frontmatter description is outside the planned rewrite. Scenario: The plan updates the behavior section and NEVER item, but the skill metadata can still advertise verifying only one Claude session is active after the singleton guard is removed
- **Proposed resolution**: Expand the skills/cleanup/SKILL.md plan item to update the frontmatter description as well as the body, removing singleton-verification wording

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:94-95,168-173
- **Concern**: FINDING_3: cleanup harness plan omits invalid LARCH_CLEANUP_RETENTION_DAYS coverage. Scenario: The plan requires positive-integer validation with warning and fallback to 7, but the proposed test-cleanup cases do not test that new acceptance criterion
- **Proposed resolution**: Add one minimal test-cleanup case with an invalid value, asserting the warning and default-7 behavior; no broad matrix needed

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-retention-algorithm, Codex-dyn-retention-algorithm
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:118-131
- **Concern**: Proposed install-stamp ordering can let un-stamped fallback mtime outrank stamped versions. Scenario: The plan says key = install stamp else dir mtime, so a legacy dir whose mtime was bumped by the old touch helper can sort ahead of an already-stamped newer version and consume one of the 8 retained slots; the plan acknowledges this as failure mode #3 rather than preventing it
- **Proposed resolution**: Make stamp presence part of the sort key so stamped dirs sort before un-stamped fallback dirs, then sort by timestamp descending and deterministic version-string tiebreak; keep the seeded ACTUAL_VERSION invariant unchanged

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/lib-resolve-implement-tmpdir.sh:37-48 scripts/test-sessionstart-health.sh:176-184
- **Concern**: Planned fallback coverage is underspecified for the resolver's three eligibility arms. Scenario: The plan asks for one legacy .larch-keepalive fallback fixture, but the resolver has design-export/manifest.env, review-round-summary.md, and .bump-version-armed arms. A fallback accidentally wired to only one arm could pass that single fixture while old in-flight sessions in the other arms fail to bind.
- **Proposed resolution**: Revise the test step to exercise legacy .larch-keepalive binding for each resolver arm, preferably by parameterizing the existing SessionStart fixture helper rather than adding broad new harnesses.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-sessionstart-health.sh:176-184 scripts/test-keepalive-sentinel.sh:47-66
- **Concern**: Plan does not require a both-files precedence fixture. Scenario: A dir containing both .larch-session and .larch-keepalive could bind through stale legacy data if implementation checks the fallback first or treats both files as separate candidates, producing ambiguous resolver results after the transition.
- **Proposed resolution**: Add one minimal mixed-state fixture: .larch-session has the expected CLONE_PATH/SESSION_ID, .larch-keepalive has conflicting values, and resolution must bind only through .larch-session without duplicate or ambiguous output.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/lib-resolve-implement-tmpdir.md:9-26
- **Concern**: The temporary legacy fallback has no removal trigger. Scenario: The plan calls .larch-keepalive a temporary read-only compatibility fallback, but without an expiry condition it can become permanent compatibility code and mask future regressions around .larch-session writing.
- **Proposed resolution**: Update the planned resolver doc/comment to name a concrete removal trigger, such as after one release window or after no supported in-flight sessions can predate this rollout.
