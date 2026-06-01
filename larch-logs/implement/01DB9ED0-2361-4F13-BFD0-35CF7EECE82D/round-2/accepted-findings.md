### FINDING_1: code-quality / risk-integration: plan-mandated rebase acceptance tests largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan and acceptance criteria call for deterministic bash-parity coverage (drop-bump plus versioned drop-changelog replay, CHANGELOG deterministic prepass, post-rebump changelog tail, guarded drop stall, multi-hop continue after successful `rebase --continue`, post-waterfall scenarios), but `python/test_rebase.py` does not enforce these paths in CI. Regressions in drop/stage/commit orchestration, prepass, or multi-hop conflict handling can ship undetected until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add stub-runner `rebase_and_rebump` test scripting `drop_bump` dropped, bullets staged, `drop_changelog_commit` called, and `Stalled` on guarded companion drop refusal.
  - From cursor-specialist-edge-cases-output.txt: Add stub tests for companion drop Stalled/success
  - From cursor-specialist-plan-fidelity-output.txt: Add the listed stub-runner tests per implementation plan `test_rebase.py` section


### FINDING_11: correctness: `make_conflict_launch_fn` reads `LAUNCHER_EXIT` from agent output file, not launcher stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cursor can fail with `LAUNCHER_EXIT=1` on launcher stdout while Python reads a missing key from the agent `--output` file as `0`, treats the tier as winner, and skips Codex/Claude. Parse `LAUNCHER_EXIT` from `launch_tier` `CommandResult.stdout` (bash `launcher_stdout` parity); add a test with `LAUNCHER_EXIT` only on stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: correctness: no tree rollback between fixer waterfall tiers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Without snapshot/revert between tiers, a partial Cursor fix leaves a dirty tree; Codex runs on polluted state and mis-resolves. Bash reverts tracked+untracked deltas between tiers (`recovery_waterfall_paths_delta_revert` parity).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: correctness: uncaught `ChangelogError` during rebump changelog write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write_changelog_entry` can raise `ChangelogError` (bad anchor, duplicate heading) after bullets are staged; driver gets uncaught `ChangelogError` instead of `Stalled`. Catch `ChangelogError`, clear bullets if appropriate, and raise `Stalled` with a redacted message (or use a commit helper that returns `CommitResult`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Catch `ChangelogError` and raise `Stalled` or use commit helper that returns `CommitResult`


### FINDING_15: risk-integration: `_commit_changelog_after_rebump` / `_changelog_ready_after_rebump` lack direct tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Helpers at `python/rebase.py` ~151–233 have zero direct tests; bump integration tests noop the helper. Duplicate-heading stall, `replaces_version` fallback, and ready-tree short-circuit can regress at the rebase boundary without assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `tmp_path` unit tests for helper functions without monkeypatching `_commit_changelog_after_rebump`.


### FINDING_17: risk-integration: `version.go` / `go.sum` deterministic prepass paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Deterministic pre-pass for `version.go` and `go.sum` lacks tests; regression could broad-checkout or omit go module conflict resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `_deterministic_prepass` tests for `version.go` and `go.sum` basenames.


### FINDING_26: correctness: duplicate-heading check hardcodes MARKDOWN for RST changelogs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicate-version-heading detection hardcodes MARKDOWN while RST changelogs with bullets bypass correct dup detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use `detect_format` for `duplicate_version_heading_count`


### FINDING_31: correctness: `_sync_local_main` silently returns on `main` instead of refusing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: If `ship.py` ever invokes `rebase_and_rebump` on `main`, Python silently returns instead of refusing like `git-sync-local-main.sh`; rebump may proceed with wrong branch semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Raise `Stalled` with bash-parity message and add a unit test


### FINDING_8: code-quality / risk-integration: `read_launcher_exit` lacks unit tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `read_launcher_exit` in `python/agents.py` has no unit test. Regression in `LAUNCHER_EXIT` parsing could break `make_conflict_launch_fn` waterfall classification (wrong tier skip or stall).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add `test_agents` cases for `LAUNCHER_EXIT` parsing and missing file default.


