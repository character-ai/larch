### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:181-211
- **Concern**: Production checks composites never pass persisted REPO_ROOT to checks run-relevant. Scenario: The plan updates only run-step-checks.sh and step-6-entry.sh, but Step 3, Step 5 self-review, Step 5 resume checks, and Step 6 all invoke checks through implement checks-commit-route or implement checks-step5-resume, which call _run_relevant_checks_for_site without --repo-root. checks run-relevant default_repo_root prefers CLAUDE_PROJECT_DIR over git toplevel, so identity can be computed from session REPO_ROOT while checks run against a different tree and persist results under the wrong inputs.
- **Proposed resolution**: Add ### UPDATED: python/larch/implement/dispatch_commit_route.py: resolve validated REPO_ROOT from session-env.sh (mirror step-8-assessment.sh), pass --repo-root to every checks run-relevant argv in _run_relevant_checks_for_site, and run the leg with cwd set to that root. Extend python/tests/implement/test_implement_dispatch.py to pin the passthrough and add a regression where CLAUDE_PROJECT_DIR points elsewhere but checks still execute against persisted REPO_ROOT.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:144-166; skills/implement/scripts/step-6-entry.sh:123-144
- **Concern**: Child mode does not explicitly revalidate the immutable launch identity before running checks. Scenario: The launcher computes identity I, then the repository changes before the child starts. The child checks the changed tree I2 but publishes I, so the foreground caller can consume a result produced from inputs different from the recorded identity.
- **Proposed resolution**: After entering the validated repository root and before invoking the checks CLI, recompute the identity and fail without publishing a terminal result if it differs from the seeded identity. Preserve the verified identity only after this check passes.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:125-135
- **Concern**: Child checks launches omit explicit --repo-root while checks default_repo_root prefers CLAUDE_PROJECT_DIR. Scenario: Identity is computed from session REPO_ROOT but checks run-relevant resolves the repo from CLAUDE_PROJECT_DIR or cwd, so a mismatched project dir can run checks on tree A while persisting identity for tree B
- **Proposed resolution**: Mirror step-8-assessment.sh: pass --repo-root "$REPO_ROOT" in build_child_command and in checks-commit-route legs; add a subprocess regression where CLAUDE_PROJECT_DIR differs from persisted REPO_ROOT

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/scripts/run-step-checks.sh:144-166
- **Concern**: Plan leaves tee-based child merge publication without a step-8-style identity round-trip. Scenario: Child mode pipes checks stdout through tee and mv, replacing the pre-seeded merge.env; terminal bgjob merge then lacks identity fields, so identity-valid completed rejoin (including unchanged failed-result reuse) never works
- **Proposed resolution**: Refactor child mode like step-8-assessment.sh run_child: read launch identity from seeded merge.env, run checks, then write_merge_kvs that preserves identity KVs plus child NEXT_ACTION output; apply the same pattern in step-6-entry.sh child mode

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/run-step-checks.sh:215-224
- **Concern**: Live-row identity lookup precedence is unspecified. Scenario: During a live job result.env may be absent or stale; reading it before merge.env can fail closed or mis-route despite a valid seeded merge identity
- **Proposed resolution**: Pin merge.env-first, result.env-fallback identity lookup for live rejoin, matching step-8-assessment.sh lines 734-738

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:181-191
- **Concern**: Composite checks legs are not listed for validated-root propagation. Scenario: The plan requires child checks to run against persisted REPO_ROOT, but Step 3/6 children call `implement checks-commit-route` / `checks-step5-resume`, which invoke `_run_relevant_checks_for_site` without `--repo-root`. `default_repo_root()` prefers `CLAUDE_PROJECT_DIR` over cwd, so launcher-only `cd` cannot prevent checks from running against the wrong tree while identity is computed from session `REPO_ROOT`.
- **Proposed resolution**: Add `### UPDATED: python/larch/implement/dispatch_commit_route.py` (and pin `--repo-root` from session `REPO_ROOT` in `_run_relevant_checks_for_site`, or teach `default_repo_root()` to prefer persisted `REPO_ROOT`) plus a regression that `CLAUDE_PROJECT_DIR` differs from session `REPO_ROOT`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:144-166
- **Concern**: Child merge.env overwrite drops launch identity unless explicitly re-emitted. Scenario: BGJOB_CHILD captures checks stdout with `tee` then `mv` replaces the entire merge env. The daemon reads merge rows only at completion, so pre-start seeding is not durable. Checks/composite stdout does not carry identity KVs, so completed/live classifiers will see legacy rows without identity and either mis-rejoin or always treat results as stale.
- **Proposed resolution**: Pin the step-8 pattern: in BGJOB_CHILD read launch identity from the seeded merge env, then after `tee` re-write identity KVs into the terminal merge envelope via a shared helper (for example `checks_result_identity` merge writer) before `mv`; mirror the same contract in `step-6-entry.sh` and cover it in subprocess tests.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:144-166
- **Concern**: skills/implement/scripts/step-6-entry.sh:123-144. Scenario: Child-mode merge capture must union seeded launch identity with checks composite stdout
- **Proposed resolution**: `implement checks-commit-route`, `checks run-relevant`, and `implement step-6-entry` emit only checks/commit KVs. Child mode tees that stdout into a temp file and then `mv` replaces `merge.env`. Seeding identity before `bgjob start` survives only while the job is live; terminal `bgjob write_result` reads the post-`mv` merge file. Without an explicit union step, completed `*.result.env` rows lack identity, so matching completed rejoin never works and the planned subprocess regressions for identity-valid reuse cannot pass. In both launchers' `--bgjob-child` paths, after the composite `tee` finishes, merge the precomputed launch identity KVs into the temp merge envelope (prepend or helper merge) before promoting it to `merge.env`, and add a structure assertion that child mode cannot promote tee-only output without identity fields.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:17-24,55-58
- **Concern**: The child stamps the parent-computed identity without validating that checks ran against that identity. Scenario: The repository can change after the parent computes identity but before or during child checks. The child then publishes a result labeled with the old identity. The initial bgjob wait can consume that result directly, and restoring the old tree later can make it reusable for inputs the checks never tested.
- **Proposed resolution**: Recompute identity in child mode before checks and before terminal publication. Require both values to match the immutable launch identity. On mismatch, publish a non-reusable integrity failure. Add a subprocess regression that mutates the repository between identity seeding and child execution.
