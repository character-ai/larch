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

### FINDING_3: Child merge publication drops launch identity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Child mode captures checks or composite stdout with `tee` and replaces `merge.env`, which discards the launch identity seeded before `bgjob start`. Since terminal result publication reads the post-`mv` merge file and checks output does not include the identity fields, completed results lack the identity required for valid rejoin and reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Refactor child mode like step-8-assessment.sh run_child: read launch identity from seeded merge.env, run checks, then write_merge_kvs that preserves identity KVs plus child NEXT_ACTION output; apply the same pattern in step-6-entry.sh child mode
  - From Cursor-Pragmatic: Pin the step-8 pattern: in BGJOB_CHILD read launch identity from the seeded merge env, then after `tee` re-write identity KVs into the terminal merge envelope via a shared helper (for example `checks_result_identity` merge writer) before `mv`; mirror the same contract in `step-6-entry.sh` and cover it in subprocess tests.
  - From Cursor-Requirements: `implement checks-commit-route`, `checks run-relevant`, and `implement step-6-entry` emit only checks/commit KVs. Child mode tees that stdout into a temp file and then `mv` replaces `merge.env`. Seeding identity before `bgjob start` survives only while the job is live; terminal `bgjob write_result` reads the post-`mv` merge file. Without an explicit union step, completed `*.result.env` rows lack identity, so matching completed rejoin never works and the planned subprocess regressions for identity-valid reuse cannot pass. In both launchers' `--bgjob-child` paths, after the composite `tee` finishes, merge the precomputed launch identity KVs into the temp merge envelope (prepend or helper merge) before promoting it to `merge.env`, and add a structure assertion that child mode cannot promote tee-only output without identity fields.

### FINDING_4: Live rejoin identity lookup precedence is unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Live-row identity lookup may read an absent or stale `result.env` before the valid seeded `merge.env`, causing valid live rejoin attempts to fail closed or be misrouted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin merge.env-first, result.env-fallback identity lookup for live rejoin, matching step-8-assessment.sh lines 734-738
